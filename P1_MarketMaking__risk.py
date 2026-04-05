"""
risk.py  –  Inventory risk management and delta-hedging logic
"""
from __future__ import annotations
import logging

import config
from models import Side, Order

log = logging.getLogger("Risk")


class RiskManager:
    """
    Monitors inventory exposure and fires delta-hedge orders
    when the position breaches the configured threshold.
    """

    def __init__(self):
        self.hedge_threshold = config.DELTA_HEDGE_THR
        self.max_inventory   = config.MAX_INVENTORY
        self._hedges_fired   = 0

    def check(self, inventory: float, mid: float) -> list[Order]:
        """
        Returns a list of hedge orders to submit (empty if no action needed).
        Hedge: market order in the opposite direction to flatten position.
        """
        orders: list[Order] = []

        if abs(inventory) < self.hedge_threshold:
            return orders

        qty    = abs(inventory) * 0.5    # partial hedge: reduce by 50%
        side   = Side.ASK if inventory > 0 else Side.BID

        log.warning("RISK | Inventory %.0f exceeds threshold %.0f → "
                    "firing %s hedge %.0f units", inventory,
                    self.hedge_threshold, side.value, qty)

        orders.append(Order.new_market(side, qty))
        self._hedges_fired += 1
        return orders

    def is_quoting_allowed(self, inventory: float) -> bool:
        """Hard limit: suspend quoting if max inventory is breached."""
        if abs(inventory) >= self.max_inventory:
            log.error("RISK | Max inventory %.0f reached – quoting SUSPENDED.",
                      inventory)
            return False
        return True

    def summary(self) -> dict:
        return {"hedges_fired": self._hedges_fired,
                "threshold":    self.hedge_threshold,
                "max_inv":      self.max_inventory}
