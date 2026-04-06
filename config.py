"""
config.py  –  All parameters for the Market Making Engine
"""

# ── Symbol ────────────────────────────────────────────────────────────────────
SYMBOL     = "GBPUSD"
TICK_SIZE  = 0.00010      # minimum price increment

# ── Avellaneda-Stoikov Model ──────────────────────────────────────────────────
GAMMA      = 0.08         # risk-aversion coefficient
SIGMA      = 0.0015       # estimated intra-session volatility
KAPPA      = 2.0          # order-arrival intensity (calibrated)
SESSION_T  = 1 / 24       # session length as fraction of day (1 hour)

# ── Inventory Risk ────────────────────────────────────────────────────────────
MAX_INVENTORY   = 500_000  # units — quoting halted beyond this
DELTA_HEDGE_THR = 300_000  # trigger delta-hedging above this level
BASE_QUOTE_SIZE = 100_000  # base lot size per side

# ── Simulation ────────────────────────────────────────────────────────────────
N_TICKS           = 10_000
INITIAL_MID       = 1.3000
INFORMED_FRACTION = 0.15   # fraction of order flow that is informed (adverse)
GBM_SEED          = 7

# ── Transaction costs ─────────────────────────────────────────────────────────
SPREAD_COST_PCT = 0.0001   # half-spread cost charged on each fill

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL     = "INFO"
LOG_FORMAT    = "%(asctime)s.%(msecs)03d  [%(levelname)5s]  %(message)s"
LOG_DATE_FMT  = "%H:%M:%S"

# ── Output ────────────────────────────────────────────────────────────────────
CHART_DPI     = 150
CHART_OUTPUT  = "mm_dashboard.png"
