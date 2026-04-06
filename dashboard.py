"""
dashboard.py  –  Performance visualisation for the Market Making Engine
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import config


def plot(pnl_history: list[float], spread_capture_series: list[float],
         adv_sel_series: list[float], inventory_series: list[float],
         spread_series: list[float], latency_df) -> None:

    fig = plt.figure(figsize=(18, 10), facecolor="#0f1117")
    gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.50, wspace=0.38)

    DARK  = "#0f1117"
    GRID  = "#1e2130"
    GREEN = "#00d4aa"
    RED   = "#ff4d6d"
    BLUE  = "#4d9de0"
    AMBER = "#f7b731"
    WHITE = "#e8eaf6"

    def _style(ax):
        ax.set_facecolor(GRID)
        ax.tick_params(colors=WHITE, labelsize=7)
        ax.spines[:].set_color("#2a2d3e")
        ax.title.set_color(WHITE)
        ax.xaxis.label.set_color(WHITE)
        ax.yaxis.label.set_color(WHITE)
        ax.grid(alpha=0.2, color="#3a3d50")

    # ── P&L Curve ────────────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    _style(ax1)
    ax1.plot(pnl_history, color=GREEN, linewidth=1.2, label="Cumulative P&L")
    ax1.fill_between(range(len(pnl_history)), pnl_history, alpha=0.15, color=GREEN)
    ax1.axhline(0, color=RED, linestyle="--", alpha=0.5)
    ax1.set_title("Cumulative Mark-to-Market P&L", fontweight="bold")
    ax1.set_ylabel("P&L")
    ax1.legend(fontsize=8, facecolor=GRID, labelcolor=WHITE)

    # ── Inventory ─────────────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    _style(ax2)
    colors_inv = [GREEN if v >= 0 else RED for v in inventory_series]
    ax2.bar(range(len(inventory_series)), inventory_series,
            color=colors_inv, width=1.0, alpha=0.7)
    ax2.axhline(config.MAX_INVENTORY, color=AMBER, linestyle=":", alpha=0.7,
                label="Max inv")
    ax2.axhline(-config.MAX_INVENTORY, color=AMBER, linestyle=":", alpha=0.7)
    ax2.set_title("Inventory (units)", fontweight="bold")
    ax2.legend(fontsize=7, facecolor=GRID, labelcolor=WHITE)

    # ── P&L Attribution ───────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, :2])
    _style(ax3)
    ax3.plot(np.cumsum(spread_capture_series), color=GREEN,
             linewidth=1.2, label="Spread Capture")
    ax3.plot(np.cumsum(adv_sel_series), color=RED,
             linewidth=1.2, label="Adverse Selection")
    ax3.set_title("P&L Attribution: Spread Capture vs Adverse Selection",
                  fontweight="bold")
    ax3.legend(fontsize=8, facecolor=GRID, labelcolor=WHITE)

    # ── Quoted Spread over time ────────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    _style(ax4)
    spread_pips = [s * 10_000 for s in spread_series]
    ax4.plot(spread_pips, color=BLUE, linewidth=0.8, alpha=0.9)
    ax4.set_title("Quoted Spread (pips)", fontweight="bold")
    ax4.set_ylabel("Pips")

    # ── Latency Profile ───────────────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[2, :2])
    _style(ax5)
    if latency_df is not None and not latency_df.empty:
        ops   = latency_df["operation"]
        means = latency_df["mean_µs"]
        p99s  = latency_df["p99_µs"]
        x     = np.arange(len(ops))
        ax5.bar(x - 0.2, means, 0.4, label="Mean µs", color=BLUE, alpha=0.8)
        ax5.bar(x + 0.2, p99s,  0.4, label="P99 µs",  color=AMBER, alpha=0.8)
        ax5.set_xticks(x)
        ax5.set_xticklabels(ops, rotation=20, ha="right", fontsize=7)
        ax5.set_title("Latency Profile (µs)", fontweight="bold")
        ax5.legend(fontsize=8, facecolor=GRID, labelcolor=WHITE)

    # ── Rolling Sharpe ────────────────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[2, 2])
    _style(ax6)
    pnl_arr = np.array(pnl_history)
    rets    = np.diff(pnl_arr)
    window  = max(100, len(rets) // 20)
    roll_sh = [
        (rets[max(0,i-window):i].mean() /
         (rets[max(0,i-window):i].std() + 1e-12)) * (252*24)**0.5
        for i in range(window, len(rets))
    ]
    ax6.plot(roll_sh, color=AMBER, linewidth=1.0)
    ax6.axhline(0, color=RED, linestyle="--", alpha=0.5)
    ax6.set_title(f"Rolling Sharpe (window={window})", fontweight="bold")

    fig.suptitle(f"Market Making Engine Dashboard  ─  {config.SYMBOL}",
                 fontsize=14, fontweight="bold", color=WHITE, y=1.01)

    plt.savefig(config.CHART_OUTPUT, dpi=config.CHART_DPI,
                bbox_inches="tight", facecolor=DARK)
    print(f"\nDashboard saved → {config.CHART_OUTPUT}")
