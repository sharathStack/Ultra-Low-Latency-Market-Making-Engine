"""
simulator.py  –  Simulated exchange feed and client order flow generator

- GBM tick generator (mid price evolution)
- Informed trader model (adverse selection)
- Noise trader model (random direction market/limit orders)
"""
from __future__ import annotations
import math
from typing import Optional

import numpy as np

import config
from models import Order, Side, OrderType


class MarketSimulator:
    """
    Generates synthetic tick-by-tick price and order flow.

    Informed traders know the true drift and trade against stale MM quotes.
    Noise traders are random. The mix is controlled by INFORMED_FRACTION.
    """

    def __init__(self):
        np.random.seed(config.GBM_SEED)
        self.price          = config.INITIAL_MID
        self.sigma          = config.SIGMA
        self.informed_frac  = config.INFORMED_FRACTION
        self._dt            = 1 / 86400          # 1-second tick in day fraction
        self._true_drift    = (np.random.choice([-1, 1])
                               * self.sigma * 3)  # hidden directional drift

    def next_tick(self) -> float:
        shock = np.random.normal(0, self.sigma * math.sqrt(self._dt))
        self.price *= math.exp(shock)
        return self.price

    def generate_order(self, best_bid: Optional[float],
                       best_ask: Optional[float]) -> Optional[Order]:
        if best_bid is None or best_ask is None:
            return None

        mid              = (best_bid + best_ask) / 2
        is_informed      = np.random.rand() < self.informed_frac

        if is_informed:
            direction = Side.BID if self._true_drift > 0 else Side.ASK
        else:
            direction = Side.BID if np.random.rand() > 0.5 else Side.ASK

        # 70% market orders, 30% limit orders
        if np.random.rand() < 0.70:
            return Order.new_market(direction,
                                    qty=self._random_qty())
        else:
            offset = np.random.uniform(0, 3) * config.TICK_SIZE
            price  = (best_ask + offset if direction == Side.BID
                      else best_bid - offset)
            return Order.new_limit(direction, round(price, 5),
                                   self._random_qty())

    @staticmethod
    def _random_qty() -> float:
        return float(np.random.choice(
            [10_000, 50_000, 100_000, 200_000],
            p=[0.40, 0.30, 0.20, 0.10]
        ))
