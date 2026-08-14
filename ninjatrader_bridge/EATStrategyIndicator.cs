// NinjaTrader 8 indicator for the Easy Access Trade (EAT) box-breakout setup.
// Apply to a 1-minute chart. Draws the session box only; the real
// entry/wick-stop/TP1/runner-trail logic lives in the backend eat_strategy.py
// engine (already tested/live). This indicator is a local visual aid; web_dash
// and VPS runtime state exclusively own backend enablement and configuration.
// Copy into Documents\NinjaTrader 8\bin\Custom\Indicators and compile.

using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;

namespace NinjaTrader.NinjaScript.Indicators
{
    public class EATStrategyIndicator : Indicator
    {
        private enum SetupPhase
        {
            BuildingBox,
            BoxReady,
            TradeWindow,
            SessionDone
        }

        private sealed class SessionCandidate
        {
            public string Name;
            public DateTime Start;
        }

        private SetupPhase phase;
        private string sessionKey;
        private string sessionName;
        private DateTime sessionStart;
        private double boxHigh;
        private double boxLow;
        private bool usedFallback;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Session box for the Easy Access Trade (EAT) setup. " +
                    "Local visual only -- entries/exits run server-side.";
                Name = "EAT Strategy Indicator";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = true;
                DrawOnPricePanel = true;
                IsSuspendedWhileInactive = true;

                EnableNY = true;
                NyStartHour = 5;
                NyStartMinute = 0;
                EnableTokyo = true;
                TokyoStartHour = 15;
                TokyoStartMinute = 00;
                EnableLondon = true;
                LondonStandardHour = 22;
                LondonStandardMinute = 30;
                LondonDstHour = 23;
                LondonDstMinute = 30;
                PrimaryBoxMinutes = 5;
                FallbackBoxMinutes = 15;
                MinBoxTicks = 100;
                MaxBoxTicks = 250;
                BufferTicks = 30;
                Tp1Ticks = 200;
                RunnerTrailTicks = 95;
                WickStopLookbackMinutes = 20;
                TradeWindowMinutes = 800;

                Enabled = false;
                Contracts = 20;
                MaxTradesPerSession = 20;
                AllowReentry = true;
                EnableLongs = true;
                EnableShorts = false;
                MaxStopTicks = 0;
                StopTicksOverride = 300;
            }
            else if (State == State.DataLoaded)
            {
                ResetSession(null, null, DateTime.MinValue);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
            {
                Draw.TextFixed(this, "EATWrongBars",
                    "EAT requires a 1-minute chart", TextPosition.TopLeft,
                    Brushes.White, new SimpleFont("Arial", 16), Brushes.DarkRed,
                    Brushes.DarkRed, 80);
                return;
            }

            if (CurrentBar < 1)
                return;

            DateTime now = Time[0];
            SessionCandidate candidate = FindActiveSession(now);
            if (candidate == null)
            {
                ShowStatus("Waiting for next EAT session (NY/Tokyo/London)");
                return;
            }

            string candidateKey = candidate.Name + ":" + candidate.Start.ToString("O");
            if (candidateKey != sessionKey)
                ResetSession(candidateKey, candidate.Name, candidate.Start);

            DateTime start = sessionStart;
            DateTime primaryEnd = start.AddMinutes(PrimaryBoxMinutes);
            DateTime fallbackEnd = start.AddMinutes(FallbackBoxMinutes);
            DateTime tradeEnd = (usedFallback ? fallbackEnd : primaryEnd)
                .AddMinutes(TradeWindowMinutes);

            if (now < start)
            {
                ShowStatus("Waiting for " + sessionName + " session start");
                return;
            }

            double boxTicks = (double.IsNaN(boxHigh) || double.IsNaN(boxLow))
                ? 0 : (boxHigh - boxLow) / TickSize;

            if (now >= start && now < primaryEnd)
            {
                boxHigh = double.IsNaN(boxHigh) ? High[0] : Math.Max(boxHigh, High[0]);
                boxLow = double.IsNaN(boxLow) ? Low[0] : Math.Min(boxLow, Low[0]);
                phase = SetupPhase.BuildingBox;
                DrawBoxLines();
                ShowStatus(sessionName + ": building primary box (" + PrimaryBoxMinutes + "m)");
                return;
            }

            if (!usedFallback && boxTicks < MinBoxTicks && now < fallbackEnd)
            {
                usedFallback = true;
            }

            if (usedFallback && now < fallbackEnd)
            {
                boxHigh = Math.Max(boxHigh, High[0]);
                boxLow = Math.Min(boxLow, Low[0]);
                phase = SetupPhase.BuildingBox;
                DrawBoxLines();
                ShowStatus(sessionName + ": box too tight, extending to fallback (" + FallbackBoxMinutes + "m)");
                return;
            }

            DrawBoxLines();

            if (now >= tradeEnd)
            {
                phase = SetupPhase.SessionDone;
                ShowStatus(sessionName + ": EAT trade window complete");
                return;
            }

            phase = boxTicks > MaxBoxTicks ? SetupPhase.SessionDone : SetupPhase.TradeWindow;
            ShowStatus(phase == SetupPhase.SessionDone
                ? sessionName + ": box too wide (" + boxTicks.ToString("0") + " ticks) -- session skipped"
                : sessionName + ": trade window open, box " + boxTicks.ToString("0") + " ticks");
        }

        // Picks whichever of NY/Tokyo/London is the most recent session start
        // that's still within its box+trade window, checking both today and
        // yesterday (a session that starts late in the evening chart-local
        // time can still be "active" past midnight).
        private SessionCandidate FindActiveSession(DateTime now)
        {
            SessionCandidate best = null;
            for (int dayOffset = -1; dayOffset <= 0; dayOffset++)
            {
                DateTime day = now.Date.AddDays(dayOffset);
                if (EnableNY)
                    ConsiderSession(ref best, now, "ny",
                        day.AddHours(NyStartHour).AddMinutes(NyStartMinute));
                if (EnableTokyo)
                    ConsiderSession(ref best, now, "tokyo",
                        day.AddHours(TokyoStartHour).AddMinutes(TokyoStartMinute));
                if (EnableLondon)
                {
                    bool dst = TimeZoneInfo.Local.IsDaylightSavingTime(day.AddHours(12));
                    int hour = dst ? LondonDstHour : LondonStandardHour;
                    int minute = dst ? LondonDstMinute : LondonStandardMinute;
                    ConsiderSession(ref best, now, "london",
                        day.AddHours(hour).AddMinutes(minute));
                }
            }
            return best;
        }

        private void ConsiderSession(ref SessionCandidate best, DateTime now,
            string name, DateTime start)
        {
            DateTime latestPossibleEnd = start
                .AddMinutes(FallbackBoxMinutes + TradeWindowMinutes);
            if (now < start || now > latestPossibleEnd)
                return;
            if (best == null || start > best.Start)
                best = new SessionCandidate { Name = name, Start = start };
        }

        private void ResetSession(string key, string name, DateTime start)
        {
            sessionKey = key;
            sessionName = name;
            sessionStart = start;
            phase = SetupPhase.BuildingBox;
            boxHigh = double.NaN;
            boxLow = double.NaN;
            usedFallback = false;
        }

        private void DrawBoxLines()
        {
            if (double.IsNaN(boxHigh) || double.IsNaN(boxLow) || sessionKey == null)
                return;
            string tag = sessionKey.Replace(":", "-").Replace(".", "-");
            Draw.HorizontalLine(this, "EATHigh" + tag, boxHigh,
                Brushes.OrangeRed, DashStyleHelper.Solid, 2);
            Draw.HorizontalLine(this, "EATLow" + tag, boxLow,
                Brushes.DodgerBlue, DashStyleHelper.Solid, 2);
            Draw.HorizontalLine(this, "EATTp1" + tag,
                boxHigh + Tp1Ticks * TickSize, Brushes.LimeGreen, DashStyleHelper.Dash, 1);
            Draw.HorizontalLine(this, "EATStop" + tag,
                boxLow - BufferTicks * TickSize, Brushes.DarkRed, DashStyleHelper.Dash, 1);
        }

        private void ShowStatus(string detail)
        {
            string range = double.IsNaN(boxHigh)
                ? "not set"
                : boxLow.ToString("0.00") + " - " + boxHigh.ToString("0.00");
            string text = "EAT " + Instrument.FullName + "\n" +
                "Session: " + (sessionName ?? "waiting") + "\n" +
                "State: " + phase + "\n" +
                "Box: " + range + "\n" +
                (Enabled ? "Backend: enabled" : "Backend: disabled") + "\n" + detail;
            Draw.TextFixed(this, "EATStatus", text, TextPosition.TopRight,
                Brushes.White, new SimpleFont("Consolas", 13),
                Brushes.Black, Brushes.Black, 55);
        }

        [NinjaScriptProperty]
        [Display(Name = "Enable New York", GroupName = "Sessions", Order = 1)]
        public bool EnableNY { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "NY start hour (chart local)", GroupName = "Sessions", Order = 2)]
        public int NyStartHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "NY start minute", GroupName = "Sessions", Order = 3)]
        public int NyStartMinute { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable Tokyo", GroupName = "Sessions", Order = 4)]
        public bool EnableTokyo { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "Tokyo start hour (chart local)", GroupName = "Sessions", Order = 5)]
        public int TokyoStartHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "Tokyo start minute", GroupName = "Sessions", Order = 6)]
        public int TokyoStartMinute { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable London", GroupName = "Sessions", Order = 7)]
        public bool EnableLondon { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "London standard hour (chart local)", GroupName = "Sessions", Order = 8)]
        public int LondonStandardHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "London standard minute", GroupName = "Sessions", Order = 9)]
        public int LondonStandardMinute { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "London DST hour (chart local)", GroupName = "Sessions", Order = 10)]
        public int LondonDstHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "London DST minute", GroupName = "Sessions", Order = 11)]
        public int LondonDstMinute { get; set; }

        [NinjaScriptProperty]
        [Range(1, 60)]
        [Display(Name = "Primary box minutes", GroupName = "Box", Order = 1)]
        public int PrimaryBoxMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 120)]
        [Display(Name = "Fallback box minutes", GroupName = "Box", Order = 2)]
        public int FallbackBoxMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 2000)]
        [Display(Name = "Min box ticks", GroupName = "Box", Order = 3)]
        public int MinBoxTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5000)]
        [Display(Name = "Max box ticks", GroupName = "Box", Order = 4)]
        public int MaxBoxTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1000)]
        [Display(Name = "Buffer ticks (stop)", GroupName = "Entry", Order = 1)]
        public int BufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 2000)]
        [Display(Name = "TP1 ticks", GroupName = "Entry", Order = 2)]
        public int Tp1Ticks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1000)]
        [Display(Name = "Runner trail ticks", GroupName = "Entry", Order = 3)]
        public int RunnerTrailTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 120)]
        [Display(Name = "Wick stop lookback minutes", GroupName = "Entry", Order = 4)]
        public int WickStopLookbackMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 600)]
        [Display(Name = "Trade window minutes", GroupName = "Session", Order = 1)]
        public int TradeWindowMinutes { get; set; }

        // Backend control: this indicator is the on/off switch and settings
        // source for this symbol's live EAT paper-trading engine, including
        // the NY/Tokyo/London session start times above -- applying it to a
        // chart with Enabled=true (and clicking OK) pushes all of this as the
        // engine's config. See ninja_futures_scanner.py's
        // configure_strategy()/_replace_engine().
        [NinjaScriptProperty]
        [Display(Name = "Enabled (controls backend EAT engine)", GroupName = "Backend Control", Order = 1)]
        public bool Enabled { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Contracts", GroupName = "Backend Control", Order = 2)]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Max trades per session", GroupName = "Backend Control", Order = 3)]
        public int MaxTradesPerSession { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow re-entry", GroupName = "Backend Control", Order = 4)]
        public bool AllowReentry { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable longs", GroupName = "Backend Control", Order = 5)]
        public bool EnableLongs { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable shorts", GroupName = "Backend Control", Order = 6)]
        public bool EnableShorts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "Max stop ticks (0 = off)", GroupName = "Backend Control", Order = 7)]
        public int MaxStopTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "Stop ticks override (0 = off)", GroupName = "Backend Control", Order = 8)]
        public int StopTicksOverride { get; set; }
    }
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private EATStrategyIndicator[] cacheEATStrategyIndicator;
		public EATStrategyIndicator EATStrategyIndicator(bool enableNY, int nyStartHour, int nyStartMinute, bool enableTokyo, int tokyoStartHour, int tokyoStartMinute, bool enableLondon, int londonStandardHour, int londonStandardMinute, int londonDstHour, int londonDstMinute, int primaryBoxMinutes, int fallbackBoxMinutes, int minBoxTicks, int maxBoxTicks, int bufferTicks, int tp1Ticks, int runnerTrailTicks, int wickStopLookbackMinutes, int tradeWindowMinutes, bool enabled, int contracts, int maxTradesPerSession, bool allowReentry, bool enableLongs, bool enableShorts, int maxStopTicks, int stopTicksOverride)
		{
			return EATStrategyIndicator(Input, enableNY, nyStartHour, nyStartMinute, enableTokyo, tokyoStartHour, tokyoStartMinute, enableLondon, londonStandardHour, londonStandardMinute, londonDstHour, londonDstMinute, primaryBoxMinutes, fallbackBoxMinutes, minBoxTicks, maxBoxTicks, bufferTicks, tp1Ticks, runnerTrailTicks, wickStopLookbackMinutes, tradeWindowMinutes, enabled, contracts, maxTradesPerSession, allowReentry, enableLongs, enableShorts, maxStopTicks, stopTicksOverride);
		}

		public EATStrategyIndicator EATStrategyIndicator(ISeries<double> input, bool enableNY, int nyStartHour, int nyStartMinute, bool enableTokyo, int tokyoStartHour, int tokyoStartMinute, bool enableLondon, int londonStandardHour, int londonStandardMinute, int londonDstHour, int londonDstMinute, int primaryBoxMinutes, int fallbackBoxMinutes, int minBoxTicks, int maxBoxTicks, int bufferTicks, int tp1Ticks, int runnerTrailTicks, int wickStopLookbackMinutes, int tradeWindowMinutes, bool enabled, int contracts, int maxTradesPerSession, bool allowReentry, bool enableLongs, bool enableShorts, int maxStopTicks, int stopTicksOverride)
		{
			if (cacheEATStrategyIndicator != null)
				for (int idx = 0; idx < cacheEATStrategyIndicator.Length; idx++)
					if (cacheEATStrategyIndicator[idx] != null && cacheEATStrategyIndicator[idx].EnableNY == enableNY && cacheEATStrategyIndicator[idx].NyStartHour == nyStartHour && cacheEATStrategyIndicator[idx].NyStartMinute == nyStartMinute && cacheEATStrategyIndicator[idx].EnableTokyo == enableTokyo && cacheEATStrategyIndicator[idx].TokyoStartHour == tokyoStartHour && cacheEATStrategyIndicator[idx].TokyoStartMinute == tokyoStartMinute && cacheEATStrategyIndicator[idx].EnableLondon == enableLondon && cacheEATStrategyIndicator[idx].LondonStandardHour == londonStandardHour && cacheEATStrategyIndicator[idx].LondonStandardMinute == londonStandardMinute && cacheEATStrategyIndicator[idx].LondonDstHour == londonDstHour && cacheEATStrategyIndicator[idx].LondonDstMinute == londonDstMinute && cacheEATStrategyIndicator[idx].PrimaryBoxMinutes == primaryBoxMinutes && cacheEATStrategyIndicator[idx].FallbackBoxMinutes == fallbackBoxMinutes && cacheEATStrategyIndicator[idx].MinBoxTicks == minBoxTicks && cacheEATStrategyIndicator[idx].MaxBoxTicks == maxBoxTicks && cacheEATStrategyIndicator[idx].BufferTicks == bufferTicks && cacheEATStrategyIndicator[idx].Tp1Ticks == tp1Ticks && cacheEATStrategyIndicator[idx].RunnerTrailTicks == runnerTrailTicks && cacheEATStrategyIndicator[idx].WickStopLookbackMinutes == wickStopLookbackMinutes && cacheEATStrategyIndicator[idx].TradeWindowMinutes == tradeWindowMinutes && cacheEATStrategyIndicator[idx].Enabled == enabled && cacheEATStrategyIndicator[idx].Contracts == contracts && cacheEATStrategyIndicator[idx].MaxTradesPerSession == maxTradesPerSession && cacheEATStrategyIndicator[idx].AllowReentry == allowReentry && cacheEATStrategyIndicator[idx].EnableLongs == enableLongs && cacheEATStrategyIndicator[idx].EnableShorts == enableShorts && cacheEATStrategyIndicator[idx].MaxStopTicks == maxStopTicks && cacheEATStrategyIndicator[idx].StopTicksOverride == stopTicksOverride && cacheEATStrategyIndicator[idx].EqualsInput(input))
						return cacheEATStrategyIndicator[idx];
			return CacheIndicator<EATStrategyIndicator>(new EATStrategyIndicator(){ EnableNY = enableNY, NyStartHour = nyStartHour, NyStartMinute = nyStartMinute, EnableTokyo = enableTokyo, TokyoStartHour = tokyoStartHour, TokyoStartMinute = tokyoStartMinute, EnableLondon = enableLondon, LondonStandardHour = londonStandardHour, LondonStandardMinute = londonStandardMinute, LondonDstHour = londonDstHour, LondonDstMinute = londonDstMinute, PrimaryBoxMinutes = primaryBoxMinutes, FallbackBoxMinutes = fallbackBoxMinutes, MinBoxTicks = minBoxTicks, MaxBoxTicks = maxBoxTicks, BufferTicks = bufferTicks, Tp1Ticks = tp1Ticks, RunnerTrailTicks = runnerTrailTicks, WickStopLookbackMinutes = wickStopLookbackMinutes, TradeWindowMinutes = tradeWindowMinutes, Enabled = enabled, Contracts = contracts, MaxTradesPerSession = maxTradesPerSession, AllowReentry = allowReentry, EnableLongs = enableLongs, EnableShorts = enableShorts, MaxStopTicks = maxStopTicks, StopTicksOverride = stopTicksOverride }, input, ref cacheEATStrategyIndicator);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.EATStrategyIndicator EATStrategyIndicator(bool enableNY, int nyStartHour, int nyStartMinute, bool enableTokyo, int tokyoStartHour, int tokyoStartMinute, bool enableLondon, int londonStandardHour, int londonStandardMinute, int londonDstHour, int londonDstMinute, int primaryBoxMinutes, int fallbackBoxMinutes, int minBoxTicks, int maxBoxTicks, int bufferTicks, int tp1Ticks, int runnerTrailTicks, int wickStopLookbackMinutes, int tradeWindowMinutes, bool enabled, int contracts, int maxTradesPerSession, bool allowReentry, bool enableLongs, bool enableShorts, int maxStopTicks, int stopTicksOverride)
		{
			return indicator.EATStrategyIndicator(Input, enableNY, nyStartHour, nyStartMinute, enableTokyo, tokyoStartHour, tokyoStartMinute, enableLondon, londonStandardHour, londonStandardMinute, londonDstHour, londonDstMinute, primaryBoxMinutes, fallbackBoxMinutes, minBoxTicks, maxBoxTicks, bufferTicks, tp1Ticks, runnerTrailTicks, wickStopLookbackMinutes, tradeWindowMinutes, enabled, contracts, maxTradesPerSession, allowReentry, enableLongs, enableShorts, maxStopTicks, stopTicksOverride);
		}

		public Indicators.EATStrategyIndicator EATStrategyIndicator(ISeries<double> input , bool enableNY, int nyStartHour, int nyStartMinute, bool enableTokyo, int tokyoStartHour, int tokyoStartMinute, bool enableLondon, int londonStandardHour, int londonStandardMinute, int londonDstHour, int londonDstMinute, int primaryBoxMinutes, int fallbackBoxMinutes, int minBoxTicks, int maxBoxTicks, int bufferTicks, int tp1Ticks, int runnerTrailTicks, int wickStopLookbackMinutes, int tradeWindowMinutes, bool enabled, int contracts, int maxTradesPerSession, bool allowReentry, bool enableLongs, bool enableShorts, int maxStopTicks, int stopTicksOverride)
		{
			return indicator.EATStrategyIndicator(input, enableNY, nyStartHour, nyStartMinute, enableTokyo, tokyoStartHour, tokyoStartMinute, enableLondon, londonStandardHour, londonStandardMinute, londonDstHour, londonDstMinute, primaryBoxMinutes, fallbackBoxMinutes, minBoxTicks, maxBoxTicks, bufferTicks, tp1Ticks, runnerTrailTicks, wickStopLookbackMinutes, tradeWindowMinutes, enabled, contracts, maxTradesPerSession, allowReentry, enableLongs, enableShorts, maxStopTicks, stopTicksOverride);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.EATStrategyIndicator EATStrategyIndicator(bool enableNY, int nyStartHour, int nyStartMinute, bool enableTokyo, int tokyoStartHour, int tokyoStartMinute, bool enableLondon, int londonStandardHour, int londonStandardMinute, int londonDstHour, int londonDstMinute, int primaryBoxMinutes, int fallbackBoxMinutes, int minBoxTicks, int maxBoxTicks, int bufferTicks, int tp1Ticks, int runnerTrailTicks, int wickStopLookbackMinutes, int tradeWindowMinutes, bool enabled, int contracts, int maxTradesPerSession, bool allowReentry, bool enableLongs, bool enableShorts, int maxStopTicks, int stopTicksOverride)
		{
			return indicator.EATStrategyIndicator(Input, enableNY, nyStartHour, nyStartMinute, enableTokyo, tokyoStartHour, tokyoStartMinute, enableLondon, londonStandardHour, londonStandardMinute, londonDstHour, londonDstMinute, primaryBoxMinutes, fallbackBoxMinutes, minBoxTicks, maxBoxTicks, bufferTicks, tp1Ticks, runnerTrailTicks, wickStopLookbackMinutes, tradeWindowMinutes, enabled, contracts, maxTradesPerSession, allowReentry, enableLongs, enableShorts, maxStopTicks, stopTicksOverride);
		}

		public Indicators.EATStrategyIndicator EATStrategyIndicator(ISeries<double> input , bool enableNY, int nyStartHour, int nyStartMinute, bool enableTokyo, int tokyoStartHour, int tokyoStartMinute, bool enableLondon, int londonStandardHour, int londonStandardMinute, int londonDstHour, int londonDstMinute, int primaryBoxMinutes, int fallbackBoxMinutes, int minBoxTicks, int maxBoxTicks, int bufferTicks, int tp1Ticks, int runnerTrailTicks, int wickStopLookbackMinutes, int tradeWindowMinutes, bool enabled, int contracts, int maxTradesPerSession, bool allowReentry, bool enableLongs, bool enableShorts, int maxStopTicks, int stopTicksOverride)
		{
			return indicator.EATStrategyIndicator(input, enableNY, nyStartHour, nyStartMinute, enableTokyo, tokyoStartHour, tokyoStartMinute, enableLondon, londonStandardHour, londonStandardMinute, londonDstHour, londonDstMinute, primaryBoxMinutes, fallbackBoxMinutes, minBoxTicks, maxBoxTicks, bufferTicks, tp1Ticks, runnerTrailTicks, wickStopLookbackMinutes, tradeWindowMinutes, enabled, contracts, maxTradesPerSession, allowReentry, enableLongs, enableShorts, maxStopTicks, stopTicksOverride);
		}
	}
}

#endregion
