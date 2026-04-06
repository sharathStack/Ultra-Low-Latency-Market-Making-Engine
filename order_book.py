"""
order_book.py  –  Level-2 limit order book (price-time priority, O(log n))
"""
from __future__ import annotations
from typing import Optional

from sortedcontainers import SortedDict

from models import Order, Trade, Side, OrderType, OrderStatus
from latency import LatencyProfiler


class OrderBook:
    """
    Double-sided limit order book.
    - Bids: highest price first  (key negated)
    - Asks: lowest  price first  (natural key)
    Each price level is a FIFO list of Orders.
    """

    def __init__(self, symbol: str, tick_size: float = 0.00010):
        self.symbol    = symbol
        self.tick_size = tick_size
        self._bids: SortedDict = SortedDict(lambda x: -x)
        self._asks: SortedDict = SortedDict()
        self._orders: dict[str, Order] = {}
        self.trades:  list[Trade] = []
        self.profiler = LatencyProfiler()

    # ── Public API ────────────────────────────────────────────────────────────
    def add_order(self, order: Order) -> list[Trade]:
        self.profiler.start("add_order")
        filled: list[Trade] = []
        if order.order_type == OrderType.MARKET:
            filled = self._match_market(order)
        else:
            filled = self._match_limit(order)
            if order.remaining > 1e-9:
                self._insert(order)
        self.trades.extend(filled)
        self.profiler.stop("add_order")
        return filled

    def cancel_order(self, order_id: str) -> bool:
        self.profiler.start("cancel_order")
        order = self._orders.pop(order_id, None)
        if order is None:
            self.profiler.stop("cancel_order")
            return False
        book = self._bids if order.side == Side.BID else self._asks
        lvl  = book.get(order.price)
        if lvl:
            try:
                lvl.remove(order)
            except ValueError:
                pass
            if not lvl:
                del book[order.price]
        order.status = OrderStatus.CANCELED
        self.profiler.stop("cancel_order")
        return True

    # ── Properties ────────────────────────────────────────────────────────────
    @property
    def best_bid(self) -> Optional[float]:
        return next(iter(self._bids), None)

    @property
    def best_ask(self) -> Optional[float]:
        return next(iter(self._asks), None)

    @property
    def mid_price(self) -> Optional[float]:
        bb, ba = self.best_bid, self.best_ask
        return (bb + ba) / 2 if bb and ba else None

    @property
    def spread(self) -> Optional[float]:
        bb, ba = self.best_bid, self.best_ask
        return (ba - bb) if bb and ba else None

    def micro_price(self) -> Optional[float]:
        """Volume-weighted mid: adjusts for order-book imbalance."""
        bb, ba = self.best_bid, self.best_ask
        if not (bb and ba):
            return None
        bv = sum(o.remaining for o in self._bids.get(bb, []))
        av = sum(o.remaining for o in self._asks.get(ba, []))
        total = bv + av
        if total < 1e-9:
            return (bb + ba) / 2
        return (bb * av + ba * bv) / total

    def depth_snapshot(self, levels: int = 5) -> dict:
        bids = [(p, sum(o.remaining for o in q))
                for p, q in list(self._bids.items())[:levels]]
        asks = [(p, sum(o.remaining for o in q))
                for p, q in list(self._asks.items())[:levels]]
        return {"bids": bids, "asks": asks}

    # ── Internal matching ─────────────────────────────────────────────────────
    def _match_limit(self, order: Order) -> list[Trade]:
        trades, opposite = [], self._asks if order.side == Side.BID else self._bids
        while order.remaining > 1e-9 and opposite:
            bp = next(iter(opposite))
            if order.side == Side.BID and order.price < bp:
                break
            if order.side == Side.ASK and order.price > bp:
                break
            trades.extend(self._fill_level(order, opposite, bp))
        return trades

    def _match_market(self, order: Order) -> list[Trade]:
        trades, opposite = [], self._asks if order.side == Side.BID else self._bids
        while order.remaining > 1e-9 and opposite:
            bp = next(iter(opposite))
            trades.extend(self._fill_level(order, opposite, bp))
        return trades

    def _fill_level(self, aggressor: Order, book: SortedDict,
                    price: float) -> list[Trade]:
        import uuid
        trades, queue, to_remove = [], book[price], []
        for passive in queue:
            if aggressor.remaining < 1e-9:
                break
            qty = min(aggressor.remaining, passive.remaining)
            aggressor.filled_qty += qty
            passive.filled_qty   += qty
            aggressor.status = OrderStatus.FILLED if aggressor.remaining < 1e-9 else OrderStatus.PARTIAL
            passive.status   = OrderStatus.FILLED if passive.remaining  < 1e-9 else OrderStatus.PARTIAL
            trades.append(Trade(str(uuid.uuid4())[:8], aggressor.side,
                                price, qty, passive.order_id, aggressor.order_id))
            if passive.remaining < 1e-9:
                to_remove.append(passive)
                self._orders.pop(passive.order_id, None)
        for o in to_remove:
            queue.remove(o)
        if not queue:
            del book[price]
        return trades

    def _insert(self, order: Order) -> None:
        book = self._bids if order.side == Side.BID else self._asks
        if order.price not in book:
            book[order.price] = []
        book[order.price].append(order)
        self._orders[order.order_id] = order
