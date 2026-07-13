// NinjaTrader 8 AddOn: read-only completed-bar bridge to a local Python scanner.
// Copy this file into Documents\NinjaTrader 8\bin\Custom\AddOns and compile.

using System;
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
        private const string Endpoint = "http://127.0.0.1:8765/ingest/bar";
        // Change this in both this file and ninja_futures_config.json.
        private const string SharedSecret = "change-this-local-secret";

        // Explicit active contracts are required for reliable live subscriptions.
        private readonly string[] instruments = {
            "MES 09-26", "ES 09-26",
            "MNQ 09-26", "NQ 09-26",
            "MYM 09-26", "YM 09-26",
            "M2K 09-26", "RTY 09-26",
            "MGC 08-26", "QO 08-26", "GC 08-26"
        };
        private readonly List<BarsRequest> requests = new List<BarsRequest>();
        private readonly Dictionary<string, DateTime> currentBarTimes = new Dictionary<string, DateTime>();
        private readonly HashSet<string> updateSeen = new HashSet<string>();

        protected override void OnStateChange()
        {
            if (State == State.Active)
                StartSubscriptions();
            else if (State == State.Terminated)
                StopSubscriptions();
        }

        private void StartSubscriptions()
        {
            foreach (string name in instruments)
            {
                Instrument instrument = Instrument.GetInstrument(name);
                if (instrument == null)
                {
                    Print("PythonFuturesBridge: instrument not found: " + name);
                    continue;
                }

                BarsRequest request = new BarsRequest(instrument, 500);
                request.BarsPeriod = new BarsPeriod { BarsPeriodType = BarsPeriodType.Minute, Value = 1 };
                request.TradingHours = TradingHours.Get("Default 24 x 7");
                request.Update += OnBarsUpdate;
                requests.Add(request);
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
        }

        private void OnBarsUpdate(object sender, BarsUpdateEventArgs e)
        {
            if (e.BarsSeries == null || e.BarsSeries.Count < 2)
                return;
            int liveIndex = e.BarsSeries.Count - 1;
            DateTime liveTime = e.BarsSeries.GetTime(liveIndex);
            string symbol = e.BarsSeries.Instrument.FullName;
            if (!updateSeen.Contains(symbol))
            {
                updateSeen.Add(symbol);
                Print("PythonFuturesBridge first live BarsUpdate: " + symbol);
            }
            DateTime previousTime;
            if (!currentBarTimes.TryGetValue(symbol, out previousTime))
            {
                currentBarTimes[symbol] = liveTime;
                return;
            }
            if (liveTime == previousTime)
                return;
            currentBarTimes[symbol] = liveTime;
            SendBar(e.BarsSeries, liveIndex - 1, symbol);
        }

        private void SendBar(BarsSeries bars, int index, string symbol)
        {
            string json = BuildJson(
                symbol, bars.GetTime(index), bars.GetOpen(index), bars.GetHigh(index),
                bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index));
            ThreadPool.QueueUserWorkItem(_ => PostJson(json));
        }

        private void SendHistory(Bars bars, string symbol)
        {
            int lastCompleted = bars.Count - 2;
            int first = Math.Max(0, lastCompleted - 89);
            ThreadPool.QueueUserWorkItem(_ =>
            {
                for (int index = first; index <= lastCompleted; index++)
                {
                    string json = BuildJson(
                        symbol, bars.GetTime(index), bars.GetOpen(index), bars.GetHigh(index),
                        bars.GetLow(index), bars.GetClose(index), bars.GetVolume(index));
                    if (!PostJson(json))
                        break;
                }
                Print("PythonFuturesBridge history sent: " + symbol + " (up to 90 bars)");
            });
        }

        private string BuildJson(string symbol, DateTime time, double open,
                                 double high, double low, double close, long volume)
        {
            return string.Format(CultureInfo.InvariantCulture,
                "{{\"secret\":\"{0}\",\"source\":\"ninjatrader\",\"symbol\":\"{1}\"," +
                "\"time\":\"{2:o}\",\"seconds\":60,\"open\":{3},\"high\":{4}," +
                "\"low\":{5},\"close\":{6},\"volume\":{7}}}",
                SharedSecret, symbol.Replace("\\", "\\\\").Replace("\"", "\\\""),
                time, open, high, low, close, volume);
        }

        private bool PostJson(string json)
        {
            try
            {
                byte[] body = Encoding.UTF8.GetBytes(json);
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(Endpoint);
                request.Method = "POST";
                request.ContentType = "application/json";
                request.ContentLength = body.Length;
                request.Timeout = 1500;
                using (Stream stream = request.GetRequestStream())
                    stream.Write(body, 0, body.Length);
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse()) { }
                return true;
            }
            catch (Exception ex)
            {
                Print("PythonFuturesBridge send failed: " + ex.Message);
                return false;
            }
        }

        private void StopSubscriptions()
        {
            foreach (BarsRequest request in requests)
            {
                request.Update -= OnBarsUpdate;
                request.Dispose();
            }
            requests.Clear();
            currentBarTimes.Clear();
            updateSeen.Clear();
        }
    }
}
