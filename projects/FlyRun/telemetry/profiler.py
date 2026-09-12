"""High-resolution latency profiler and neuromorphic SynOps / FLOPs estimator.

Benchmarks compliance with sub-millisecond real-time execution deadlines.
"""

from __future__ import annotations
import time
import numpy as np
import torch
from typing import Dict, Any, List


class LatencyProfiler:
    """Microsecond-precision execution timer and statistical analyzer."""

    def __init__(self, name: str = "FlyRun_Inference"):
        self.name = name
        self.durations_us: List[float] = []
        self._start_ns: int = 0

    def start(self) -> None:
        """Mark start of timed block."""
        self._start_ns = time.perf_counter_ns()

    def stop(self) -> float:
        """Mark end of timed block and record duration in microseconds."""
        elapsed_us = (time.perf_counter_ns() - self._start_ns) / 1000.0
        self.durations_us.append(elapsed_us)
        return elapsed_us

    def reset(self) -> None:
        self.durations_us.clear()

    def statistics(self) -> Dict[str, float]:
        """Compute comprehensive latency statistics in microseconds and milliseconds."""
        if not self.durations_us:
            return {"count": 0}

        arr = np.array(self.durations_us)
        return {
            "count": len(arr),
            "mean_ms": float(np.mean(arr) / 1000.0),
            "median_ms": float(np.median(arr) / 1000.0),
            "p95_ms": float(np.percentile(arr, 95) / 1000.0),
            "p99_ms": float(np.percentile(arr, 99) / 1000.0),
            "min_ms": float(np.min(arr) / 1000.0),
            "max_ms": float(np.max(arr) / 1000.0),
            "mean_us": float(np.mean(arr)),
            "median_us": float(np.median(arr)),
            "p95_us": float(np.percentile(arr, 95)),
            "p99_us": float(np.percentile(arr, 99)),
        }


class EnergyEstimator:
    """Estimates neuromorphic synaptic operations (SynOps) and equivalent energy consumption.

    Neuromorphic metrics:
    - Typical neuromorphic chip energy per synaptic event: ~1-10 pJ (e.g., Intel Loihi ~20 pJ).
    - Standard edge GPU/CPU floating-point multiply-accumulate (MAC): ~5-20 pJ.
    """

    def __init__(self, pJ_per_synop: float = 15.0, pJ_per_neuron_update: float = 5.0):
        self.pJ_per_synop = pJ_per_synop
        self.pJ_per_neuron = pJ_per_neuron_update
        self.total_spikes: int = 0
        self.total_synops: int = 0
        self.total_steps: int = 0

    def record_step(self, active_spikes: int, active_synapses: int, total_neurons: int) -> None:
        self.total_steps += 1
        self.total_spikes += active_spikes
        self.total_synops += active_synapses

    def summary(self) -> Dict[str, Any]:
        """Compute accumulated energy and power estimates."""
        if self.total_steps == 0:
            return {}

        total_energy_pJ = (self.total_synops * self.pJ_per_synop) + (
            self.total_steps * self.pJ_per_neuron
        )
        total_energy_uJ = total_energy_pJ / 1e6
        avg_synops_per_step = self.total_synops / self.total_steps
        avg_spikes_per_step = self.total_spikes / self.total_steps

        return {
            "total_steps": self.total_steps,
            "total_spikes": self.total_spikes,
            "total_synops": self.total_synops,
            "avg_spikes_per_step": avg_spikes_per_step,
            "avg_synops_per_step": avg_synops_per_step,
            "total_energy_microjoules": total_energy_uJ,
            "estimated_power_mW_at_1kHz": (total_energy_pJ * 1000.0) / 1e9,
        }
