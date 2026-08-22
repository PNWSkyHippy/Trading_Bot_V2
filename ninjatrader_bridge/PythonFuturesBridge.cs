// NinjaTrader 8 AddOn: read-only completed-bar bridge to a local Python scanner.
// Copy this file into Documents\NinjaTrader 8\bin\Custom\AddOns and compile.

using System;
using System.Collections.Concurrent;

using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;

namespace NinjaTrader.NinjaScript.AddOns
{
    public class PythonFuturesBridge : AddOnBase
    {
        // Two independent destinations, each on its own local port, so a stalled
        // or flapping tunnel to Hostinger can never block or starve delivery to
        // the always-local scanner (and vice versa). The Hostinger SSH tunnel
        // (Scripts/run_emt_hostinger_tunnel.ps1) forwards local 8766 -> the VPS's
        // own 8765; the local scanner binds 8765 directly. They used to both want
        // local port 8765, which meant only one of them could ever be listening
        // at a time.
        private const string LocalHost = "http://127.0.0.1:8765";
        private const string HostingerHost = "http://127.0.0.1:8766";
        private const string BarPath = "/ingest/bar";
        private const string EmtPath = "/ingest/emt/bar";
        private const string HeartbeatPath = "/ingest/heartbeat";
        private const int HeartbeatIntervalMs = 30000;
        private const int EmtTickBars = 610;
        // Change this in both this file and ninja_futures_config.json.
        private const string SharedSecret = "okay-so-i-changed-secret";

        // Explicit active contracts are required for reliable live subscriptions.
        private readonly string[] instruments = {
            "MES 09-26", "ES 09-26",
            "MNQ 09-26", "NQ 09-26",
            "MYM 09-26", "YM 09-26",
            "M2K 09-26", "RTY 09-26",
            "MGC 12-26", "GC 12-26", "MNK 09-26",
            "NKD 09-26", "MBT 09-26", "MET 09-26"
        };
        private readonly ConcurrentDictionary<string, BarsRequest> requests =
            new ConcurrentDictionary<string, BarsRequest>();
        private readonly ConcurrentDictionary<string, BarsRequest> emtRequests =
            new ConcurrentDictionary<string, BarsRequest>();
        private readonly ConcurrentDictionary<string, int> currentBarCounts =
            new ConcurrentDictionary<string, int>();
        private readonly ConcurrentDictionary<string, DateTime> currentBarTimes =
            new ConcurrentDictionary<string, DateTime>();
        private readonly ConcurrentDictionary<string, byte> updateSeen =
            new ConcurrentDictionary<string, byte>();
        // Tracks the last time each subscription's Update event actually fired
        // (any live-tick update, not just a completed bar), keyed by instrument
        // name for the 1-minute feeds and "EMT:<name>" for the 610-tick feed.
        // NinjaTrader's BarsRequest subscriptions have occasionally been
        // observed to go silent for the rest of the session (no more Update
        // callbacks) while the connection and heartbeat stay healthy; only a
        // NinjaScript recompile -- which tears down and recreates this whole
        // AddOn -- brought data back. The watchdog below detects that
        // per-subscription silence and resubscribes automatically instead.
        private readonly ConcurrentDictionary<string, DateTime> lastUpdateUtc =
            new ConcurrentDictionary<string, DateTime>();
        private Timer heartbeatTimer;
        private Timer watchdogTimer;
        private const int WatchdogIntervalMs = 30000;
        private const int StaleThresholdMs = 120000;

        private struct OutboundMessage
        {
            public string Path;
            public string Json;
            public string Kind;
            public int Attempts;
            public DateTime FirstQueuedUtc;
        }

        // A brief tunnel drop (observed: a few minutes of connection resets
        // during the SSH handshake, e.g. logs/emt_tunnel.log) used to mean any
        // bar that failed its 2 inner PostJson attempts was gone for good --
        // NinjaTrader only ever sends bars going forward, it never resends a
        // completed bar once queued. That silently blew out the VPS-side EMT
        // strategy's opening-range window (RANGE_DATA_MISSED) even though the
        // data existed locally the whole time. Failed sends now go back on
        // their own queue and get retried until delivered, capped so a
        // destination that is down for a long time can't grow the backlog
        // forever.
        private const int MaxRequeueAttempts = 30;
        private static readonly TimeSpan MaxRequeueAge = TimeSpan.FromMinutes(10);
        // Hostinger must never replay an hours-old market-data backlog after
        // its SSH tunnel recovers; stale FIFO messages can starve live bars.
        private static readonly TimeSpan MaxHostingerDeliveryAge = TimeSpan.FromMinutes(2);
        // Reserve remote queue capacity for ordinary one-minute bars.  The
        // 610-tick feeds across all subscribed contracts can otherwise fill it.
        private const int MaxPendingHostingerEmtMessages = 40;

        private readonly BlockingCollection<OutboundMessage> localQueue =
            new BlockingCollection<OutboundMessage>(2000);
        private readonly BlockingCollection<OutboundMessage> hostingerQueue =
            new BlockingCollection<OutboundMessage>(2000);
        private Thread localSenderThread;
        private Thread hostingerSenderThread;
        private volatile bool stopping;

        protected override void OnStateChange()
        {
            if (State == State.Active)
            {
                StartSenders();
                StartSubscriptions();
                StartEmtSubscriptions();
                StartHeartbeat();
                StartWatchdog();
            }
            else if (State == State.Terminated)
            {
                StopWatchdog();
                StopHeartbeat();
                StopSubscriptions();
                StopEmtSubscriptions();
                StopSenders();
            }
        }

        private void StartSenders()
        {
            stopping = false;
            localSenderThread = new Thread(() => SenderLoop(localQueue, LocalHost, "local"));
            localSenderThread.IsBackground = true;
            localSenderThread.Name = "PythonFuturesBridgeLocalSender";
            localSenderThread.Start();

            hostingerSenderThread = new Thread(() => SenderLoop(hostingerQueue, HostingerHost, "hostinger"));
            hostingerSenderThread.IsBackground = true;
            hostingerSenderThread.Name = "PythonFuturesBridgeHostingerSender";
            hostingerSenderThread.Start();
        }

        private void StopSenders()
        {
            stopping = true;
            localQueue.CompleteAdding();
            hostingerQueue.CompleteAdding();
            if (localSenderThread != null && localSenderThread.IsAlive)
                localSenderThread.Join(2000);
            if (hostingerSenderThread != null && hostingerSenderThread.IsAlive)
                hostingerSenderThread.Join(2000);
            localSenderThread = null;
            hostingerSenderThread = null;
        }

        private void SenderLoop(BlockingCollection<OutboundMessage> queue, string host, string label)
        {
            foreach (OutboundMessage msg in queue.GetConsumingEnumerable())
            {
                if (stopping)
                    break;
                if (label == "hostinger" &&
                    DateTime.UtcNow - msg.FirstQueuedUtc > MaxHostingerDeliveryAge)
                {
                    Print(string.Format(CultureInfo.InvariantCulture,
                        "PythonFuturesBridge hostinger dropping stale {0} {1} queued {2:F0}s ago",
                        msg.Kind, msg.Path,
                        (DateTime.UtcNow - msg.FirstQueuedUtc).TotalSeconds));
                    continue;
                }
                if (!PostJson(msg, host, label) && msg.Kind != "heartbeat")
                    Requeue(queue, label, msg);
            }
        }

        private void Requeue(BlockingCollection<OutboundMessage> queue, string label, OutboundMessage msg)
        {
            if (stopping || queue.IsAddingCompleted)
                return;
            OutboundMessage retry = msg;
            retry.Attempts = msg.Attempts + 1;
            if (retry.Attempts > MaxRequeueAttempts || (DateTime.UtcNow - retry.FirstQueuedUtc) > MaxRequeueAge)
            {
                Print(string.Format(CultureInfo.InvariantCulture,
                    "PythonFuturesBridge {0} giving up on {1} {2} after {3} attempts @ {4:HH:mm:ss.fff} UTC",
                    label, msg.Kind, msg.Path, retry.Attempts, DateTime.UtcNow));
                return;
            }
            if (!queue.TryAdd(retry))
                Print(string.Format(CultureInfo.InvariantCulture,
                    "PythonFuturesBridge {0} queue full @ {1:HH:mm:ss.fff} UTC; dropped retry of {2} {3}",
                    label, DateTime.UtcNow, msg.Kind, msg.Path));
        }

        private void Enqueue(BlockingCollection<OutboundMessage> queue, string label, OutboundMessage msg)
        {
            if (stopping || queue.IsAddingCompleted)
                return;
            if (!queue.TryAdd(msg))
                Print(string.Format(CultureInfo.InvariantCulture,
                    "PythonFuturesBridge {0} queue full @ {1:HH:mm:ss.fff} UTC; dropped {2} {3}",
                    label, DateTime.UtcNow, msg.Kind, msg.Path));
        }

        private void EnqueueBoth(string path, string json, string kind)
        {
            OutboundMessage msg = new OutboundMessage {
                Path = path, Json = json, Kind = kind,
                Attempts = 0, FirstQueuedUtc = DateTime.UtcNow
            };
            Enqueue(localQueue, "local", msg);
            if (kind == "emt" && hostingerQueue.Count >= MaxPendingHostingerEmtMessages)
            {
                Print(string.Format(CultureInfo.InvariantCulture,
                    "PythonFuturesBridge hostinger EMT queue reserve reached @ {0:HH:mm:ss.fff} UTC; dropped live EMT bar",
                    DateTime.UtcNow));
                return;
            }
            Enqueue(hostingerQueue, "hostinger", msg);
        }

        // A local startup history seed is useful.  Sending all of it through
        // the VPS tunnel is not: 13 minute plus 13 EMT feeds overflowed the
        // remote queue on each Ninja restart before current bars could enter.
        private void EnqueueLocalOnly(string path, string json, string kind)
        {
            OutboundMessage msg = new OutboundMessage {
                Path = path, Json = json, Kind = kind,
                Attempts = 0, FirstQueuedUtc = DateTime.UtcNow
            };
            Enqueue(localQueue, "local", msg);
        }

        private void StartHeartbeat()
        {
            StopHeartbeat();
            // Send once immediately, then every 30 seconds. This is a tiny,
            // authenticated bridge keepalive only; it never creates bars,
            // requests history, submits orders, or simulates user input.
            // Building the payload and enqueueing it is the only work done on
            // the Timer callback itself, so a stalled destination can never
            // delay or skip the next tick.
            heartbeatTimer = new Timer(_ => SendHeartbeat(), null, 0, HeartbeatIntervalMs);
        }

        private void StopHeartbeat()
        {
            Timer timer = Interlocked.Exchange(ref heartbeatTimer, null);
            if (timer != null)
                timer.Dispose();
        }

        private void SendHeartbeat()
        {
            string json = string.Format(CultureInfo.InvariantCulture,
                "{{\"secret\":\"{0}\",\"source\":\"ninjatrader\"," +
                "\"type\":\"heartbeat\",\"time\":\"{1:o}\"," +
                "\"subscriptions\":{2}}}",
                SharedSecret, DateTime.UtcNow, (requests.Count + emtRequests.Count));
            EnqueueBoth(HeartbeatPath, json, "heartbeat");
        }

        private void StartSubscriptions()
        {
            foreach (string name in instruments)
                SubscribeInstrument(name);
        }

        private void SubscribeInstrument(string name)
        {
            Instrument instrument = Instrument.GetInstrument(name);
            if (instrument == null)
            {
                Print("PythonFuturesBridge: instrument not found: " + name);
                return;
            }

            // Seed the watchdog clock at subscribe time, not just on the first
            // Update event. Without this, an instrument whose live feed never
            // fires a single Update after this initial subscribe has no
            // lastUpdateUtc entry at all, so CheckSubscriptionHealth's
            // TryGetValue always misses it and the watchdog can never detect
            // or resubscribe it -- it just stays silent forever.
            lastUpdateUtc[name] = DateTime.UtcNow;

            BarsRequest request = new BarsRequest(instrument, 500);
            request.BarsPeriod = new BarsPeriod { BarsPeriodType = BarsPeriodType.Minute, Value = 1 };
            request.TradingHours = TradingHours.Get("Default 24 x 7");
            request.Update += OnBarsUpdate;
            requests[name] = request;
            request.Request((bars, errorCode, errorMessage) =>
            {
                if (errorCode != ErrorCode.NoError)
                    Print("PythonFuturesBridge request failed for " + name + ": " + errorMessage);
                else
                {
                    Print("PythonFuturesBridge subscribed: " + name + " (1-minute, historical bars=" + bars.Bars.Count + ")");
                    SendHistory(bars.Bars, instrument.FullName);
                }
            });
        }

        // Called by the watchdog when a subscription's Update event has gone
        // silent for too long. Tears down the stale BarsRequest and creates a
        // fresh one, clearing this instrument's tracked bar-time/seen state so
        // OnBarsUpdate treats it as a brand-new subscription (matching what
        // happens today after a manual NinjaScript recompile).
        private void ResubscribeInstrument(string name)
        {
            BarsRequest oldRequest;
            if (requests.TryRemove(name, out oldRequest) && oldRequest != null)
            {
                oldRequest.Update -= OnBarsUpdate;
                oldRequest.Dispose();
            }
            DateTime discardedTime;
            currentBarTimes.TryRemove(name, out discardedTime);
            byte discardedByte;
            updateSeen.TryRemove(name, out discardedByte);
            // Reset (not remove) the watchdog clock: if this fresh subscription
            // also fails to produce updates, CheckSubscriptionHealth needs an
            // existing timestamp to compare against on the next cycle, or it
            // reads "no entry" as "never subscribed yet" and silently stops
            // checking this instrument forever -- exactly what forced manual
            // recompiles before this fix.
            lastUpdateUtc[name] = DateTime.UtcNow;
            SubscribeInstrument(name);
        }

        private void StartEmtSubscriptions()
        {
            StopEmtSubscriptions();
            foreach (string name in instruments)
                SubscribeEmtInstrument(name);
        }

        private void SubscribeEmtInstrument(string name)
        {
            string emtKey = "EMT:" + name;
            int discardedCount;
            currentBarCounts.TryRemove(emtKey, out discardedCount);
            byte discardedByte;
            updateSeen.TryRemove(emtKey, out discardedByte);
            // Reset (not remove) the watchdog clock -- see the matching comment
            // in ResubscribeInstrument. A removed entry makes a failed
            // resubscribe invisible to CheckSubscriptionHealth forever.
            lastUpdateUtc[emtKey] = DateTime.UtcNow;

            Instrument instrument = Instrument.GetInstrument(name);
            if (instrument == null)
            {
                Print("PythonFuturesBridge EMT instrument not found: " + name);
                return;
            }

            BarsRequest request = new BarsRequest(instrument, 500);
            request.BarsPeriod = new BarsPeriod { BarsPeriodType = BarsPeriodType.Tick, Value = EmtTickBars };
            request.TradingHours = TradingHours.Get("Default 24 x 7");
            request.Update += OnEmtBarsUpdate;
            emtRequests[name] = request;
            request.Request((bars, errorCode, errorMessage) =>
            {
                if (errorCode != ErrorCode.NoError)
                    Print("PythonFuturesBridge EMT request failed for " + name + ": " + errorMessage);
                else
                {
                    Print("PythonFuturesBridge EMT subscribed: " + name + " (" + EmtTickBars + "-tick, historical bars=" + bars.Bars.Count + ")");
                    SendEmtHistory(bars.Bars, instrument.FullName);
                }
            });
        }

        // Called by the watchdog when one symbol's 610-tick subscription has
        // gone silent for too long. Mirrors ResubscribeInstrument, but for a
        // single entry in emtRequests instead of the whole dictionary.
        private void ResubscribeEmtInstrument(string name)
        {
            BarsRequest oldRequest;
            if (emtRequests.TryRemove(name, out oldRequest) && oldRequest != null)
            {
                oldRequest.Update -= OnEmtBarsUpdate;
                oldRequest.Dispose();
            }
            SubscribeEmtInstrument(name);
        }

        private void OnEmtBarsUpdate(object sender, BarsUpdateEventArgs e)
        {
            try
            {
                if (e.BarsSeries == null || e.BarsSeries.Count < 2)
                    return;
                int liveIndex = e.BarsSeries.Count - 1;
                int liveCount = e.BarsSeries.Count;
                string symbol = e.BarsSeries.Instrument.FullName;
                string key = "EMT:" + symbol;
                lastUpdateUtc[key] = DateTime.UtcNow;
                if (updateSeen.TryAdd(key, 0))
                    Print("PythonFuturesBridge first EMT 610t BarsUpdate: " + symbol);
                int previousCount;
                if (!currentBarCounts.TryGetValue(key, out previousCount))
                {
                    currentBarCounts.TryAdd(key, liveCount);
                    return;
                }
                if (liveCount == previousCount)
                    return;
                if (!currentBarCounts.TryUpdate(key, liveCount, previousCount))
                    return;
                SendEmtBar(e.BarsSeries, liveIndex - 1, symbol, false);
                Print("PythonFuturesBridge EMT completed 610t bar queued: " + symbol + " " +
                      e.BarsSeries.GetTime(liveIndex - 1).ToString("yyyy-MM-dd HH:mm:ss"));
            }
            catch (Exception ex)
            {
                Print("PythonFuturesBridge EMT BarsUpdate failed: " + ex);
            }
        }

        private void SendEmtBar(BarsSeries bars, int index, string symbol, bool historical)
        {
            string json = BuildEmtJson(
                symbol, bars.GetTime(index), bars.GetOpen(index), bars.GetHigh(index),
                bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index), historical);
            EnqueueBoth(EmtPath, json, "emt");
        }

        private void SendEmtHistory(Bars bars, string symbol)
        {
            int lastCompleted = bars.Count - 2;
            int first = Math.Max(0, lastCompleted - 89);
            int queued = 0;
            for (int index = first; index <= lastCompleted && index < bars.Count; index++)
            {
                string json = BuildEmtJson(
                    symbol, bars.GetTime(index), bars.GetOpen(index), bars.GetHigh(index),
                    bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index), true);
                EnqueueLocalOnly(EmtPath, json, "emt-history");
                queued++;
            }
            Print("PythonFuturesBridge EMT history queued locally: " + symbol + " (" + queued + " bars)");
        }

        private void OnBarsUpdate(object sender, BarsUpdateEventArgs e)
        {
            try
            {
                if (e.BarsSeries == null || e.BarsSeries.Count < 2)
                    return;
                int liveIndex = e.BarsSeries.Count - 1;
                DateTime liveTime = e.BarsSeries.GetTime(liveIndex);
                string symbol = e.BarsSeries.Instrument.FullName;
                lastUpdateUtc[symbol] = DateTime.UtcNow;
                if (updateSeen.TryAdd(symbol, 0))
                    Print("PythonFuturesBridge first live BarsUpdate: " + symbol);
                DateTime previousTime;
                if (!currentBarTimes.TryGetValue(symbol, out previousTime))
                {
                    currentBarTimes.TryAdd(symbol, liveTime);
                    return;
                }
                if (liveTime == previousTime)
                    return;
                if (!currentBarTimes.TryUpdate(symbol, liveTime, previousTime))
                    return;
                SendBar(e.BarsSeries, liveIndex - 1, symbol);
                Print("PythonFuturesBridge completed bar queued: " + symbol + " " +
                      e.BarsSeries.GetTime(liveIndex - 1).ToString("yyyy-MM-dd HH:mm:ss"));
            }
            catch (Exception ex)
            {
                Print("PythonFuturesBridge BarsUpdate failed: " + ex);
            }
        }

        private void SendBar(BarsSeries bars, int index, string symbol)
        {
            string json = BuildJson(
                symbol, bars.GetTime(index), bars.GetOpen(index), bars.GetHigh(index),
                bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index), false);
            EnqueueBoth(BarPath, json, "bar");
        }

        private void SendHistory(Bars bars, string symbol)
        {
            int lastCompleted = bars.Count - 2;
            int first = Math.Max(0, lastCompleted - 89);
            int queued = 0;
            for (int index = first; index <= lastCompleted && index < bars.Count; index++)
            {
                string json = BuildJson(
                    symbol, bars.GetTime(index), bars.GetOpen(index), bars.GetHigh(index),
                    bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index), true);
                EnqueueLocalOnly(BarPath, json, "history");
                queued++;
            }
            Print("PythonFuturesBridge history queued locally: " + symbol + " (" + queued + " bars)");
        }

        private string BuildJson(string symbol, DateTime time, double open,
                                 double high, double low, double close, long volume,
                                 bool historical)
        {
            return string.Format(CultureInfo.InvariantCulture,
                "{{\"secret\":\"{0}\",\"source\":\"ninjatrader\",\"symbol\":\"{1}\"," +
                "\"historical\":{2},\"time\":\"{3:o}\",\"seconds\":60,\"open\":{4},\"high\":{5}," +
                "\"low\":{6},\"close\":{7},\"volume\":{8}}}",
                SharedSecret, symbol.Replace("\\", "\\\\").Replace("\"", "\\\""),
                historical ? "true" : "false", time, open, high, low, close, volume);
        }

        private string BuildEmtJson(string symbol, DateTime time, double open,
                                    double high, double low, double close,
                                    long volume, bool historical)
        {
            string rootSymbol = symbol.Split(' ')[0];
            return string.Format(CultureInfo.InvariantCulture,
                "{{\"secret\":\"{0}\",\"source\":\"ninjatrader\",\"symbol\":\"{1}\"," +
                "\"bar_type\":\"tick\",\"bar_value\":{2},\"complete\":true," +
                "\"historical\":{3},\"time\":\"{4:o}\",\"open\":{5}," +
                "\"high\":{6},\"low\":{7},\"close\":{8},\"volume\":{9}}}",
                SharedSecret, rootSymbol.Replace("\\", "\\\\").Replace("\"", "\\\""),
                EmtTickBars, historical ? "true" : "false",
                time, open, high, low, close, volume);
        }

        private bool PostJson(OutboundMessage msg, string host, string label)
        {
            string endpoint = host + msg.Path;
            byte[] body = Encoding.UTF8.GetBytes(msg.Json);
            bool isHeartbeat = msg.Kind == "heartbeat";
            DateTime startedUtc = DateTime.UtcNow;
            for (int attempt = 1; attempt <= 2; attempt++)
            {
                try
                {
                    HttpWebRequest request = (HttpWebRequest)WebRequest.Create(endpoint);
                    request.Method = "POST";
                    request.ContentType = "application/json";
                    request.ContentLength = body.Length;
                    request.Timeout = 5000;
                    using (Stream stream = request.GetRequestStream())
                        stream.Write(body, 0, body.Length);
                    using (HttpWebResponse response = (HttpWebResponse)request.GetResponse()) { }
                    if (isHeartbeat)
                    {
                        double elapsedMs = (DateTime.UtcNow - startedUtc).TotalMilliseconds;
                        Print(string.Format(CultureInfo.InvariantCulture,
                            "PythonFuturesBridge HEARTBEAT ok -> {0} @ {1:HH:mm:ss.fff} UTC ({2:F0}ms, attempt {3})",
                            label, DateTime.UtcNow, elapsedMs, attempt));
                    }
                    return true;
                }
                catch (Exception ex)
                {
                    if (attempt == 2 || isHeartbeat)
                    {
                        Print(string.Format(CultureInfo.InvariantCulture,
                            "PythonFuturesBridge {0} FAILED -> {1} @ {2:HH:mm:ss.fff} UTC attempt {3}/2: {4}: {5}",
                            msg.Kind.ToUpperInvariant(), label, DateTime.UtcNow, attempt, ex.GetType().Name, ex.Message));
                    }
                    if (attempt == 2)
                        return false;
                    Thread.Sleep(300);
                }
            }
            return false;
        }

        private void StopEmtSubscriptions()
        {
            foreach (BarsRequest request in emtRequests.Values)
            {
                request.Update -= OnEmtBarsUpdate;
                request.Dispose();
            }
            emtRequests.Clear();
        }

        private void StopSubscriptions()
        {
            foreach (BarsRequest request in requests.Values)
            {
                request.Update -= OnBarsUpdate;
                request.Dispose();
            }
            requests.Clear();
            currentBarTimes.Clear();
            updateSeen.Clear();
            lastUpdateUtc.Clear();
        }

        private void StartWatchdog()
        {
            StopWatchdog();
            // First check only after a full interval so freshly created
            // subscriptions have time to receive their initial Update before
            // being judged stale.
            watchdogTimer = new Timer(_ => CheckSubscriptionHealth(), null, WatchdogIntervalMs, WatchdogIntervalMs);
        }

        private void StopWatchdog()
        {
            Timer timer = Interlocked.Exchange(ref watchdogTimer, null);
            if (timer != null)
                timer.Dispose();
        }

        private void CheckSubscriptionHealth()
        {
            try
            {
                DateTime now = DateTime.UtcNow;
                foreach (string name in instruments)
                {
                    DateTime last;
                    if (!lastUpdateUtc.TryGetValue(name, out last))
                        continue;
                    if ((now - last).TotalMilliseconds <= StaleThresholdMs)
                        continue;
                    Print(string.Format(CultureInfo.InvariantCulture,
                        "PythonFuturesBridge: {0} silent for {1:F0}s; resubscribing.",
                        name, (now - last).TotalSeconds));
                    ResubscribeInstrument(name);
                }

                foreach (string name in instruments)
                {
                    string emtKey = "EMT:" + name;
                    DateTime lastEmt;
                    if (!lastUpdateUtc.TryGetValue(emtKey, out lastEmt))
                        continue;
                    if ((now - lastEmt).TotalMilliseconds <= StaleThresholdMs)
                        continue;
                    Print(string.Format(CultureInfo.InvariantCulture,
                        "PythonFuturesBridge: EMT {0} silent for {1:F0}s; resubscribing.",
                        name, (now - lastEmt).TotalSeconds));
                    ResubscribeEmtInstrument(name);
                }
            }
            catch (Exception ex)
            {
                Print("PythonFuturesBridge watchdog check failed: " + ex);
            }
        }
    }
}
