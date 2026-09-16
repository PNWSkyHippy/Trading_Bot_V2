// NinjaTrader 8 AddOn: one-shot historical futures bar exporter for backtesting.
// Copy into Documents\NinjaTrader 8\bin\Custom\AddOns and compile.
//
// On load, requests as much 1-minute history as the connected data feed will
// return for each instrument below and writes it to a CSV per symbol. Each
// instrument is skipped if its output file already exists, so recompiling or
// restarting NinjaTrader doesn't re-fetch data you already have -- delete a
// symbol's CSV if you want it re-pulled.
//
// Note: each entry below is a specific contract month (e.g. "ES 09-26"), not a
// stitched continuous series -- history is limited to however long that one
// contract has been listed/traded, not multiple years back. Ask if you want a
// continuous-contract version instead.

using System;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;

namespace NinjaTrader.NinjaScript.AddOns
{
    public class HistoricalFuturesExporter : AddOnBase
    {
        private const string OutputDir = @"C:\Users\Linda\trading_bot_v2\data\futures_history";

        private readonly string[] instruments = {
            "MES 09-26", "ES 12-26",
            "MNQ 12-26", "NQ 09-26",
            "MYM 09-26", "YM 09-26", 
            "M2K 09-26", "RTY 09-26",
            "MGC 12-26", "GC 12-26", "MNK 09-26",
            "NKD 09-26", "MBT 09-26", "MET 09-26"
        };

        protected override void OnStateChange()
        {
            if (State == State.Active)
            {
                try
                {
                    Directory.CreateDirectory(OutputDir);
                }
                catch (Exception ex)
                {
                    Print("HistoricalFuturesExporter: could not create output dir: " + ex);
                    return;
                }
                foreach (string name in instruments)
                    ExportInstrument(name);
            }
        }

        private void ExportInstrument(string name)
        {
            string root = name.Split(' ')[0];
            string path = Path.Combine(OutputDir, root + "_1min.csv");
            if (File.Exists(path))
            {
                Print("HistoricalFuturesExporter: " + root + " already exported, skipping (" + path + ")");
                return;
            }

            Instrument instrument = Instrument.GetInstrument(name);
            if (instrument == null)
            {
                Print("HistoricalFuturesExporter: instrument not found: " + name);
                return;
            }

            Print("HistoricalFuturesExporter: requesting history for " + root + "...");
            BarsRequest request = new BarsRequest(instrument, DateTime.Now.AddYears(-5), DateTime.Now);
            request.BarsPeriod = new BarsPeriod { BarsPeriodType = BarsPeriodType.Minute, Value = 1 };
            request.TradingHours = TradingHours.Get("Default 24 x 7");
            request.Request((bars, errorCode, errorMessage) =>
            {
                if (errorCode != ErrorCode.NoError)
                {
                    Print("HistoricalFuturesExporter: request failed for " + root + ": " + errorMessage);
                    return;
                }
                WriteCsv(path, root, bars.Bars);
            });
        }

        private void WriteCsv(string path, string symbol, Bars bars)
        {
            try
            {
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("symbol,time,open,high,low,close,volume");
                for (int i = 0; i < bars.Count; i++)
                {
                    sb.AppendLine(string.Format(CultureInfo.InvariantCulture,
                        "{0},{1:o},{2},{3},{4},{5},{6}",
                        symbol,
                        bars.GetTime(i),
                        bars.GetOpen(i),
                        bars.GetHigh(i),
                        bars.GetLow(i),
                        bars.GetClose(i),
                        bars.GetVolume(i)));
                }
                File.WriteAllText(path, sb.ToString());
                Print("HistoricalFuturesExporter: wrote " + bars.Count + " bars for " + symbol + " -> " + path);
            }
            catch (Exception ex)
            {
                Print("HistoricalFuturesExporter: write failed for " + symbol + ": " + ex);
            }
        }
    }
}
