"""
main.py  –  Market Making Engine entry point & async event loop orchestrator

Flow per tick:
  1. Receive new mid-price tick
  2. Cancel stale MM quotes
  3. Check risk limits
  4. Compute A-S quotes → submit to order book
  5. Simulate incoming client order → match
  6. Dispatch fill events to market maker
  7. Run risk checks (delta-hedge if needed)
"""

import asyncio
import logging

import config
from order_book import OrderBook
from market_maker import AvellanedaStoikovMM
from simulator import MarketSimulator
from risk import RiskManager
from latency import LatencyProfiler
from models import Side, FillEvent
import dashboard

logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT,
                    datefmt=config.LOG_DATE_FMT)
log = logging.getLogger("Main")

# ── Telemetry series for dashboard ────────────────────────────────────────────
_spread_series:   list[float] = []
_inv_series:      list[float] = []
_sc_series:       list[float] = []   # spread capture deltas
_as_series:       list[float] = []   # adverse selection deltas


async def run_engine() -> None:
    book    = OrderBook(config.SYMBOL, tick_size=config.TICK_SIZE)
    mm      = AvellanedaStoikovMM()
    sim     = MarketSimulator()
    risk    = RiskManager()
    profiler = LatencyProfiler()

    mm_bid_id: str | None = None
    mm_ask_id: str | None = None
    tick_count = quote_count = fill_count = 0
    dt = 1 / 86400    # 1-second tick in day fraction

    log.info("Engine start | symbol=%s | ticks=%d", config.SYMBOL, config.N_TICKS)

    for _ in range(config.N_TICKS):
        await asyncio.sleep(0)    # cooperative yield

        profiler.start("tick_total")

        # ── 1. New tick ───────────────────────────────────────────────────────
        mid   = sim.next_tick()
        micro = book.micro_price() or mid
        mm.update_time(dt)
        tick_count += 1

        # ── 2. Cancel stale quotes ────────────────────────────────────────────
        if mm_bid_id:
            book.cancel_order(mm_bid_id)
        if mm_ask_id:
            book.cancel_order(mm_ask_id)

        # ── 3. Risk check ─────────────────────────────────────────────────────
        hedge_orders = risk.check(mm.inventory, mid)
        for ho in hedge_orders:
            book.add_order(ho)

        if not risk.is_quoting_allowed(mm.inventory):
            profiler.stop("tick_total")
            continue

        # ── 4. Generate & submit MM quotes ────────────────────────────────────
        quote = mm.quote(micro)
        if quote:
            from models import Order
            bid_ord = Order.new_limit(Side.BID, quote.bid_price, quote.bid_size,
                                      order_id=f"MM_B_{tick_count}")
            ask_ord = Order.new_limit(Side.ASK, quote.ask_price, quote.ask_size,
                                      order_id=f"MM_A_{tick_count}")
            book.add_order(bid_ord)
            book.add_order(ask_ord)
            mm_bid_id, mm_ask_id = bid_ord.order_id, ask_ord.order_id
            quote_count += 1
            _spread_series.append(quote.spread)

        # ── 5. Simulate client order ──────────────────────────────────────────
        client_ord = sim.generate_order(book.best_bid, book.best_ask)
        if client_ord:
            fills = book.add_order(client_ord)
            prev_sc = mm.spread_capture
            prev_as = mm.adverse_selection
            for fill in fills:
                if fill.maker_id.startswith("MM_"):
                    side = (Side.BID if fill.maker_id.startswith("MM_B_")
                            else Side.ASK)
                    mm.on_fill(FillEvent(side=side, price=fill.price,
                                         qty=fill.qty, mid_at_fill=micro))
                    fill_count += 1
            _sc_series.append(mm.spread_capture - prev_sc)
            _as_series.append(mm.adverse_selection - prev_as)

        _inv_series.append(mm.inventory)
        profiler.stop("tick_total")

    log.info("Engine done | quotes=%d | fills=%d", quote_count, fill_count)

    # ── Report ────────────────────────────────────────────────────────────────
    stats = mm.stats()
    print("\n" + "═" * 55)
    print(f"  MARKET MAKING REPORT  ─  {config.SYMBOL}")
    print("═" * 55)
    for k, v in stats.items():
        print(f"  {k:<28} {v}")
    print(f"  {'ticks':28} {tick_count:,}")
    print(f"  {'quotes':28} {quote_count:,}")
    print(f"  {'fills':28} {fill_count:,}")
    print(f"  {'hedges_fired':28} {risk.summary()['hedges_fired']}")

    # Latency
    print(profiler.summary_str())
    print(book.profiler.summary_str())

    # Dashboard
    dashboard.plot(
        pnl_history          = mm.pnl_history,
        spread_capture_series= _sc_series,
        adv_sel_series       = _as_series,
        inventory_series     = _inv_series,
        spread_series        = _spread_series,
        latency_df           = profiler.report(),
    )


if __name__ == "__main__":
    asyncio.run(run_engine())
