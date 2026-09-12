"""Visual telemetry and spike raster plotting utilities."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless rendering
import matplotlib.pyplot as plt


def plot_looming_trajectory(
    timestamps_ms: List[float],
    lc4_spike_counts: List[int],
    gf_voltages: List[List[float]],
    gf_spikes: List[List[int]],
    save_path: Optional[str] = "looming_trajectory.png",
) -> None:
    """Generate high-resolution publication-quality figure of LC4 -> GF looming reflex."""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    t = np.array(timestamps_ms)

    # 1. LC4 Population Activity
    ax1.plot(t, lc4_spike_counts, color="tab:blue", lw=1.5, label="Active LC4 Units")
    ax1.set_ylabel("LC4 Spikes / ms", fontsize=11)
    ax1.set_title("Biological Looming Circuit Dynamics (LC4 -> Giant Fiber)", fontsize=13, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left")

    # 2. Giant Fiber Membrane Potential
    gf_v_arr = np.array(gf_voltages)
    ax2.plot(t, gf_v_arr[:, 0], color="tab:purple", lw=1.8, label="GF_L Membrane (V)")
    ax2.plot(t, gf_v_arr[:, 1], color="tab:cyan", lw=1.5, linestyle="--", label="GF_R Membrane (V)")
    ax2.axhline(1.8, color="red", linestyle=":", lw=1.2, label="Firing Threshold")
    ax2.set_ylabel("Potential (mV)", fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left")

    # 3. Giant Fiber Spikes / Reflex Actuation
    gf_s_arr = np.array(gf_spikes)
    jump_events = np.where((gf_s_arr[:, 0] > 0) | (gf_s_arr[:, 1] > 0))[0]
    
    ax3.step(t, gf_s_arr[:, 0], color="crimson", lw=1.5, label="GF Spike Action Potential")
    for idx in jump_events:
        ax3.axvline(t[idx], color="gold", lw=2, alpha=0.8, linestyle="--", label="Emergency Jump Triggered" if idx == jump_events[0] else "")
    
    ax3.set_ylabel("Motor Spike", fontsize=11)
    ax3.set_xlabel("Time (ms)", fontsize=11)
    ax3.set_ylim(-0.1, 1.2)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left")

    plt.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=200)
        plt.close(fig)
        print(f"Saved trajectory plot to {save_path}")


def print_ascii_raster(spike_matrix: np.ndarray, num_neurons: int = 16, num_steps: int = 60) -> str:
    """Generate compact ASCII spike raster for terminal output."""
    steps = min(spike_matrix.shape[0], num_steps)
    neurons = min(spike_matrix.shape[1], num_neurons)
    lines = []
    lines.append("+" + "-" * steps + "+")
    for n in range(neurons):
        row_str = "".join("|" if spike_matrix[t, n] > 0 else " " for t in range(steps))
        lines.append(f"|{row_str}| N{n:02d}")
    lines.append("+" + "-" * steps + "+")
    return "\n".join(lines)
