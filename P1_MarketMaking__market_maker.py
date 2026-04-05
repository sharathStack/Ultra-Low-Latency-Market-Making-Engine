"""
market_maker.py  –  Avellaneda-Stoikov (2008) inventory-adjusted quoting model

Reservation price : r(s,q,t) = s  -  q · γ · σ² · (T-t)
Optimal spread    : δ_bid + δ_ask = γ·σ²·(T-t) + (2/γ)·ln(1 + γ/κ)

References:
  Avellaneda & Stoikov (2008) "High-frequency trading in a limit order book"
"""
from __future__ import annotations
import math
from typing import Optional

import numpy as np

import config
from models import Side, Quote, FillEvent


class AvellanedaStoikovMM:

    def __init__(self):
        self.gamma   = config.GAMMA
        self.sigma   = config.SIGMA
        self.kappa   = config.KAPPA
        self.T       = config.SESSION_T
        self.max_inv = config.MAX_INVENTORY
        self.tick    = config.TICK_SIZE

        # State
        self.inventory: float = 0.0
        self.cash:      float = 0.0
        self._t:        float = 0.0

        # P&L attribution
        self.spread_capture:    float = 0.0
        self.adverse_selection: float = 0.0
        self.pnl_history:       list[float] = [0.0]

    # ── Time ─────────────────────────────────────────────────────────────────
    def update_time(self, dt: float) -> None:
        self._t = min(self._t + dt, self.T)

    @property
    def time_remaining(self) -> float:
        return max(self.T - self._t, 1e-6)

    # ── Model ─────────────────────────────────────────────────────────────────
    def reservation_price(self, micro_price: float) -> float:
        return micro_price - self.inventory * self.gamma * self.sigma**2 * self.time_remaining

    def optimal_half_spread(self) -> float:
        term1 = 0.5 * self.gamma * self.sigma**2 * self.time_remaining
        term2 = (1 / self.gamma) * math.log(1 + self.gamma / self.kappa)
        return term1 + term2

    def quote(self, micro_price: float) -> Optional[Quote]:
        if abs(self.inventory) >= self.max_inv:
            return None

        r     = self.reservation_price(micro_price)
        delta = self.optimal_half_spread()

        # Skew quotes away from inventory direction
        inv_frac = self.inventory / self.max_inv          # –1 to +1
        skew_adj = inv_frac * delta * 0.4

        bid = self._round(r - delta - skew_adj)
        ask = self._round(r + delta - skew_adj)

        # Size: reduce when inventory is large
        size_f   = max(0.1, 1.0 - abs(self.inventory) / self.max_inv)
        qty      = config.BASE_QUOTE_SIZE * size_f

        return Quote(bid_price=bid, bid_size=qty,
                     ask_price=ask, ask_size=qty,
                     fair_value=r, spread=ask - bid)

    # ── Fill Handler ──────────────────────────────────────────────────────────
    def on_fill(self, event: FillEvent) -> None:
        if event.side == Side.BID:
            self.inventory += event.qty
            self.cash      -= event.price * event.qty
        else:
            self.inventory -= event.qty
            self.cash      += event.price * event.qty

        r    = self.reservation_price(event.mid_at_fill)
        edge = (r - event.price) if event.side == Side.BID else (event.price - r)
        if edge > 0:
            self.spread_capture    += edge * event.qty
        else:
            self.adverse_selection += abs(edge) * event.qty

        mtm = self.cash + self.inventory * event.mid_at_fill
        self.pnl_history.append(mtm)

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        pnl = np.array(self.pnl_history)
        ret = np.diff(pnl)
        sharpe = (ret.mean() / (ret.std() + 1e-12)) * math.sqrt(252 * 24)
        dd     = float(np.min(pnl - np.maximum.accumulate(pnl)))
        return {
            "inventory":         self.inventory,
            "cash":              round(self.cash, 4),
            "total_pnl":         round(float(pnl[-1]), 5),
            "spread_capture":    round(self.spread_capture, 5),
            "adverse_selection": round(self.adverse_selection, 5),
            "net_edge":          round(self.spread_capture - self.adverse_selection, 5),
            "sharpe_ann":        round(sharpe, 3),
            "max_drawdown":      round(dd, 5),
        }

    def _round(self, price: float) -> float:
        return round(round(price / self.tick) * self.tick, 6)
