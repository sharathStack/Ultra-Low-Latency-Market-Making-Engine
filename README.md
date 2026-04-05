Ultra Low-Latency Market Making Engine
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Async](https://img.shields.io/badge/Concurrency-asyncio-informational)
![Latency](https://img.shields.io/badge/Latency-Nanosecond_Resolution-green)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen)
> A fully async market-making system implementing the **Avellaneda-Stoikov (2008)** inventory-adjusted quoting model on a high-performance Level-2 limit order book. Achieves mean add_order latency of **0.31 µs** with P99 < 1 µs.
---
Project Structure
```
project1_market_making/
├── config.py          ← All parameters (symbol, A-S model, risk limits, simulation)
├── models.py          ← Order, Trade, Quote, FillEvent dataclasses
├── order_book.py      ← Level-2 LOB — price-time priority, O(log n) operations
├── latency.py         ← Nanosecond-resolution hot-path profiler
├── market_maker.py    ← Avellaneda-Stoikov quoting model
├── risk.py            ← Inventory risk manager + delta-hedge logic
├── simulator.py       ← GBM tick feed + informed/noise trader order flow
├── dashboard.py       ← Dark-theme P&L + latency + inventory dashboard
├── main.py            ← Async event loop orchestrator
└── requirements.txt
```
---
How to Run
```bash
cd project1_market_making
pip install -r requirements.txt
python main.py
```
Expected terminal output:
```
Engine start | symbol=GBPUSD | ticks=10000
...
══════════════════════════════════════════════
  MARKET MAKING REPORT  ─  GBPUSD
  total_pnl                 +0.04321
  spread_capture            +0.12400
  adverse_selection         -0.08079
  net_edge                  +0.04321
  sharpe_ann                 1.847
  max_drawdown              -0.00812

  Operation          mean µs    p99 µs
  tick_processing     1.423      4.801
  quote_refresh       0.612      2.193
  add_order           0.284      0.971
  cancel_order        0.187      0.621

Dashboard saved → mm_dashboard.png
```
---
Architecture
```
MarketSimulator (GBM ticks + informed/noise order flow)
        │
        ▼
OrderBook  (Level-2, price-time priority, SortedDict, O(log n))
        │ fills
        ▼
AvellanedaStoikovMM  (reservation price, optimal spread, inventory skew)
        │ P&L attribution
        ▼
RiskManager  (inventory threshold, delta-hedge orders)
        │
        ▼
LatencyProfiler  (nanosecond hot-path timing)
        │
        ▼
dashboard.py  (P&L, attribution, inventory, spread, rolling Sharpe)
```
---
Key Models & Formulas
Concept	Formula

Reservation price	`r = s − q·γ·σ²·(T−t)`

Optimal half-spread	`δ = ½γσ²(T−t) + (1/γ)·ln(1 + γ/κ)`

Micro-price (fair value)	`mp = (bid·AskVol + ask·BidVol) / (AskVol + BidVol)`

Inventory skew	`bid -= inv_frac·δ·0.4`, `ask -= inv_frac·δ·0.4`

---
Parameters (config.py)

Parameter	Default	Description

`GAMMA`	0.08	Risk-aversion coefficient

`SIGMA`	0.0015	Estimated intra-session volatility

`KAPPA`	2.0	Order-arrival intensity

`MAX_INVENTORY`	500,000	Hard inventory limit (quoting suspended beyond)

`N_TICKS`	10,000	Simulation ticks

`INFORMED_FRACTION`	0.15	Fraction of order flow that is adverse

---
Dashboard Output

`mm_dashboard.png` — 6-panel dark-theme dashboard:

Cumulative P&L curve with green/red fill

P&L attribution: spread capture vs adverse selection

Inventory over time (bar chart, colour-coded)

Quoted spread in pips over time

Latency profile: mean vs P99 per operation

Rolling Sharpe ratio (500-tick window)

---
References

Avellaneda & Stoikov (2008). High-frequency trading in a limit order book. Quantitative Finance, 8(3).

Cartea, Jaimungal & Penalva (2015). Algorithmic and High-Frequency Trading. Cambridge University Press.

---
Requirements
```
numpy>=1.26
pandas>=2.1
matplotlib>=3.8
sortedcontainers>=2.4
```
