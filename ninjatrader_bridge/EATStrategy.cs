// Real order-placing port of the EAT box-breakout setup (ported from the VPS's
// /opt/trading_bot_v2/ninjatrader_bridge/eat_strategy.py paper-trading engine).
// EATStrategyIndicator.cs stays as-is (VPS control + chart visuals); this file
// is what actually submits orders. Apply to a 1-minute chart; test on a
// Sim/paper account before ever attaching to a funded combine account.
//
// Session start hours below are "chart local" time, matching the existing
// indicator's convention. The market blackout check converts chart-local time
// to Pacific explicitly (the VPS engine's blackout window is Pacific-based) --
// if this NinjaTrader install displays bars in exchange time rather than
// local time, that conversion assumption should be double-checked against
// how the indicator's own session boxes already line up for you.

using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class EATStrategy : Strategy
    {
        private static readonly TimeZoneInfo PacificTz =
            TimeZoneInfo.FindSystemTimeZoneById("Pacific Standard Time");

        private enum EatPhase
        {
            WaitSession,
            BuildingBox,
            WaitBufferClose,
            InTrade,
            SessionDone
        }

        private sealed class SessionCandidate
        {
            public string Name;
            public DateTime Start;
        }

        private EatPhase phase;
        private string sessionKey;
        private string sessionName;
        private DateTime sessionStart;
        private DateTime tradeEnd;
        private double innerHigh;
        private double innerLow;
        private double outerHigh;
        private double outerLow;
        private bool usedFallback;
        private bool primaryChecked;
        private bool fallbackChecked;
        private int tradesThisSession;
        private string lastZone;

        private string activeDirection;
        private int remainingQuantity;
        private bool tp1Done;
        private double bestPrice;
        private double runnerStop;
        private double pendingStop;
        private double pendingTp1;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Places real orders for the EAT box-breakout setup: " +
                    "half position off at TP1, trailing stop on the runner.";
                Name = "EAT Strategy";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                IsUnmanaged = false;
                IsInstantiatedOnEachOptimizationIteration = true;
                TimeInForce = TimeInForce.Gtc;

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
                TradeWindowMinutes = 600;
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
                phase = EatPhase.WaitSession;
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
                return;
            if (CurrentBar < WickStopLookbackMinutes + 10)
                return;

            DateTime now = Time[0];

            if (phase == EatPhase.InTrade)
            {
                UpdateRunnerTrail();
                return;
            }

            SessionCandidate candidate = FindActiveSession(now);
            if (candidate == null)
            {
                phase = EatPhase.WaitSession;
                return;
            }

            string candidateKey = candidate.Name + ":" + candidate.Start.ToString("O");
            if (candidateKey != sessionKey)
                ResetSession(candidateKey, candidate.Name, candidate.Start);

            if (InMarketBlackout(now))
                return;

            DateTime start = sessionStart;
            DateTime primaryEnd = start.AddMinutes(PrimaryBoxMinutes);
            DateTime fallbackEnd = start.AddMinutes(FallbackBoxMinutes);

            if (now < start)
                return;

            if (phase == EatPhase.BuildingBox)
                TryBuildBox(now, primaryEnd, fallbackEnd);

            if (phase == EatPhase.WaitBufferClose)
                CheckEntry(now);
        }

        // ---- session detection (same convention as EATStrategyIndicator.cs) ----

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
            DateTime latestPossibleEnd = start.AddMinutes(FallbackBoxMinutes + TradeWindowMinutes);
            if (now < start || now > latestPossibleEnd)
                return;
            if (best == null || start > best.Start)
                best = new SessionCandidate { Name = name, Start = start };
        }

        private void ResetSession(string key, string name, DateTime start)
        {
            if (key != null)
                Print(Time[0] + " RESET session=" + name + " start=" + start);
            sessionKey = key;
            sessionName = name;
            sessionStart = start;
            phase = EatPhase.BuildingBox;
            innerHigh = double.NaN;
            innerLow = double.NaN;
            outerHigh = double.NaN;
            outerLow = double.NaN;
            usedFallback = false;
            primaryChecked = false;
            fallbackChecked = false;
            tradesThisSession = 0;
            lastZone = null;
        }

        private bool InMarketBlackout(DateTime chartLocalNow)
        {
            DateTime pacific = TimeZoneInfo.ConvertTime(chartLocalNow, TimeZoneInfo.Local, PacificTz);
            DayOfWeek day = pacific.DayOfWeek;
            TimeSpan tod = pacific.TimeOfDay;

            if (day == DayOfWeek.Saturday)
                return true;
            if (day == DayOfWeek.Sunday)
                return tod < new TimeSpan(15, 0, 0);
            if (day == DayOfWeek.Friday)
                return tod >= new TimeSpan(13, 0, 0);
            return tod >= new TimeSpan(13, 0, 0) && tod < new TimeSpan(15, 0, 0);
        }

        // ---- box building: primary window, fallback extension, min/max bounds ----

        private void TryBuildBox(DateTime now, DateTime primaryEnd, DateTime fallbackEnd)
        {
            if (now < primaryEnd)
            {
                innerHigh = double.IsNaN(innerHigh) ? High[0] : Math.Max(innerHigh, High[0]);
                innerLow = double.IsNaN(innerLow) ? Low[0] : Math.Min(innerLow, Low[0]);
                return;
            }

            if (!primaryChecked)
            {
                primaryChecked = true;
                double ticks = (innerHigh - innerLow) / TickSize;
                if (ticks > MaxBoxTicks)
                {
                    Print(now + " " + sessionName + " box FAIL primary ticks=" + ticks + " (>max " + MaxBoxTicks + ")");
                    phase = EatPhase.SessionDone;
                    return;
                }
                if (ticks >= MinBoxTicks)
                {
                    Print(now + " " + sessionName + " box OK primary ticks=" + ticks);
                    FinalizeBox(primaryEnd);
                    return;
                }
                usedFallback = true;
            }

            if (!usedFallback)
                return;

            if (now < fallbackEnd)
            {
                innerHigh = Math.Max(innerHigh, High[0]);
                innerLow = Math.Min(innerLow, Low[0]);
                return;
            }

            if (!fallbackChecked)
            {
                fallbackChecked = true;
                double ticks = (innerHigh - innerLow) / TickSize;
                if (!(ticks >= MinBoxTicks && ticks <= MaxBoxTicks))
                {
                    Print(now + " " + sessionName + " box FAIL fallback ticks=" + ticks + " (min " + MinBoxTicks + " max " + MaxBoxTicks + ")");
                    phase = EatPhase.SessionDone;
                    return;
                }
                Print(now + " " + sessionName + " box OK fallback ticks=" + ticks);
                FinalizeBox(fallbackEnd);
            }
        }

        private void FinalizeBox(DateTime boxEnd)
        {
            outerHigh = innerHigh + BufferTicks * TickSize;
            outerLow = innerLow - BufferTicks * TickSize;
            tradeEnd = boxEnd.AddMinutes(TradeWindowMinutes);
            phase = EatPhase.WaitBufferClose;
        }

        // ---- entry: close-only buffer-zone check, wick stop, TP1, position split ----

        private void CheckEntry(DateTime now)
        {
            if (phase != EatPhase.WaitBufferClose)
                return;
            if (now > tradeEnd)
            {
                phase = EatPhase.SessionDone;
                return;
            }
            if (tradesThisSession >= MaxTradesPerSession)
            {
                phase = EatPhase.SessionDone;
                return;
            }

            double close = Close[0];
            string zone = ZoneForClose(close);
            if (zone == null)
            {
                lastZone = null;
                return;
            }
            if (lastZone == zone && AllowReentry)
                return;

            string direction = zone == "top" ? "long" : "short";
            if ((direction == "long" && !EnableLongs) || (direction == "short" && !EnableShorts))
            {
                lastZone = zone;
                return;
            }

            Print(now + " " + sessionName + " ENTRY " + direction + " close=" + close +
                " box[" + innerLow + "-" + innerHigh + "] outer[" + outerLow + "-" + outerHigh + "]");
            OpenTrade(direction, close, now);
            lastZone = zone;
        }

        private string ZoneForClose(double close)
        {
            if (double.IsNaN(innerHigh) || double.IsNaN(innerLow) ||
                double.IsNaN(outerHigh) || double.IsNaN(outerLow))
                return null;
            if (close >= innerHigh && close <= outerHigh)
                return "top";
            if (close <= innerLow && close >= outerLow)
                return "bottom";
            return null;
        }

        private void OpenTrade(string direction, double entryPrice, DateTime now)
        {
            double stop;
            double preClampStop;
            if (StopTicksOverride > 0)
            {
                double dist = StopTicksOverride * TickSize;
                stop = direction == "long" ? entryPrice - dist : entryPrice + dist;
                preClampStop = stop;
            }
            else
            {
                stop = WickStop(direction, now);
                preClampStop = stop;
                if (MaxStopTicks > 0)
                {
                    stop = direction == "long"
                        ? Math.Max(stop, entryPrice - MaxStopTicks * TickSize)
                        : Math.Min(stop, entryPrice + MaxStopTicks * TickSize);
                }
            }
            Print(now + " " + sessionName + " STOP StopTicksOverride=" + StopTicksOverride +
                " MaxStopTicks=" + MaxStopTicks +
                " wickStop=" + preClampStop + " finalStop=" + stop +
                " entry=" + entryPrice + " distTicks=" + Math.Round(Math.Abs(entryPrice - stop) / TickSize, 1));
            int quantity = Contracts;

            activeDirection = direction;
            remainingQuantity = quantity;
            tp1Done = false;
            bestPrice = double.NaN;
            runnerStop = double.NaN;
            tradesThisSession++;
            phase = EatPhase.InTrade;

            pendingStop = stop;
            pendingTp1 = direction == "long"
                ? innerHigh + Tp1Ticks * TickSize
                : innerLow - Tp1Ticks * TickSize;

            // Stop/TP1 exits are submitted in OnExecutionUpdate once the entry fill
            // is confirmed -- submitting them here, in the same call as the entry,
            // returns null in historical backtesting because Position is still
            // Flat at this instant (the entry hasn't filled yet).
            if (direction == "long")
                EnterLong(quantity, "EATEntry");
            else
                EnterShort(quantity, "EATEntry");
        }

        // Lowest/highest rejection-wick low/high in the lookback window that
        // wicked into the buffer zone without closing there; falls back to the
        // raw (non-buffered) box edge if no such bar exists.
        private double WickStop(string direction, DateTime entryTime)
        {
            double fallback = direction == "long" ? innerLow : innerHigh;
            DateTime lookbackStart = entryTime.AddMinutes(-WickStopLookbackMinutes);
            double best = double.NaN;

            for (int i = 1; i <= CurrentBar; i++)
            {
                DateTime barTime = Time[i];
                if (barTime < lookbackStart)
                    break;
                if (barTime >= entryTime)
                    continue;

                if (direction == "long")
                {
                    double low = Low[i];
                    if (low >= outerLow && low < innerLow && Close[i] >= innerLow)
                        best = double.IsNaN(best) ? low : Math.Min(best, low);
                }
                else
                {
                    double high = High[i];
                    if (high > innerHigh && high <= outerHigh && Close[i] <= innerHigh)
                        best = double.IsNaN(best) ? high : Math.Max(best, high);
                }
            }

            return double.IsNaN(best) ? fallback : best;
        }

        // ---- runner trail: one-directional ratchet, re-issued each live bar ----

        private Order SubmitProtectiveStop(int quantity, double requestedStop,
            double executionPrice, DateTime now, string context)
        {
            if (quantity <= 0)
                return null;

            double stop = Instrument.MasterInstrument.RoundToTickSize(requestedStop);
            double barClose = Close[0];

            // With Calculate.OnBarClose, an entry fill or a runner update can be
            // processed after this bar has already crossed the intended stop.
            // Submitting that now-wrong-side stop makes NinjaTrader reject the
            // order and can cause later orders in an Analyzer iteration to be
            // ignored. Once the intended stop is breached, flatten immediately
            // instead of moving the stop farther away from the market.
            bool alreadyBreached = activeDirection == "long"
                ? stop >= Math.Min(executionPrice, barClose)
                : stop <= Math.Max(executionPrice, barClose);

            if (alreadyBreached)
            {
                Print(now + " " + sessionName + " " + context +
                    " STOP ALREADY BREACHED requested=" + stop +
                    " execution=" + executionPrice + " close=" + barClose +
                    " -> market exit");

                if (activeDirection == "long")
                    ExitLong(quantity, "EATStopNow", "EATEntry");
                else
                    ExitShort(quantity, "EATStopNow", "EATEntry");
                return null;
            }

            return activeDirection == "long"
                ? ExitLongStopMarket(0, true, quantity, stop, "EATStop", "EATEntry")
                : ExitShortStopMarket(0, true, quantity, stop, "EATStop", "EATEntry");
        }

        private void UpdateRunnerTrail()
        {
            if (!tp1Done || remainingQuantity <= 0)
                return;

            if (activeDirection == "long")
            {
                bestPrice = Math.Max(bestPrice, High[0]);
                double candidate = bestPrice - RunnerTrailTicks * TickSize;
                runnerStop = Math.Max(runnerStop, candidate);
                SubmitProtectiveStop(remainingQuantity, runnerStop, Close[0],
                    Time[0], "RUNNER");
            }
            else
            {
                bestPrice = Math.Min(bestPrice, Low[0]);
                double candidate = bestPrice + RunnerTrailTicks * TickSize;
                runnerStop = Math.Min(runnerStop, candidate);
                SubmitProtectiveStop(remainingQuantity, runnerStop, Close[0],
                    Time[0], "RUNNER");
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution?.Order == null)
                return;

            string signal = execution.Order.Name;
            Print(time + " EXEC signal=\"" + signal + "\" qty=" + quantity + " price=" + price +
                " marketPos=" + marketPosition + " remainingBefore=" + remainingQuantity);

            if (signal == "EATEntry")
            {
                int tp1Qty = (int)Math.Ceiling(quantity / 2.0);
                Order stopOrder, tp1Order;
                if (activeDirection == "long")
                {
                    stopOrder = SubmitProtectiveStop(quantity, pendingStop, price,
                        time, "ENTRY");
                    tp1Order = stopOrder == null
                        ? null
                        : ExitLongLimit(0, true, tp1Qty, pendingTp1, "EATTp1", "EATEntry");
                }
                else
                {
                    stopOrder = SubmitProtectiveStop(quantity, pendingStop, price,
                        time, "ENTRY");
                    tp1Order = stopOrder == null
                        ? null
                        : ExitShortLimit(0, true, tp1Qty, pendingTp1, "EATTp1", "EATEntry");
                }
                Print(time + " ORDERS stop=" + (stopOrder == null ? "NULL" : stopOrder.OrderState.ToString()) +
                    " tp1=" + (tp1Order == null ? "NULL" : tp1Order.OrderState.ToString()));
                return;
            }

            if (signal == "EATTp1" && Position.MarketPosition != MarketPosition.Flat)
            {
                remainingQuantity -= quantity;
                tp1Done = true;

                bestPrice = price;
                runnerStop = activeDirection == "long"
                    ? price - RunnerTrailTicks * TickSize
                    : price + RunnerTrailTicks * TickSize;

                SubmitProtectiveStop(remainingQuantity, runnerStop, price,
                    time, "TP1 RUNNER");
                return;
            }

            // Any fill that leaves the position flat ends the trade, whichever
            // order caused it -- a full-size EATTp1, the EATStop, or a forced
            // "Exit on session close" flatten (name-matching only "EATStop"
            // missed that last case and left the state machine stuck InTrade).
            if (Position.MarketPosition == MarketPosition.Flat)
                CloseOutTrade(time);
        }

        private void CloseOutTrade(DateTime closeTime)
        {
            phase = (AllowReentry && closeTime < tradeEnd) ? EatPhase.WaitBufferClose : EatPhase.SessionDone;
            Print(closeTime + " " + sessionName + " CLOSE -> " + phase + " (tradeEnd=" + tradeEnd + ")");
            tp1Done = false;
            remainingQuantity = 0;
            bestPrice = double.NaN;
            runnerStop = double.NaN;
            activeDirection = null;
        }

        #region Properties

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
        [Display(Name = "Buffer ticks (entry zone width)", GroupName = "Entry", Order = 1)]
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

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Contracts", GroupName = "Order Management", Order = 1)]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Max trades per session", GroupName = "Order Management", Order = 2)]
        public int MaxTradesPerSession { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow re-entry", GroupName = "Order Management", Order = 3)]
        public bool AllowReentry { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable longs", GroupName = "Order Management", Order = 4)]
        public bool EnableLongs { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable shorts", GroupName = "Order Management", Order = 5)]
        public bool EnableShorts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2000)]
        [Display(Name = "Max stop ticks (0 = off, uses wick stop as-is)", GroupName = "Order Management", Order = 6)]
        public int MaxStopTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2000)]
        [Display(Name = "Stop ticks override (0 = off, forces exact stop distance)", GroupName = "Order Management", Order = 7)]
        public int StopTicksOverride { get; set; }

        #endregion
    }
}
