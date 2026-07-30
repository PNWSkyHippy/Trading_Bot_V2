// NinjaTrader 8 indicator for the Easy Money Trade (EMT) setup.
// Apply to any 610-tick chart. Advisory only: draws and alerts, no orders.

using System;
using System.Collections.Generic;
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
    public class EMTStrategyIndicator : Indicator
    {
        private enum SetupPhase
        {
            BuildingRange,
            WaitingBreakout,
            WaitingRetrace,
            RetraceTouched,
            Ready,
            SessionDone
        }

        private SetupPhase phase;
        private DateTime sessionDate;
        private double openingHigh;
        private double openingLow;
        private double supportLevel;
        private double resistanceLevel;
        private double breakoutExtreme;
        private double lastPrice;
        private int direction; // -1 short, +1 long
        private int setupStartBar;
        private bool retraceSeen;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Opening-range/Keltner retracement alerts for the Easy Money Trade setup.";
                Name = "EMT Strategy Indicator";
                Calculate = Calculate.OnEachTick;
                IsOverlay = true;
                DisplayInDataBox = true;
                DrawOnPricePanel = true;
                IsSuspendedWhileInactive = true;

                OpeningStartHour = 5;
                OpeningStartMinute = 0;
                OpeningRangeMinutes = 15;
                TradeWindowMinutes = 60;
                KeltnerEmaPeriod = 20;
                KeltnerAtrPeriod = 10;
                KeltnerAtrMultiplier = 1.5;
                RetraceToleranceTicks = 1;
                ConfirmationTicks = 1;
                PatternLookbackBars = 20;
                PatternTolerancePoints = 1.0;
                PatternNecklinePoints = 1.0;

                AddPlot(Brushes.Gold, "KeltnerMidline");
                AddPlot(Brushes.DimGray, "KeltnerUpper");
                AddPlot(Brushes.DimGray, "KeltnerLower");
            }
            else if (State == State.DataLoaded)
            {
                ResetSession(DateTime.MinValue);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Tick || BarsPeriod.Value != 610)
            {
                Draw.TextFixed(this, "EMTWrongBars",
                    "EMT requires a 610-tick chart", TextPosition.TopLeft,
                    Brushes.White, new SimpleFont("Arial", 16), Brushes.DarkRed,
                    Brushes.DarkRed, 80);
                return;
            }

            if (CurrentBar < Math.Max(KeltnerEmaPeriod, KeltnerAtrPeriod) + 2)
                return;

            if (sessionDate != Time[0].Date)
                ResetSession(Time[0].Date);

            double midline = EMA(KeltnerEmaPeriod)[0];
            double channelDistance = ATR(KeltnerAtrPeriod)[0] * KeltnerAtrMultiplier;
            Values[0][0] = midline;
            Values[1][0] = midline + channelDistance;
            Values[2][0] = midline - channelDistance;

            DateTime start = Time[0].Date
                .AddHours(OpeningStartHour)
                .AddMinutes(OpeningStartMinute);
            DateTime rangeEnd = start.AddMinutes(OpeningRangeMinutes);
            DateTime tradeEnd = rangeEnd.AddMinutes(TradeWindowMinutes);

            if (Time[0] >= start && Time[0] < rangeEnd)
            {
                openingHigh = double.IsNaN(openingHigh) ? High[0] : Math.Max(openingHigh, High[0]);
                openingLow = double.IsNaN(openingLow) ? Low[0] : Math.Min(openingLow, Low[0]);
                phase = SetupPhase.BuildingRange;
                DrawRangeLines();
                ShowStatus(midline, "Building 15-minute opening range");
                lastPrice = Close[0];
                return;
            }

            if (Time[0] < rangeEnd || double.IsNaN(openingHigh) || double.IsNaN(openingLow))
            {
                ShowStatus(midline, "Waiting for opening range data");
                return;
            }

            if (double.IsNaN(resistanceLevel))
            {
                resistanceLevel = openingHigh;
                supportLevel = openingLow;
                phase = SetupPhase.WaitingBreakout;
            }
            DrawRangeLines();

            if (Time[0] >= tradeEnd)
            {
                phase = SetupPhase.SessionDone;
                ShowStatus(midline, "EMT trade window complete");
                return;
            }

            double price = Close[0];
            double retraceTolerance = RetraceToleranceTicks * TickSize;
            double confirmationDistance = ConfirmationTicks * TickSize;

            // Ready is an alert state, not a terminal state. Leave it on-screen
            // until the next incoming tick, then advance the tracked S/R level
            // and resume looking for the next breakout.
            if (phase == SetupPhase.Ready)
            {
                ResetSetupForNextBreakout();
                DrawRangeLines();
            }

            if (phase == SetupPhase.WaitingBreakout)
            {
                if (price < supportLevel && midline < supportLevel)
                    ArmBreakout(-1, price, midline);
                else if (price > resistanceLevel && midline > resistanceLevel)
                    ArmBreakout(1, price, midline);
            }
            else if (phase == SetupPhase.WaitingRetrace)
            {
                if (direction < 0)
                {
                    double priorExtreme = breakoutExtreme;
                    breakoutExtreme = Math.Min(breakoutExtreme, Low[0]);
                    if (price >= breakoutExtreme + confirmationDistance)
                        retraceSeen = true;
                    bool touched = price >= midline - retraceTolerance;
                    bool continued = retraceSeen && price < priorExtreme;
                    if (continued && !touched)
                    {
                        supportLevel = priorExtreme;
                        retraceSeen = false;
                        AlertOnce("CONT", "EMT continuation: tracking new support " +
                            supportLevel.ToString("0.00"), Brushes.Black, Brushes.Gold);
                        DrawRangeLines();
                    }
                    if (touched)
                        MarkRetrace(price, midline);
                }
                else
                {
                    double priorExtreme = breakoutExtreme;
                    breakoutExtreme = Math.Max(breakoutExtreme, High[0]);
                    if (price <= breakoutExtreme - confirmationDistance)
                        retraceSeen = true;
                    bool touched = price <= midline + retraceTolerance;
                    bool continued = retraceSeen && price > priorExtreme;
                    if (continued && !touched)
                    {
                        resistanceLevel = priorExtreme;
                        retraceSeen = false;
                        AlertOnce("CONT", "EMT continuation: tracking new resistance " +
                            resistanceLevel.ToString("0.00"), Brushes.Black, Brushes.Gold);
                        DrawRangeLines();
                    }
                    if (touched)
                        MarkRetrace(price, midline);
                }
            }
            else if (phase == SetupPhase.RetraceTouched)
            {
                bool movingAway = direction < 0
                    ? price <= midline - confirmationDistance && price < lastPrice
                    : price >= midline + confirmationDistance && price > lastPrice;
                if (movingAway)
                {
                    bool blocked = direction < 0
                        ? HasCurrentDoubleBottom()
                        : HasCurrentDoubleTop();
                    if (blocked)
                    {
                        AlertOnce("PATTERN", "EMT entry blocked by current " +
                            (direction < 0 ? "double bottom" : "double top"),
                            Brushes.White, Brushes.DarkRed);
                        ResetSetupForNextBreakout();
                        DrawRangeLines();
                    }
                    else
                    {
                        MarkReady(price);
                    }
                }
            }

            string detail = phase.ToString();
            if (phase == SetupPhase.WaitingBreakout)
            {
                if (price < supportLevel && midline >= supportLevel)
                    detail = "Price below support; waiting for Keltner midline < " +
                        supportLevel.ToString("0.00");
                else if (price > resistanceLevel && midline <= resistanceLevel)
                    detail = "Price above resistance; waiting for Keltner midline > " +
                        resistanceLevel.ToString("0.00");
            }
            ShowStatus(midline, detail);
            lastPrice = price;
        }

        private void ResetSession(DateTime date)
        {
            sessionDate = date;
            phase = SetupPhase.BuildingRange;
            openingHigh = double.NaN;
            openingLow = double.NaN;
            supportLevel = double.NaN;
            resistanceLevel = double.NaN;
            breakoutExtreme = double.NaN;
            lastPrice = double.NaN;
            direction = 0;
            setupStartBar = 0;
            retraceSeen = false;
        }

        private void DrawRangeLines()
        {
            if (double.IsNaN(openingHigh) || double.IsNaN(openingLow))
                return;
            string day = sessionDate.ToString("yyyyMMdd");
            Draw.HorizontalLine(this, "EMTHigh" + day, resistanceLevel,
                Brushes.OrangeRed, DashStyleHelper.Solid, 2);
            Draw.HorizontalLine(this, "EMTLow" + day, supportLevel,
                Brushes.DodgerBlue, DashStyleHelper.Solid, 2);
        }

        private void ArmBreakout(int newDirection, double price, double midline)
        {
            direction = newDirection;
            phase = SetupPhase.WaitingRetrace;
            setupStartBar = Math.Max(0, CurrentBar - 4);
            breakoutExtreme = direction < 0 ? Low[0] : High[0];
            retraceSeen = false;
            AlertOnce("L1", "EMT level 1: " + DirectionText() +
                " breakout; wait for Keltner retracement", Brushes.Black,
                Brushes.Gold);
        }

        private void MarkRetrace(double price, double midline)
        {
            phase = SetupPhase.RetraceTouched;
            AlertOnce("L2", "EMT level 2: retracement reached Keltner midline; " +
                "wait for reversal", Brushes.Black, Brushes.Orange);
        }

        private void MarkReady(double price)
        {
            phase = SetupPhase.Ready;
            if (direction < 0)
                Draw.ArrowDown(this, "EMTReady" + CurrentBar, false, 0,
                    High[0] + 2 * TickSize, Brushes.Red);
            else
                Draw.ArrowUp(this, "EMTReady" + CurrentBar, false, 0,
                    Low[0] - 2 * TickSize, Brushes.LimeGreen);
            AlertOnce("L3", "EMT level 3: PAPER/MANUAL " + DirectionText() +
                " ready | 2-point stop | 2-point target", Brushes.White,
                direction < 0 ? Brushes.DarkRed : Brushes.DarkGreen);
        }

        private void ResetSetupForNextBreakout()
        {
            if (direction < 0 && !double.IsNaN(breakoutExtreme))
                supportLevel = breakoutExtreme;
            else if (direction > 0 && !double.IsNaN(breakoutExtreme))
                resistanceLevel = breakoutExtreme;
            phase = SetupPhase.WaitingBreakout;
            direction = 0;
            retraceSeen = false;
        }

        private string DirectionText()
        {
            return direction < 0 ? "SHORT" : "LONG";
        }

        private void AlertOnce(string level, string message,
            Brush foreground, Brush background)
        {
            string id = "EMT-" + level + "-" + sessionDate.ToString("yyyyMMdd") +
                "-" + CurrentBar;
            Alert(id, Priority.High, message, "Alert1.wav", 10,
                foreground, background);
        }

        private void ShowStatus(double midline, string detail)
        {
            string range = double.IsNaN(openingHigh)
                ? "not set"
                : openingLow.ToString("0.00") + " - " + openingHigh.ToString("0.00");
            string text = "EMT " + Instrument.FullName + "\n" +
                "State: " + phase + " " + (direction == 0 ? "" : DirectionText()) + "\n" +
                "Opening range: " + range + "\n" +
                "Keltner midline: " + midline.ToString("0.00") + "\n" + detail;
            Draw.TextFixed(this, "EMTStatus", text, TextPosition.TopRight,
                Brushes.White, new SimpleFont("Consolas", 13),
                Brushes.Black, Brushes.Black, 55);
        }

        private List<double> CurrentSetupSeries(bool lows)
        {
            int available = CurrentBar - setupStartBar + 1;
            int count = Math.Min(PatternLookbackBars, available);
            List<double> result = new List<double>();
            for (int barsAgo = count - 1; barsAgo >= 0; barsAgo--)
                result.Add(lows ? Low[barsAgo] : High[barsAgo]);
            return result;
        }

        private bool HasCurrentDoubleBottom()
        {
            return HasDoublePattern(
                CurrentSetupSeries(true), CurrentSetupSeries(false), true);
        }

        private bool HasCurrentDoubleTop()
        {
            return HasDoublePattern(
                CurrentSetupSeries(false), CurrentSetupSeries(true), false);
        }

        private bool HasDoublePattern(List<double> values,
            List<double> oppositeValues, bool bottom)
        {
            const int pivotWindow = 3; // Mirrors chart_patterns.py pivot definition.
            if (values.Count < pivotWindow * 2 + 3)
                return false;

            List<int> pivots = new List<int>();
            for (int i = pivotWindow; i < values.Count - pivotWindow; i++)
            {
                bool pivot = true;
                for (int j = i - pivotWindow; j <= i + pivotWindow; j++)
                {
                    if (bottom && values[j] < values[i]) pivot = false;
                    if (!bottom && values[j] > values[i]) pivot = false;
                }
                if (pivot) pivots.Add(i);
            }
            if (pivots.Count < 2)
                return false;

            int first = pivots[pivots.Count - 2];
            int second = pivots[pivots.Count - 1];
            if (second - first < 6 ||
                Math.Abs(values[first] - values[second]) > PatternTolerancePoints)
                return false;

            // A W neckline is the intervening high; an M neckline is the
            // intervening low. Do not derive it from the pivot-side series.
            double neckline = oppositeValues[first];
            for (int i = first; i <= second; i++)
                neckline = bottom
                    ? Math.Max(neckline, oppositeValues[i])
                    : Math.Min(neckline, oppositeValues[i]);
            return bottom
                ? neckline - Math.Max(values[first], values[second]) >= PatternNecklinePoints
                : Math.Min(values[first], values[second]) - neckline >= PatternNecklinePoints;
        }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "Opening start hour (chart local)", GroupName = "Session", Order = 1)]
        public int OpeningStartHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "Opening start minute", GroupName = "Session", Order = 2)]
        public int OpeningStartMinute { get; set; }

        [NinjaScriptProperty]
        [Range(1, 120)]
        [Display(Name = "Opening range minutes", GroupName = "Session", Order = 3)]
        public int OpeningRangeMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 600)]
        [Display(Name = "Trade window minutes", GroupName = "Session", Order = 4)]
        public int TradeWindowMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(2, 100)]
        [Display(Name = "Keltner EMA period", GroupName = "Keltner", Order = 1)]
        public int KeltnerEmaPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(2, 100)]
        [Display(Name = "Keltner ATR period", GroupName = "Keltner", Order = 2)]
        public int KeltnerAtrPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Keltner ATR multiplier", GroupName = "Keltner", Order = 3)]
        public double KeltnerAtrMultiplier { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Retrace tolerance ticks", GroupName = "Entry", Order = 1)]
        public int RetraceToleranceTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Confirmation ticks", GroupName = "Entry", Order = 2)]
        public int ConfirmationTicks { get; set; }

        [NinjaScriptProperty]
        [Range(9, 100)]
        [Display(Name = "Pattern lookback bars", GroupName = "Pattern veto", Order = 1)]
        public int PatternLookbackBars { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 20.0)]
        [Display(Name = "Pattern tolerance points", GroupName = "Pattern veto", Order = 2)]
        public double PatternTolerancePoints { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 20.0)]
        [Display(Name = "Pattern neckline points", GroupName = "Pattern veto", Order = 3)]
        public double PatternNecklinePoints { get; set; }
    }
}


#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private EMTStrategyIndicator[] cacheEMTStrategyIndicator;
		public EMTStrategyIndicator EMTStrategyIndicator(int openingStartHour, int openingStartMinute, int openingRangeMinutes, int tradeWindowMinutes, int keltnerEmaPeriod, int keltnerAtrPeriod, double keltnerAtrMultiplier, int retraceToleranceTicks, int confirmationTicks, int patternLookbackBars, double patternTolerancePoints, double patternNecklinePoints)
		{
			return EMTStrategyIndicator(Input, openingStartHour, openingStartMinute, openingRangeMinutes, tradeWindowMinutes, keltnerEmaPeriod, keltnerAtrPeriod, keltnerAtrMultiplier, retraceToleranceTicks, confirmationTicks, patternLookbackBars, patternTolerancePoints, patternNecklinePoints);
		}

		public EMTStrategyIndicator EMTStrategyIndicator(ISeries<double> input, int openingStartHour, int openingStartMinute, int openingRangeMinutes, int tradeWindowMinutes, int keltnerEmaPeriod, int keltnerAtrPeriod, double keltnerAtrMultiplier, int retraceToleranceTicks, int confirmationTicks, int patternLookbackBars, double patternTolerancePoints, double patternNecklinePoints)
		{
			if (cacheEMTStrategyIndicator != null)
				for (int idx = 0; idx < cacheEMTStrategyIndicator.Length; idx++)
					if (cacheEMTStrategyIndicator[idx] != null && cacheEMTStrategyIndicator[idx].OpeningStartHour == openingStartHour && cacheEMTStrategyIndicator[idx].OpeningStartMinute == openingStartMinute && cacheEMTStrategyIndicator[idx].OpeningRangeMinutes == openingRangeMinutes && cacheEMTStrategyIndicator[idx].TradeWindowMinutes == tradeWindowMinutes && cacheEMTStrategyIndicator[idx].KeltnerEmaPeriod == keltnerEmaPeriod && cacheEMTStrategyIndicator[idx].KeltnerAtrPeriod == keltnerAtrPeriod && cacheEMTStrategyIndicator[idx].KeltnerAtrMultiplier == keltnerAtrMultiplier && cacheEMTStrategyIndicator[idx].RetraceToleranceTicks == retraceToleranceTicks && cacheEMTStrategyIndicator[idx].ConfirmationTicks == confirmationTicks && cacheEMTStrategyIndicator[idx].PatternLookbackBars == patternLookbackBars && cacheEMTStrategyIndicator[idx].PatternTolerancePoints == patternTolerancePoints && cacheEMTStrategyIndicator[idx].PatternNecklinePoints == patternNecklinePoints && cacheEMTStrategyIndicator[idx].EqualsInput(input))
						return cacheEMTStrategyIndicator[idx];
			return CacheIndicator<EMTStrategyIndicator>(new EMTStrategyIndicator(){ OpeningStartHour = openingStartHour, OpeningStartMinute = openingStartMinute, OpeningRangeMinutes = openingRangeMinutes, TradeWindowMinutes = tradeWindowMinutes, KeltnerEmaPeriod = keltnerEmaPeriod, KeltnerAtrPeriod = keltnerAtrPeriod, KeltnerAtrMultiplier = keltnerAtrMultiplier, RetraceToleranceTicks = retraceToleranceTicks, ConfirmationTicks = confirmationTicks, PatternLookbackBars = patternLookbackBars, PatternTolerancePoints = patternTolerancePoints, PatternNecklinePoints = patternNecklinePoints }, input, ref cacheEMTStrategyIndicator);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.EMTStrategyIndicator EMTStrategyIndicator(int openingStartHour, int openingStartMinute, int openingRangeMinutes, int tradeWindowMinutes, int keltnerEmaPeriod, int keltnerAtrPeriod, double keltnerAtrMultiplier, int retraceToleranceTicks, int confirmationTicks, int patternLookbackBars, double patternTolerancePoints, double patternNecklinePoints)
		{
			return indicator.EMTStrategyIndicator(Input, openingStartHour, openingStartMinute, openingRangeMinutes, tradeWindowMinutes, keltnerEmaPeriod, keltnerAtrPeriod, keltnerAtrMultiplier, retraceToleranceTicks, confirmationTicks, patternLookbackBars, patternTolerancePoints, patternNecklinePoints);
		}

		public Indicators.EMTStrategyIndicator EMTStrategyIndicator(ISeries<double> input , int openingStartHour, int openingStartMinute, int openingRangeMinutes, int tradeWindowMinutes, int keltnerEmaPeriod, int keltnerAtrPeriod, double keltnerAtrMultiplier, int retraceToleranceTicks, int confirmationTicks, int patternLookbackBars, double patternTolerancePoints, double patternNecklinePoints)
		{
			return indicator.EMTStrategyIndicator(input, openingStartHour, openingStartMinute, openingRangeMinutes, tradeWindowMinutes, keltnerEmaPeriod, keltnerAtrPeriod, keltnerAtrMultiplier, retraceToleranceTicks, confirmationTicks, patternLookbackBars, patternTolerancePoints, patternNecklinePoints);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.EMTStrategyIndicator EMTStrategyIndicator(int openingStartHour, int openingStartMinute, int openingRangeMinutes, int tradeWindowMinutes, int keltnerEmaPeriod, int keltnerAtrPeriod, double keltnerAtrMultiplier, int retraceToleranceTicks, int confirmationTicks, int patternLookbackBars, double patternTolerancePoints, double patternNecklinePoints)
		{
			return indicator.EMTStrategyIndicator(Input, openingStartHour, openingStartMinute, openingRangeMinutes, tradeWindowMinutes, keltnerEmaPeriod, keltnerAtrPeriod, keltnerAtrMultiplier, retraceToleranceTicks, confirmationTicks, patternLookbackBars, patternTolerancePoints, patternNecklinePoints);
		}

		public Indicators.EMTStrategyIndicator EMTStrategyIndicator(ISeries<double> input , int openingStartHour, int openingStartMinute, int openingRangeMinutes, int tradeWindowMinutes, int keltnerEmaPeriod, int keltnerAtrPeriod, double keltnerAtrMultiplier, int retraceToleranceTicks, int confirmationTicks, int patternLookbackBars, double patternTolerancePoints, double patternNecklinePoints)
		{
			return indicator.EMTStrategyIndicator(input, openingStartHour, openingStartMinute, openingRangeMinutes, tradeWindowMinutes, keltnerEmaPeriod, keltnerAtrPeriod, keltnerAtrMultiplier, retraceToleranceTicks, confirmationTicks, patternLookbackBars, patternTolerancePoints, patternNecklinePoints);
		}
	}
}

#endregion
