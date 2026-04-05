"""
models.py  –  Core data classes: Order, Trade, Quote, Fill
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Side(Enum):
    BID = "BID"
    ASK = "ASK"


class OrderType(Enum):
    LIMIT  = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(Enum):
    NEW      = "NEW"
    PARTIAL  = "PARTIAL"
    FILLED   = "FILLED"
    CANCELED = "CANCELED"


@dataclass
class Order:
    order_id:   str
    side:       Side
    price:      float
    qty:        float
    order_type: OrderType   = OrderType.LIMIT
    status:     OrderStatus = OrderStatus.NEW
    filled_qty: float       = 0.0
    ts_ns:      int         = field(default_factory=time.perf_counter_ns)

    @property
    def remaining(self) -> float:
        return self.qty - self.filled_qty

    @classmethod
    def new_limit(cls, side: Side, price: float, qty: float,
                  order_id: Optional[str] = None) -> "Order":
        return cls(order_id=order_id or str(uuid.uuid4())[:10],
                   side=side, price=price, qty=qty, order_type=OrderType.LIMIT)

    @classmethod
    def new_market(cls, side: Side, qty: float) -> "Order":
        price = 0.0  # market order – matched at best available
        return cls(order_id=str(uuid.uuid4())[:10],
                   side=side, price=price, qty=qty, order_type=OrderType.MARKET)


@dataclass
class Trade:
    trade_id:  str
    aggressor: Side
    price:     float
    qty:       float
    maker_id:  str
    taker_id:  str
    ts_ns:     int = field(default_factory=time.perf_counter_ns)


@dataclass
class Quote:
    bid_price:  float
    bid_size:   float
    ask_price:  float
    ask_size:   float
    fair_value: float
    spread:     float

    def __str__(self) -> str:
        return (f"Quote  bid={self.bid_price:.5f}×{self.bid_size:,.0f} | "
                f"ask={self.ask_price:.5f}×{self.ask_size:,.0f} | "
                f"FV={self.fair_value:.5f}  spread={self.spread*10000:.1f}pips")


@dataclass
class FillEvent:
    """Emitted when the market maker is filled on a resting quote."""
    side:         Side
    price:        float
    qty:          float
    mid_at_fill:  float
    is_mm_maker:  bool = True
