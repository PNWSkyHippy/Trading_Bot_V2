// NinjaTrader 8 visual companion for the EAT session-box strategy.
// Apply to a 1-minute futures chart. Advisory only: it draws and alerts;
// Hostinger's Python EAT engine remains the only automated order executor.

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
            WaitingSession,
            BuildingBox,
            WaitingBufferClose,
            InTrade,
            SessionDone,
            MarketClosed
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
        private DateTime boxEnd;
        private DateTime tradeEnd;
        private double primaryHigh;
        private double primaryLow;
        private double fallbackHigh;
        private double fallbackLow;
        private int primaryBars;
        private int fallbackBars;
        private int selectedBoxMinutes;
        private double innerHigh;
        private double innerLow;
        private double outerHigh;
        private double outerLow;
        private int lastZone;
        private int tradesThisSession;
        private int tradeSequence;

        private bool tradeActive;
        private int tradeDirection;
        private int tradeQuantity;
        private int remainingQuantity;
        private int tp1Quantity;
        private double entryPrice;
        private double stopPrice;
        private double tp1Price;
        private double runnerStop;
        private double bestPrice;
        private bool tp1Done;
        private int entryBar;
        private double realizedPnlTicks;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "EAT first-candle range, entry buffers, paper signals, and runner visualization.";
                Name = "EAT Strategy Indicator";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = true;
                DrawOnPricePanel = true;
                IsSuspendedWhileInactive = true;

                Contracts = 1;
                EnableNY = true;
                NYStartHour = 5;
                NYStartMinute = 0;
                EnableTokyo = true;
                TokyoStartHour = 14;
                TokyoStartMinute = 30;
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
                TP1Ticks = 100;
                RunnerTrailTicks = 30;
                WickStopLookbackMinutes = 20;
                TradeWindowMinutes = 60;
                MaxTradesPerSession = 12;
            }
            else if (State == State.DataLoaded)
            {
                ResetSession(null);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
            {
                Draw.TextFixed(this, "EATWrongBars",
                    "EAT requires a 1-minute futures chart", TextPosition.TopLeft,
                    Brushes.White, new SimpleFont("Arial", 16), Brushes.DarkRed,
                    Brushes.DarkRed, 80);
                return;
            }

            if (CurrentBar < Math.Max(FallbackBoxMinutes, WickStopLookbackMinutes) + 2)
                return;

            DateTime now = Time[0];
            if (FallbackBoxMinutes < PrimaryBoxMinutes || MaxBoxTicks < MinBoxTicks)
            {
                Draw.TextFixed(this, "EATBadSettings",
                    "EAT settings invalid: fallback box/range maximum must not be smaller",
                    TextPosition.TopLeft, Brushes.White,
                    new SimpleFont("Arial", 14), Brushes.DarkRed,
                    Brushes.DarkRed, 80);
                return;
            }
            SessionCandidate candidate = FindActiveSession(now);
            if (candidate == null)
            {
                if (tradeActive)
                    UpdatePaperTrade();
                else
                    phase = SetupPhase.WaitingSession;
                ShowStatus(tradeActive
                    ? "Paper position active outside its entry window"
                    : "Waiting for next EAT session");
                return;
            }

            string candidateKey = candidate.Name + ":" + candidate.Start.ToString("O");
            if (candidateKey != sessionKey && !tradeActive)
                ResetSession(candidate);

            if (IsMarketClosed(now))
            {
                if (tradeActive)
                    UpdatePaperTrade();
                else
                    phase = SetupPhase.MarketClosed;
                ShowStatus(tradeActive
                    ? "Paper position active during market closure"
                    : "Futures market maintenance/weekly closure");
                return;
            }

            UpdateBoxInputs(now);
            TryFinalizeBox(now);

            if (tradeActive)
                UpdatePaperTrade();
            else if (phase == SetupPhase.WaitingBufferClose)
                CheckEntry(now);

            if (tradeEnd != DateTime.MinValue && now > tradeEnd && !tradeActive)
                phase = SetupPhase.SessionDone;

            DrawSessionBox();
            ShowStatus(StatusDetail());
        }

        private SessionCandidate FindActiveSession(DateTime now)
        {
            SessionCandidate best = null;
            for (int dayOffset = -1; dayOffset <= 0; dayOffset++)
            {
                DateTime day = now.Date.AddDays(dayOffset);
                if (EnableNY)
                    ConsiderSession(ref best, now, "NY",
                        day.AddHours(NYStartHour).AddMinutes(NYStartMinute));
                if (EnableTokyo)
                    ConsiderSession(ref best, now, "Tokyo",
                        day.AddHours(TokyoStartHour).AddMinutes(TokyoStartMinute));
                if (EnableLondon)
                {
                    bool dst = TimeZoneInfo.Local.IsDaylightSavingTime(day.AddHours(12));
                    int hour = dst ? LondonDstHour : LondonStandardHour;
                    int minute = dst ? LondonDstMinute : LondonStandardMinute;
                    ConsiderSession(ref best, now, "London",
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

        private void ResetSession(SessionCandidate candidate)
        {
            sessionKey = candidate == null
                ? null
                : candidate.Name + ":" + candidate.Start.ToString("O");
            sessionName = candidate == null ? null : candidate.Name;
            sessionStart = candidate == null ? DateTime.MinValue : candidate.Start;
            boxEnd = DateTime.MinValue;
            tradeEnd = DateTime.MinValue;
            phase = candidate == null
                ? SetupPhase.WaitingSession
                : SetupPhase.BuildingBox;
            primaryHigh = fallbackHigh = double.NaN;
            primaryLow = fallbackLow = double.NaN;
            primaryBars = fallbackBars = 0;
            selectedBoxMinutes = 0;
            innerHigh = innerLow = outerHigh = outerLow = double.NaN;
            lastZone = 0;
            tradesThisSession = 0;
            ClearPaperTrade();
        }

        private void UpdateBoxInputs(DateTime now)
        {
            if (phase != SetupPhase.BuildingBox || sessionStart == DateTime.MinValue)
                return;
            DateTime barStart = now.AddMinutes(-1);
            DateTime primaryEnd = sessionStart.AddMinutes(PrimaryBoxMinutes);
            DateTime fallbackEnd = sessionStart.AddMinutes(FallbackBoxMinutes);
            if (barStart >= sessionStart && barStart < primaryEnd)
            {
                primaryHigh = double.IsNaN(primaryHigh)
                    ? High[0] : Math.Max(primaryHigh, High[0]);
                primaryLow = double.IsNaN(primaryLow)
                    ? Low[0] : Math.Min(primaryLow, Low[0]);
                primaryBars++;
            }
            if (barStart >= sessionStart && barStart < fallbackEnd)
            {
                fallbackHigh = double.IsNaN(fallbackHigh)
                    ? High[0] : Math.Max(fallbackHigh, High[0]);
                fallbackLow = double.IsNaN(fallbackLow)
                    ? Low[0] : Math.Min(fallbackLow, Low[0]);
                fallbackBars++;
            }
        }

        private void TryFinalizeBox(DateTime now)
        {
            if (phase != SetupPhase.BuildingBox || sessionStart == DateTime.MinValue)
                return;
            DateTime primaryEnd = sessionStart.AddMinutes(PrimaryBoxMinutes);
            DateTime fallbackEnd = sessionStart.AddMinutes(FallbackBoxMinutes);

            if (selectedBoxMinutes == 0 && now >= primaryEnd
                && primaryBars >= PrimaryBoxMinutes)
            {
                int ticks = RangeTicks(primaryHigh, primaryLow);
                if (ticks > MaxBoxTicks)
                {
                    SkipSession("Primary box too large: " + ticks + " ticks");
                    return;
                }
                if (ticks >= MinBoxTicks)
                {
                    SetBox(primaryHigh, primaryLow, PrimaryBoxMinutes, ticks);
                    return;
                }
                selectedBoxMinutes = -1;
                AlertOnce("FALLBACK",
                    "EAT " + sessionName + ": 5-minute box too small; waiting for 15-minute box",
                    Brushes.Black, Brushes.Gold);
            }

            if (selectedBoxMinutes == -1 && now >= fallbackEnd
                && fallbackBars >= FallbackBoxMinutes)
            {
                int ticks = RangeTicks(fallbackHigh, fallbackLow);
                if (ticks < MinBoxTicks)
                {
                    SkipSession("Fallback box too small: " + ticks + " ticks");
                    return;
                }
                if (ticks > MaxBoxTicks)
                {
                    SkipSession("Fallback box too large: " + ticks + " ticks");
                    return;
                }
                SetBox(fallbackHigh, fallbackLow, FallbackBoxMinutes, ticks);
            }
        }

        private int RangeTicks(double high, double low)
        {
            return (int)Math.Round((high - low) / TickSize);
        }

        private void SetBox(double high, double low, int minutes, int ticks)
        {
            selectedBoxMinutes = minutes;
            boxEnd = sessionStart.AddMinutes(minutes);
            tradeEnd = boxEnd.AddMinutes(TradeWindowMinutes);
            innerHigh = high;
            innerLow = low;
            outerHigh = innerHigh + BufferTicks * TickSize;
            outerLow = innerLow - BufferTicks * TickSize;
            phase = SetupPhase.WaitingBufferClose;
            AlertOnce("BOX",
                "EAT " + sessionName + " box ready: "
                + innerLow.ToString("0.00") + "-" + innerHigh.ToString("0.00")
                + " (" + ticks + " ticks)",
                Brushes.Black, Brushes.Turquoise);
        }

        private void SkipSession(string reason)
        {
            phase = SetupPhase.SessionDone;
            tradeEnd = sessionStart.AddMinutes(
                FallbackBoxMinutes + TradeWindowMinutes);
            AlertOnce("SKIP", "EAT " + sessionName + " skipped: " + reason,
                Brushes.White, Brushes.DarkRed);
        }

        private void CheckEntry(DateTime now)
        {
            if (now > tradeEnd || tradesThisSession >= MaxTradesPerSession)
            {
                phase = SetupPhase.SessionDone;
                return;
            }

            double close = Close[0];
            int zone = 0;
            if (close >= innerHigh && close <= outerHigh)
                zone = 1;
            else if (close >= outerLow && close <= innerLow)
                zone = -1;

            if (zone == 0)
            {
                lastZone = 0;
                return;
            }
            if (zone == lastZone)
                return;

            OpenPaperTrade(zone, close);
            lastZone = zone;
        }

        private void OpenPaperTrade(int direction, double price)
        {
            tradeSequence++;
            tradeDirection = direction;
            tradeQuantity = Contracts;
            remainingQuantity = Contracts;
            tp1Quantity = (int)Math.Ceiling(Contracts / 2.0);
            entryPrice = price;
            stopPrice = WickStop(direction);
            tp1Price = direction > 0
                ? innerHigh + TP1Ticks * TickSize
                : innerLow - TP1Ticks * TickSize;
            runnerStop = double.NaN;
            bestPrice = price;
            tp1Done = false;
            entryBar = CurrentBar;
            realizedPnlTicks = 0;
            tradeActive = true;
            tradesThisSession++;
            phase = SetupPhase.InTrade;

            string tag = TradeTag();
            if (direction > 0)
                Draw.ArrowUp(this, tag + "Entry", false, 0,
                    Low[0] - 2 * TickSize, Brushes.LimeGreen);
            else
                Draw.ArrowDown(this, tag + "Entry", false, 0,
                    High[0] + 2 * TickSize, Brushes.Red);
            DrawTradeLines();
            AlertOnce("ENTRY" + tradeSequence,
                "EAT PAPER " + (direction > 0 ? "LONG " : "SHORT ")
                + Contracts + " " + Instrument.FullName
                + " | stop " + stopPrice.ToString("0.00")
                + " | TP1 " + tp1Price.ToString("0.00"),
                Brushes.White, direction > 0 ? Brushes.DarkGreen : Brushes.DarkRed);
        }

        private double WickStop(int direction)
        {
            double fallback = direction > 0 ? innerLow : innerHigh;
            double result = fallback;
            int count = Math.Min(WickStopLookbackMinutes, CurrentBar);
            for (int barsAgo = 1; barsAgo <= count; barsAgo++)
            {
                if (direction > 0
                    && Low[barsAgo] >= outerLow && Low[barsAgo] < innerLow
                    && Close[barsAgo] >= innerLow)
                    result = Math.Min(result, Low[barsAgo]);
                if (direction < 0
                    && High[barsAgo] > innerHigh && High[barsAgo] <= outerHigh
                    && Close[barsAgo] <= innerHigh)
                    result = Math.Max(result, High[barsAgo]);
            }
            return result;
        }

        private void UpdatePaperTrade()
        {
            bool entryBarNow = CurrentBar == entryBar;
            double observedLow = entryBarNow ? Close[0] : Low[0];
            double observedHigh = entryBarNow ? Close[0] : High[0];
            bool stopHit = tradeDirection > 0
                ? observedLow <= stopPrice
                : observedHigh >= stopPrice;
            bool tpHit = tradeDirection > 0
                ? observedHigh >= tp1Price
                : observedLow <= tp1Price;

            if (!tp1Done && stopHit)
            {
                ClosePaperTrade(stopPrice, "stop");
                return;
            }
            if (!tp1Done && tpHit)
            {
                int qty = Math.Min(tp1Quantity, remainingQuantity);
                Realize(qty, tp1Price);
                tp1Done = true;
                if (remainingQuantity <= 0)
                {
                    ClosePaperTrade(tp1Price, "TP1");
                    return;
                }
                bestPrice = tradeDirection > 0
                    ? Math.Max(bestPrice, observedHigh)
                    : Math.Min(bestPrice, observedLow);
                runnerStop = tradeDirection > 0
                    ? bestPrice - RunnerTrailTicks * TickSize
                    : bestPrice + RunnerTrailTicks * TickSize;
                AlertOnce("TP1" + tradeSequence,
                    "EAT TP1 reached; runner trail armed at "
                    + runnerStop.ToString("0.00"),
                    Brushes.Black, Brushes.LimeGreen);
            }

            if (tp1Done && remainingQuantity > 0)
            {
                if (tradeDirection > 0)
                {
                    bestPrice = Math.Max(bestPrice, observedHigh);
                    runnerStop = Math.Max(
                        runnerStop, bestPrice - RunnerTrailTicks * TickSize);
                    if (observedLow <= runnerStop)
                    {
                        ClosePaperTrade(runnerStop, "runner trail");
                        return;
                    }
                }
                else
                {
                    bestPrice = Math.Min(bestPrice, observedLow);
                    runnerStop = Math.Min(
                        runnerStop, bestPrice + RunnerTrailTicks * TickSize);
                    if (observedHigh >= runnerStop)
                    {
                        ClosePaperTrade(runnerStop, "runner trail");
                        return;
                    }
                }
            }
            DrawTradeLines();
        }

        private void Realize(int quantity, double price)
        {
            double ticks = tradeDirection > 0
                ? (price - entryPrice) / TickSize
                : (entryPrice - price) / TickSize;
            realizedPnlTicks += ticks * quantity;
            remainingQuantity -= quantity;
        }

        private void ClosePaperTrade(double price, string reason)
        {
            if (remainingQuantity > 0)
                Realize(remainingQuantity, price);
            string tag = TradeTag();
            if (tradeDirection > 0)
                Draw.ArrowDown(this, tag + "Exit", false, 0,
                    High[0] + 2 * TickSize, Brushes.White);
            else
                Draw.ArrowUp(this, tag + "Exit", false, 0,
                    Low[0] - 2 * TickSize, Brushes.White);
            AlertOnce("EXIT" + tradeSequence,
                "EAT PAPER EXIT " + reason + " | "
                + realizedPnlTicks.ToString("0") + " contract-ticks",
                Brushes.White,
                realizedPnlTicks >= 0 ? Brushes.DarkGreen : Brushes.DarkRed);
            tradeActive = false;
            phase = Time[0] < tradeEnd
                ? SetupPhase.WaitingBufferClose
                : SetupPhase.SessionDone;
        }

        private void ClearPaperTrade()
        {
            tradeActive = false;
            tradeDirection = 0;
            tradeQuantity = remainingQuantity = tp1Quantity = 0;
            entryPrice = stopPrice = tp1Price = runnerStop = bestPrice = double.NaN;
            tp1Done = false;
            entryBar = -1;
            realizedPnlTicks = 0;
        }

        private string TradeTag()
        {
            return "EATTrade" + sessionStart.ToString("yyyyMMddHHmm")
                + "-" + tradeSequence;
        }

        private void DrawTradeLines()
        {
            if (!tradeActive)
                return;
            string tag = TradeTag();
            Draw.HorizontalLine(this, tag + "EntryLine", entryPrice,
                Brushes.DodgerBlue, DashStyleHelper.Dash, 1);
            Draw.HorizontalLine(this, tag + "StopLine", stopPrice,
                Brushes.Red, DashStyleHelper.Dash, 1);
            Draw.HorizontalLine(this, tag + "TPLine", tp1Price,
                Brushes.LimeGreen, DashStyleHelper.Dash, 1);
            if (!double.IsNaN(runnerStop))
                Draw.HorizontalLine(this, tag + "RunnerLine", runnerStop,
                    Brushes.MediumPurple, DashStyleHelper.Dot, 2);
        }

        private void DrawSessionBox()
        {
            if (sessionStart == DateTime.MinValue)
                return;
            DateTime end = tradeEnd != DateTime.MinValue && Time[0] > tradeEnd
                ? tradeEnd
                : Time[0];
            string tag = "EAT-" + sessionName + "-"
                + sessionStart.ToString("yyyyMMddHHmm");

            if (selectedBoxMinutes <= 0)
            {
                double high = !double.IsNaN(fallbackHigh)
                    ? fallbackHigh : primaryHigh;
                double low = !double.IsNaN(fallbackLow)
                    ? fallbackLow : primaryLow;
                if (!double.IsNaN(high) && !double.IsNaN(low))
                    Draw.Rectangle(this, tag + "-Building", false,
                        sessionStart, high, Time[0], low,
                        Brushes.SteelBlue, Brushes.SteelBlue, 12);
                return;
            }

            Draw.Rectangle(this, tag + "-Range", false,
                sessionStart, innerHigh, end, innerLow,
                Brushes.DodgerBlue, Brushes.DodgerBlue, 8);
            Draw.Rectangle(this, tag + "-TopBuffer", false,
                boxEnd, outerHigh, end, innerHigh,
                Brushes.Turquoise, Brushes.Turquoise, 16);
            Draw.Rectangle(this, tag + "-BottomBuffer", false,
                boxEnd, innerLow, end, outerLow,
                Brushes.IndianRed, Brushes.IndianRed, 16);
            Draw.Line(this, tag + "-InnerHigh", false,
                sessionStart, innerHigh, end, innerHigh,
                Brushes.Aquamarine, DashStyleHelper.Solid, 2);
            Draw.Line(this, tag + "-InnerLow", false,
                sessionStart, innerLow, end, innerLow,
                Brushes.LightCoral, DashStyleHelper.Solid, 2);
            Draw.Line(this, tag + "-OuterHigh", false,
                boxEnd, outerHigh, end, outerHigh,
                Brushes.Turquoise, DashStyleHelper.Dash, 1);
            Draw.Line(this, tag + "-OuterLow", false,
                boxEnd, outerLow, end, outerLow,
                Brushes.IndianRed, DashStyleHelper.Dash, 1);
        }

        private bool IsMarketClosed(DateTime stamp)
        {
            DayOfWeek day = stamp.DayOfWeek;
            TimeSpan time = stamp.TimeOfDay;
            if (day == DayOfWeek.Saturday)
                return true;
            if (day == DayOfWeek.Sunday)
                return time < new TimeSpan(15, 0, 0);
            if (day == DayOfWeek.Friday)
                return time >= new TimeSpan(13, 0, 0);
            return time >= new TimeSpan(13, 0, 0)
                && time < new TimeSpan(15, 0, 0);
        }

        private string StatusDetail()
        {
            if (phase == SetupPhase.BuildingBox)
                return selectedBoxMinutes == -1
                    ? "5-minute box too small; building 15-minute fallback"
                    : "Building first 5-minute session box";
            if (phase == SetupPhase.WaitingBufferClose)
                return "Waiting for a 1-minute close inside either buffer";
            if (phase == SetupPhase.InTrade)
                return "Paper position active; TP1 then 30-tick runner trail";
            if (phase == SetupPhase.SessionDone)
                return "Session complete";
            return phase.ToString();
        }

        private void ShowStatus(string detail)
        {
            string range = double.IsNaN(innerHigh)
                ? "not set"
                : innerLow.ToString("0.00") + " - " + innerHigh.ToString("0.00");
            string text = "EAT " + Instrument.FullName + "\n"
                + "Session: " + (sessionName ?? "waiting") + "\n"
                + "State: " + phase + "\n"
                + "Box: " + range + "\n"
                + "Contracts: " + Contracts
                + " | Trades: " + tradesThisSession + "/" + MaxTradesPerSession
                + "\n" + detail;
            Draw.TextFixed(this, "EATStatus", text, TextPosition.TopRight,
                Brushes.White, new SimpleFont("Consolas", 13),
                Brushes.Black, Brushes.Black, 55);
        }

        private void AlertOnce(string level, string message,
            Brush foreground, Brush background)
        {
            string id = "EAT-" + level + "-"
                + sessionStart.ToString("yyyyMMddHHmm") + "-" + CurrentBar;
            Alert(id, Priority.High, message, "Alert1.wav", 10,
                foreground, background);
        }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contracts", GroupName = "Trade display", Order = 1)]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable New York", GroupName = "Sessions", Order = 1)]
        public bool EnableNY { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "NY start hour PT", GroupName = "Sessions", Order = 2)]
        public int NYStartHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "NY start minute", GroupName = "Sessions", Order = 3)]
        public int NYStartMinute { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable Tokyo", GroupName = "Sessions", Order = 4)]
        public bool EnableTokyo { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "Tokyo start hour PT", GroupName = "Sessions", Order = 5)]
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
        [Display(Name = "London standard hour PT", GroupName = "Sessions", Order = 8)]
        public int LondonStandardHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "London standard minute", GroupName = "Sessions", Order = 9)]
        public int LondonStandardMinute { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "London DST hour PT", GroupName = "Sessions", Order = 10)]
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
        [Range(1, 60)]
        [Display(Name = "Fallback box minutes", GroupName = "Box", Order = 2)]
        public int FallbackBoxMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5000)]
        [Display(Name = "Minimum box ticks", GroupName = "Box", Order = 3)]
        public int MinBoxTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5000)]
        [Display(Name = "Maximum box ticks", GroupName = "Box", Order = 4)]
        public int MaxBoxTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name = "Buffer ticks", GroupName = "Entry", Order = 1)]
        public int BufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 2000)]
        [Display(Name = "TP1 ticks", GroupName = "Exit", Order = 1)]
        public int TP1Ticks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name = "Runner trail ticks", GroupName = "Exit", Order = 2)]
        public int RunnerTrailTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 240)]
        [Display(Name = "Wick stop lookback minutes", GroupName = "Exit", Order = 3)]
        public int WickStopLookbackMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 600)]
        [Display(Name = "Trade window minutes", GroupName = "Session control", Order = 1)]
        public int TradeWindowMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Maximum trades per session", GroupName = "Session control", Order = 2)]
        public int MaxTradesPerSession { get; set; }
    }
}
