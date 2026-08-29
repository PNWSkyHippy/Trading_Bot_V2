// FCR (First Candle Rule) strategy, ported from the spec at
// Ron/Docs/FCR-Strat-md.txt. One file, not a pair: PlaceTrades gates only the
// EnterLong/EnterShort calls, so with it off this runs purely as an
// informational overlay (range box, phase status, signal markers) and never
// touches the account -- no separate indicator file needed, unlike EAT (whose
// two-file split exists because its indicator also feeds the Python bot; FCR
// has no bot side, so one file covers both roles). Test in the Strategy
// Analyzer before ever enabling PlaceTrades on a live/paper account.
//
// FVG detection is delegated to the user's own FVGICT indicator (found on
// this machine's Indicators folder) via its FVGList, rather than reimplementing
// fair-value-gap logic here. FVGICT's FVGType.S is an up-gap (created on a bar
// where Low[0] > High[2]), FVGType.R is a down-gap (High[0] < Low[2]); its
// FVG.LowerPrice/UpperPrice always satisfy Lower < Upper regardless of type.
//
// RangeStartTime is chart-local time, matching EATStrategy.cs's convention --
// if this NinjaTrader install displays bars in exchange time rather than
// local time, double check 6:30 AM against how the chart actually labels the
// spec's 6:30-6:35 AM PST opening range.

using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.NinjaScript.Indicators;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class FCRStrategy : Strategy
    {
        private enum FcrPhase
        {
            WaitSession,
            BuildingRange,
            WaitingBreakout,
            WaitingRetrace,
            WaitingEngulf,
            InTrade
        }

        private FcrPhase phase;
        private FVGICT fvg;

        private double rangeHigh;
        private double rangeLow;

        private string activeFvgTag;
        private double activeFvgLower;
        private double activeFvgUpper;
        private string activeDirection;

        private double entryCandleOpen;
        private double entryCandleClose;
        private double entryCandleHigh;
        private double entryCandleLow;

        private double pendingStop;
        private int maxFvgCountThisSession;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "First Candle Rule: opening-range breakout confirmed by an FVG, " +
                    "then a retrace into that FVG and an engulfing candle, 3:1 TP off a tick-buffered SL.";
                Name = "FCR Strategy";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                IsUnmanaged = false;
                IsInstantiatedOnEachOptimizationIteration = true;
                TimeInForce = TimeInForce.Gtc;

                RangeStartTime = new TimeSpan(6, 30, 0);
                RangeLengthMinutes = 5;

                UseFvgImpulseFilter = true;
                FvgImpulseFactor = 1.1;
                MinFvgSizeTicks = 2;

                StopBufferTicks = 1;
                TpRatio = 3.0;

                Contracts = 1;
                PlaceTrades = false;
                EnableLongs = true;
                EnableShorts = true;
            }
            else if (State == State.DataLoaded)
            {
                fvg = FVGICT(
                    false, FVGPeriodTypes.Minute, 1,
                    1,
                    UseFvgImpulseFilter, FvgImpulseFactor, 10,
                    MinFvgSizeTicks * TickSize,
                    false,
                    FVGFillType.CLOSE_THROUGH,
                    true,
                    false,
                    false, default(TimeSpan), 60,
                    false, default(TimeSpan), 60,
                    false, default(TimeSpan), 60,
                    Brushes.Transparent, Brushes.Transparent, Brushes.Transparent,
                    Brushes.Transparent, Brushes.Transparent, Brushes.Transparent,
                    1, 1,
                    false, TextPosition.TopRight, new SimpleFont("Arial", 10),
                    Brushes.Transparent, Brushes.Transparent, Brushes.Transparent, 1);

                ResetForNewSession();
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 10)
                return;

            DateTime now = Time[0];

            fvg.Update();

            if (Bars.IsFirstBarOfSession && phase != FcrPhase.InTrade)
            {
                if (!double.IsNaN(rangeHigh))
                    Print(now + " FCR prior session max FVGList.Count=" + maxFvgCountThisSession +
                        " fvg.CurrentBar=" + fvg.CurrentBar + " strategy CurrentBar=" + CurrentBar);
                ResetForNewSession();
            }

            if (fvg.FVGList.Count > maxFvgCountThisSession)
                maxFvgCountThisSession = fvg.FVGList.Count;

            DrawStatus();

            if (phase == FcrPhase.InTrade)
                return;

            TimeSpan tod = now.TimeOfDay;
            TimeSpan rangeStart = RangeStartTime;
            TimeSpan rangeEnd = RangeStartTime.Add(TimeSpan.FromMinutes(RangeLengthMinutes));

            if (phase == FcrPhase.WaitSession)
            {
                if (tod > rangeStart && tod <= rangeEnd)
                {
                    phase = FcrPhase.BuildingRange;
                    rangeHigh = High[0];
                    rangeLow = Low[0];
                }
                return;
            }

            if (phase == FcrPhase.BuildingRange)
            {
                if (tod <= rangeEnd)
                {
                    rangeHigh = Math.Max(rangeHigh, High[0]);
                    rangeLow = Math.Min(rangeLow, Low[0]);
                    return;
                }

                Print(now + " FCR range built high=" + rangeHigh + " low=" + rangeLow);
                DrawRangeBox(now, rangeStart, rangeEnd);
                phase = FcrPhase.WaitingBreakout;
                return;
            }

            if (phase == FcrPhase.WaitingBreakout)
            {
                CheckForBreakoutFvg(now);
                return;
            }

            if (phase == FcrPhase.WaitingRetrace)
            {
                CheckForRetrace(now);
                return;
            }

            if (phase == FcrPhase.WaitingEngulf)
            {
                CheckForEngulfingEntry(now);
                return;
            }
        }

        // ---- phase 1: opening range ----

        private void ResetForNewSession()
        {
            phase = FcrPhase.WaitSession;
            rangeHigh = double.NaN;
            rangeLow = double.NaN;
            maxFvgCountThisSession = 0;
            ResetSetupState();
        }

        private void ResetSetupState()
        {
            activeFvgTag = null;
            activeFvgLower = double.NaN;
            activeFvgUpper = double.NaN;
            activeDirection = null;
            entryCandleOpen = double.NaN;
            entryCandleClose = double.NaN;
            entryCandleHigh = double.NaN;
            entryCandleLow = double.NaN;
        }

        private void DrawRangeBox(DateTime now, TimeSpan rangeStart, TimeSpan rangeEnd)
        {
            DateTime startDt = now.Date.Add(rangeStart);
            DateTime endDt = now.Date.Add(rangeEnd);
            string tag = "FCRRange" + now.Date.ToString("yyyyMMdd");

            Draw.Rectangle(this, tag, false, startDt, rangeLow, endDt, rangeHigh,
                Brushes.DodgerBlue, Brushes.DodgerBlue, 10);
            Draw.Line(this, tag + "Hi", false, startDt, rangeHigh, now.Date.AddDays(1), rangeHigh,
                Brushes.DodgerBlue, DashStyleHelper.Dash, 1);
            Draw.Line(this, tag + "Lo", false, startDt, rangeLow, now.Date.AddDays(1), rangeLow,
                Brushes.DodgerBlue, DashStyleHelper.Dash, 1);
        }

        private void DrawStatus()
        {
            string text = "FCR phase=" + phase +
                (activeDirection != null ? " dir=" + activeDirection : "") +
                (double.IsNaN(rangeHigh) ? "" : " range=[" + rangeLow + "-" + rangeHigh + "]");
            Draw.TextFixed(this, "FCRStatus", text, TextPosition.TopRight);
        }

        // ---- phase 2: FVG breaking out of the range ----

        private void CheckForBreakoutFvg(DateTime now)
        {
            foreach (NinjaTrader.NinjaScript.Indicators.FVGICT.FVG f in fvg.FVGList)
            {
                if (f.IsFilled || f.IsExpired)
                    continue;

                if (EnableLongs && f.Type == NinjaTrader.NinjaScript.Indicators.FVGICT.FVGType.S && f.LowerPrice > rangeHigh)
                {
                    SetActiveFvg(f, "long", now);
                    return;
                }
                if (EnableShorts && f.Type == NinjaTrader.NinjaScript.Indicators.FVGICT.FVGType.R && f.UpperPrice < rangeLow)
                {
                    SetActiveFvg(f, "short", now);
                    return;
                }
            }
        }

        private void SetActiveFvg(NinjaTrader.NinjaScript.Indicators.FVGICT.FVG f, string direction, DateTime now)
        {
            activeFvgTag = f.Tag;
            activeFvgLower = f.LowerPrice;
            activeFvgUpper = f.UpperPrice;
            activeDirection = direction;
            phase = FcrPhase.WaitingRetrace;

            Print(now + " FCR breakout FVG dir=" + direction + " zone=[" + activeFvgLower + "-" + activeFvgUpper +
                "] range=[" + rangeLow + "-" + rangeHigh + "]");
        }

        private bool ActiveFvgStillValid()
        {
            foreach (NinjaTrader.NinjaScript.Indicators.FVGICT.FVG f in fvg.FVGList)
            {
                if (f.Tag == activeFvgTag)
                    return !f.IsFilled && !f.IsExpired;
            }
            return false;
        }

        // ---- phase 3: retrace into the FVG (wick touch, not close, per spec) ----

        private void CheckForRetrace(DateTime now)
        {
            if (!ActiveFvgStillValid())
            {
                Print(now + " FCR breakout FVG filled/expired before any retrace, resuming scan");
                ResetSetupState();
                phase = FcrPhase.WaitingBreakout;
                return;
            }

            bool touchedZone = Low[0] <= activeFvgUpper && High[0] >= activeFvgLower;
            if (!touchedZone)
                return;

            entryCandleOpen = Open[0];
            entryCandleClose = Close[0];
            entryCandleHigh = High[0];
            entryCandleLow = Low[0];
            phase = FcrPhase.WaitingEngulf;

            Print(now + " FCR retrace into FVG on candle O=" + entryCandleOpen + " H=" + entryCandleHigh +
                " L=" + entryCandleLow + " C=" + entryCandleClose);
        }

        // ---- phase 4: engulfing candle confirms entry ----

        private void CheckForEngulfingEntry(DateTime now)
        {
            if (!ActiveFvgStillValid())
            {
                Print(now + " FCR setup invalidated before engulfing confirmation, resuming scan");
                ResetSetupState();
                phase = FcrPhase.WaitingBreakout;
                return;
            }

            bool confirmed = activeDirection == "long"
                ? BullishEngulfs(entryCandleOpen, entryCandleClose, entryCandleHigh)
                : BearishEngulfs(entryCandleOpen, entryCandleClose, entryCandleLow);

            if (!confirmed)
                return;

            double slPrice = activeDirection == "long"
                ? entryCandleLow - StopBufferTicks * TickSize
                : entryCandleHigh + StopBufferTicks * TickSize;

            if (PlaceTrades)
            {
                OpenTrade(activeDirection, slPrice, now);
            }
            else
            {
                double markerPrice = activeDirection == "long" ? Low[0] - 2 * TickSize : High[0] + 2 * TickSize;
                Draw.Dot(this, "FCRSignal" + CurrentBar, true, 0, markerPrice,
                    activeDirection == "long" ? Brushes.LimeGreen : Brushes.Crimson);
                Print(now + " FCR SIGNAL-ONLY " + activeDirection + " @ " + Close[0] +
                    " SL=" + Instrument.MasterInstrument.RoundToTickSize(slPrice) + " (PlaceTrades=false)");
                ResetSetupState();
                phase = FcrPhase.WaitingBreakout;
            }
        }

        private bool BullishEngulfs(double refOpen, double refClose, double refHigh)
        {
            bool currentBullish = Close[0] > Open[0];
            bool bodyEngulfs = Open[0] <= Math.Min(refOpen, refClose) && Close[0] >= Math.Max(refOpen, refClose);
            bool topsHigh = High[0] > refHigh;
            return currentBullish && bodyEngulfs && topsHigh;
        }

        private bool BearishEngulfs(double refOpen, double refClose, double refLow)
        {
            bool currentBearish = Close[0] < Open[0];
            bool bodyEngulfs = Open[0] >= Math.Max(refOpen, refClose) && Close[0] <= Math.Min(refOpen, refClose);
            bool bottomsLow = Low[0] < refLow;
            return currentBearish && bodyEngulfs && bottomsLow;
        }

        // ---- order submission ----

        private void OpenTrade(string direction, double slPrice, DateTime now)
        {
            activeDirection = direction;
            pendingStop = Instrument.MasterInstrument.RoundToTickSize(slPrice);
            phase = FcrPhase.InTrade;

            Print(now + " FCR ENTRY SIGNAL " + direction + " entryCandle H=" + entryCandleHigh +
                " L=" + entryCandleLow + " SL=" + pendingStop);

            if (direction == "long")
                EnterLong(Contracts, "FCREntry");
            else
                EnterShort(Contracts, "FCREntry");
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution?.Order == null)
                return;

            string signal = execution.Order.Name;

            if (signal == "FCREntry")
            {
                double tp = activeDirection == "long"
                    ? price + TpRatio * (price - pendingStop)
                    : price - TpRatio * (pendingStop - price);
                tp = Instrument.MasterInstrument.RoundToTickSize(tp);

                if (activeDirection == "long")
                {
                    ExitLongStopMarket(0, true, quantity, pendingStop, "FCRStop", "FCREntry");
                    ExitLongLimit(0, true, quantity, tp, "FCRTp", "FCREntry");
                }
                else
                {
                    ExitShortStopMarket(0, true, quantity, pendingStop, "FCRStop", "FCREntry");
                    ExitShortLimit(0, true, quantity, tp, "FCRTp", "FCREntry");
                }

                Print(time + " FCR ENTRY FILLED " + activeDirection + " @ " + price +
                    " SL=" + pendingStop + " TP=" + tp);
                return;
            }

            if (Position.MarketPosition == MarketPosition.Flat && phase == FcrPhase.InTrade)
            {
                Print(time + " FCR trade closed, resuming scan");
                phase = FcrPhase.WaitingBreakout;
                ResetSetupState();
            }
        }

        #region Properties

        [NinjaScriptProperty]
        [XmlIgnore]
        [Display(Name = "Opening range start (chart local)", GroupName = "Opening Range", Order = 1)]
        public TimeSpan RangeStartTime { get; set; }

        [Browsable(false)]
        public string RangeStartTimeSerializable
        {
            get { return RangeStartTime.ToString(); }
            set { RangeStartTime = TimeSpan.Parse(value); }
        }

        [NinjaScriptProperty]
        [Range(1, 60)]
        [Display(Name = "Opening range length (minutes)", GroupName = "Opening Range", Order = 2)]
        public int RangeLengthMinutes { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Require ATR impulse move for FVGs", GroupName = "FVG Filter", Order = 1)]
        public bool UseFvgImpulseFilter { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, double.MaxValue)]
        [Display(Name = "FVG impulse factor (x ATR)", GroupName = "FVG Filter", Order = 2)]
        public double FvgImpulseFactor { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Min FVG size (ticks)", GroupName = "FVG Filter", Order = 3)]
        public double MinFvgSizeTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Stop buffer beyond entry candle (ticks)", GroupName = "Entry & Risk", Order = 1)]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, double.MaxValue)]
        [Display(Name = "TP ratio (x risk)", GroupName = "Entry & Risk", Order = 2)]
        public double TpRatio { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Contracts", GroupName = "Order Management", Order = 1)]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place trades (off = informational only)", GroupName = "Order Management", Order = 2)]
        public bool PlaceTrades { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable long entries", GroupName = "Order Management", Order = 3)]
        public bool EnableLongs { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable short entries", GroupName = "Order Management", Order = 4)]
        public bool EnableShorts { get; set; }

        #endregion
    }
}
