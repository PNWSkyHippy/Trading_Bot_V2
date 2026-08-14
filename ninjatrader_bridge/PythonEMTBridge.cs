// NinjaTrader 8 AddOn: ES 610-tick data bridge for the local EMT paper engine.
// This AddOn sends market data only. It contains no account or order access.

using System;
using System.Collections.Concurrent;
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
    public class PythonEMTBridge : AddOnBase
    {
        // Two independent destinations on two different local ports so a dead
        // or flapping Hostinger tunnel can never block or delay delivery to the
        // always-local scanner. See PythonFuturesBridge.cs for the same pattern
        // and Scripts/run_emt_hostinger_tunnel.ps1 for the tunnel side (it
        // forwards local 8766 -> the VPS's own 8765).
        private const string LocalEndpoint = "http://127.0.0.1:8765/ingest/emt/bar";
        private const string HostingerEndpoint = "http://127.0.0.1:8766/ingest/emt/bar";
        // Set this to the same value as ninja_futures_config.json.
        private const string SharedSecret = "okay-so-i-changed-secret";
        private const string InstrumentName = "ES 09-26";
        private const int TickBarSize = 610;
        private const int SnapshotIntervalMs = 150;
        private const int HistoryBars = 120;

        private readonly BlockingCollection<string> localOutbound =
            new BlockingCollection<string>(500);
        private readonly BlockingCollection<string> hostingerOutbound =
            new BlockingCollection<string>(500);
        private BarsRequest request;
        private Thread localSenderThread;
        private Thread hostingerSenderThread;
        private DateTime currentBarTime = DateTime.MinValue;
        private DateTime lastSnapshotUtc = DateTime.MinValue;
        private volatile bool stopping;

        protected override void OnStateChange()
        {
            // Disabled: PythonFuturesBridge.cs already subscribes to the same
            // ES 610-tick EMT feed and posts to the same two endpoints, with
            // real retry/requeue logic instead of this addon's single
            // 1.5s-timeout, zero-retry PostJson. Running both risked the
            // ingest endpoint receiving duplicate bar submissions for the
            // same symbol/time, and this one was the sole source of the
            // "send failed -> hostinger" spam since it gives up instantly on
            // any tunnel blip. Left in place (not deleted) in case
            // PythonFuturesBridge.cs is ever retired and this needs reviving.
        }

        private void StartSender()
        {
            stopping = false;
            localSenderThread = new Thread(() => SenderLoop(localOutbound, LocalEndpoint, "local"));
            localSenderThread.IsBackground = true;
            localSenderThread.Name = "PythonEMTBridgeLocalSender";
            localSenderThread.Start();

            hostingerSenderThread = new Thread(() => SenderLoop(hostingerOutbound, HostingerEndpoint, "hostinger"));
            hostingerSenderThread.IsBackground = true;
            hostingerSenderThread.Name = "PythonEMTBridgeHostingerSender";
            hostingerSenderThread.Start();
        }

        private void StopSender()
        {
            stopping = true;
            localOutbound.CompleteAdding();
            hostingerOutbound.CompleteAdding();
            if (localSenderThread != null && localSenderThread.IsAlive)
                localSenderThread.Join(2000);
            if (hostingerSenderThread != null && hostingerSenderThread.IsAlive)
                hostingerSenderThread.Join(2000);
            localSenderThread = null;
            hostingerSenderThread = null;
        }

        private void SenderLoop(BlockingCollection<string> outbound, string endpoint, string label)
        {
            foreach (string json in outbound.GetConsumingEnumerable())
            {
                if (stopping)
                    break;
                PostJson(json, endpoint, label);
            }
        }

        private void QueueJson(string json)
        {
            if (stopping)
                return;
            if (!localOutbound.IsAddingCompleted && !localOutbound.TryAdd(json))
                Print("PythonEMTBridge local queue full; snapshot dropped");
            if (!hostingerOutbound.IsAddingCompleted && !hostingerOutbound.TryAdd(json))
                Print("PythonEMTBridge hostinger queue full; snapshot dropped");
        }

        private void StartSubscription()
        {
            Instrument instrument = Instrument.GetInstrument(InstrumentName);
            if (instrument == null)
            {
                Print("PythonEMTBridge instrument not found: " + InstrumentName);
                return;
            }

            request = new BarsRequest(instrument, 500);
            request.BarsPeriod = new BarsPeriod {
                BarsPeriodType = BarsPeriodType.Tick,
                Value = TickBarSize
            };
            request.TradingHours = TradingHours.Get("Default 24 x 7");
            request.Update += OnBarsUpdate;
            request.Request((bars, errorCode, errorMessage) =>
            {
                if (errorCode != ErrorCode.NoError)
                {
                    Print("PythonEMTBridge request failed: " + errorMessage);
                    return;
                }

                int lastCompleted = bars.Bars.Count - 2;
                int first = Math.Max(0, lastCompleted - HistoryBars + 1);
                for (int index = first; index <= lastCompleted; index++)
                    QueueJson(BuildJson(bars.Bars, index, true, true));

                if (bars.Bars.Count > 0)
                    currentBarTime = bars.Bars.GetTime(bars.Bars.Count - 1);

                Print("PythonEMTBridge subscribed: " + InstrumentName +
                      " (610-tick, history=" + Math.Max(0, lastCompleted - first + 1) + ")");
            });
        }

        private void OnBarsUpdate(object sender, BarsUpdateEventArgs e)
        {
            try
            {
                if (e.BarsSeries == null || e.BarsSeries.Count < 1)
                    return;

                int currentIndex = e.BarsSeries.Count - 1;
                DateTime latestTime = e.BarsSeries.GetTime(currentIndex);

                if (currentBarTime == DateTime.MinValue)
                    currentBarTime = latestTime;

                if (latestTime != currentBarTime)
                {
                    int completedIndex = currentIndex - 1;
                    if (completedIndex >= 0)
                        QueueJson(BuildJson(e.BarsSeries, completedIndex, true, false));
                    currentBarTime = latestTime;
                }

                DateTime now = DateTime.UtcNow;
                if ((now - lastSnapshotUtc).TotalMilliseconds >= SnapshotIntervalMs)
                {
                    lastSnapshotUtc = now;
                    QueueJson(BuildJson(e.BarsSeries, currentIndex, false, false));
                }
            }
            catch (Exception ex)
            {
                Print("PythonEMTBridge BarsUpdate failed: " + ex.Message);
            }
        }

        private string BuildJson(Bars bars, int index, bool complete, bool historical)
        {
            return BuildJson(bars.Instrument.FullName, bars.GetTime(index),
                complete, historical, bars.GetOpen(index), bars.GetHigh(index),
                bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index));
        }

        // BarsRequest history callbacks hand back a Bars object, but the live
        // OnBarsUpdate event hands back a BarsSeries - a different, unrelated
        // type in the NT8 API with no implicit conversion between them. Both
        // expose the same GetOpen/GetHigh/GetLow/GetClose/GetVolume/GetTime
        // accessors, so this overload just mirrors the one above for that type.
        private string BuildJson(BarsSeries bars, int index, bool complete, bool historical)
        {
            return BuildJson(bars.Instrument.FullName, bars.GetTime(index),
                complete, historical, bars.GetOpen(index), bars.GetHigh(index),
                bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index));
        }

        private string BuildJson(string symbol, DateTime time, bool complete, bool historical,
            double open, double high, double low, double close, double volume)
        {
            return string.Format(CultureInfo.InvariantCulture,
                "{{\"secret\":\"{0}\",\"source\":\"ninjatrader\"," +
                "\"symbol\":\"{1}\",\"time\":\"{2:o}\"," +
                "\"bar_type\":\"tick\",\"bar_value\":{3}," +
                "\"complete\":{4},\"historical\":{5}," +
                "\"open\":{6},\"high\":{7},\"low\":{8}," +
                "\"close\":{9},\"volume\":{10}}}",
                SharedSecret,
                symbol.Replace("\\", "\\\\").Replace("\"", "\\\""),
                time, TickBarSize,
                complete ? "true" : "false",
                historical ? "true" : "false",
                open, high, low, close, volume);
        }

        private void PostJson(string json, string endpoint, string label)
        {
            try
            {
                byte[] body = Encoding.UTF8.GetBytes(json);
                HttpWebRequest http = (HttpWebRequest)WebRequest.Create(endpoint);
                http.Method = "POST";
                http.ContentType = "application/json";
                http.ContentLength = body.Length;
                http.Timeout = 1500;
                using (Stream stream = http.GetRequestStream())
                    stream.Write(body, 0, body.Length);
                using (HttpWebResponse response = (HttpWebResponse)http.GetResponse()) { }
            }
            catch (Exception ex)
            {
                Print(string.Format(CultureInfo.InvariantCulture,
                    "PythonEMTBridge send failed -> {0} @ {1:HH:mm:ss.fff} UTC: {2}: {3}",
                    label, DateTime.UtcNow, ex.GetType().Name, ex.Message));
            }
        }

        private void StopSubscription()
        {
            if (request != null)
            {
                request.Update -= OnBarsUpdate;
                request.Dispose();
                request = null;
            }
        }
    }
}
