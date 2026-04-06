"""
latency.py  –  Nanosecond-resolution latency profiler for hot-path operations
"""
from __future__ import annotations
import time
from collections import defaultdict, deque

import numpy as np
import pandas as pd


class LatencyProfiler:
    """
    Records elapsed nanoseconds for labelled code sections.
    Usage:
        profiler.start("add_order")
        ... code ...
        profiler.stop("add_order")
    """

    def __init__(self, max_samples: int = 100_000):
        self._buckets: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._start:   dict[str, int]   = {}

    def start(self, label: str) -> None:
        self._start[label] = time.perf_counter_ns()

    def stop(self, label: str) -> int:
        elapsed = time.perf_counter_ns() - self._start.pop(label, 0)
        self._buckets[label].append(elapsed)
        return elapsed

    def report(self) -> pd.DataFrame:
        rows = []
        for label, samples in self._buckets.items():
            s = list(samples)
            if not s:
                continue
            rows.append({
                "operation": label,
                "count":     len(s),
                "mean_µs":   round(np.mean(s) / 1_000, 3),
                "median_µs": round(np.median(s) / 1_000, 3),
                "p95_µs":    round(np.percentile(s, 95) / 1_000, 3),
                "p99_µs":    round(np.percentile(s, 99) / 1_000, 3),
                "min_µs":    round(np.min(s) / 1_000, 3),
                "max_µs":    round(np.max(s) / 1_000, 3),
            })
        return pd.DataFrame(rows)

    def summary_str(self) -> str:
        df  = self.report()
        out = [f"\n{'Operation':<22} {'mean µs':>9} {'p99 µs':>9} {'n':>8}"]
        out.append("  " + "─" * 52)
        for _, r in df.iterrows():
            out.append(f"  {r['operation']:<20} {r['mean_µs']:>9.3f} {r['p99_µs']:>9.3f} {r['count']:>8,}")
        return "\n".join(out)
