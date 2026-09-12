"""Phase 1 MVP: End-to-End Looming Stimulus to Giant Fiber Escape Reflex.

Demonstrates:
1. Synthetic expanding looming stimulus (time-to-collision dynamics).
2. LC4 OFF-pathway population activation.
3. Giant Fiber (GF / DNp01) all-or-none action potential emission.
4. Instantaneous Jump reflex actuation prior to collision.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
import torch

from circuits.looming import LoomingEscapeCircuit, generate_synthetic_looming_stimulus
from telemetry.profiler import LatencyProfiler, EnergyEstimator
from telemetry.visualizer import plot_looming_trajectory, print_ascii_raster


def run_mvp(output_plot: str = "looming_trajectory.png") -> None:
    print("=" * 70)
    print("FlyRun Phase 1 MVP: Biological Looming Reflex Pipeline")
    print("=" * 70)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Hardware Compute Device: {device.upper()}")

    grid_size = 48
    num_lc4 = 256
    num_steps = 150
    t_collision = 120
    r_over_v = 35.0

    print(f"Vision Grid: {grid_size}x{grid_size} ommatidia ({grid_size * grid_size} photoreceptors)")
    print(f"Looming Population: {num_lc4} LC4 Columnar Units -> 2 Giant Fiber Neurons (GF_L, GF_R)")
    print(f"Collision Projected at Step {t_collision} ms (r/v = {r_over_v} ms)")
    print("-" * 70)

    # 1. Initialize Circuit
    circuit = LoomingEscapeCircuit(
        grid_height=grid_size,
        grid_width=grid_size,
        num_lc4=num_lc4,
        dt_ms=1.0,
        device=device,
    )
    circuit.reset()

    # 2. Generate Synthetic Looming Stimulus Sequence
    print("Generating synthetic expanding looming disk stimulus...")
    stimulus = generate_synthetic_looming_stimulus(
        grid_height=grid_size,
        grid_width=grid_size,
        num_steps=num_steps,
        r_over_v=r_over_v,
        t_collision=t_collision,
    ).to(device)

    # 3. Telemetry and Profiling Setup
    profiler = LatencyProfiler("LoomingCircuit_Step")
    energy = EnergyEstimator()

    timestamps_ms = []
    lc4_spike_counts = []
    gf_voltages = []
    gf_spikes_list = []
    jump_triggered_step = None

    print("\nExecuting 1 kHz simulation loop (1 ms steps)...")
    for t in range(num_steps):
        frame = stimulus[t]

        profiler.start()
        gf_spikes, lc4_spikes, telemetry = circuit.process_frame(frame)
        step_us = profiler.stop()

        active_spikes = int(lc4_spikes.sum().item() + gf_spikes.sum().item())
        active_syn = int(lc4_spikes.sum().item()) * 2
        energy.record_step(active_spikes, active_syn, num_lc4 + 2)

        timestamps_ms.append(float(t))
        lc4_spike_counts.append(telemetry["lc4_spikes_count"])
        gf_voltages.append(telemetry["gf_v"])
        gf_spikes_list.append(telemetry["gf_spikes"])

        if telemetry["jump_command"] and jump_triggered_step is None:
            jump_triggered_step = t
            time_to_collision = t_collision - t
            print(f">>> [EMERGENCY JUMP TRIGGERED] at t = {t} ms (Time-to-Collision: {time_to_collision} ms, Step latency: {step_us:.2f} us)")

    print("-" * 70)
    print("Execution Finished!")

    # 4. Results & Latency Stats
    stats = profiler.statistics()
    print(f"\n--- Latency Performance (Target: < 1.0 ms) ---")
    print(f"Mean Latency:    {stats['mean_us']:.2f} us ({stats['mean_ms']:.4f} ms)")
    print(f"Median Latency:  {stats['median_us']:.2f} us ({stats['median_ms']:.4f} ms)")
    print(f"P95 Latency:     {stats['p95_us']:.2f} us ({stats['p95_ms']:.4f} ms)")
    print(f"P99 Latency:     {stats['p99_us']:.2f} us ({stats['p99_ms']:.4f} ms)")
    print(f"Min / Max:       {stats['min_ms']:.4f} ms / {stats['max_ms']:.4f} ms")

    en_stats = energy.summary()
    print(f"\n--- Neuromorphic Energy & SynOps Estimation ---")
    print(f"Total Spikes Emitted:      {en_stats['total_spikes']}")
    print(f"Total Synaptic Operations: {en_stats['total_synops']}")
    print(f"Avg SynOps per Step:       {en_stats['avg_synops_per_step']:.2f}")
    print(f"Estimated Dynamic Power:   {en_stats['estimated_power_mW_at_1kHz']:.4f} mW (at 1 kHz)")

    print(f"\n--- Escape Behavior Validation ---")
    if jump_triggered_step is not None:
        ttc = t_collision - jump_triggered_step
        print(f"SUCCESS: Escape takeoff fired {ttc} ms BEFORE predicted physical collision.")
        print(f"Biological fly take-off reflex window: 15-45 ms prior to collision.")
    else:
        print("FAILURE: Escape reflex was not triggered.")
        sys.exit(1)

    # 5. Render Trajectory Artifact
    plot_looming_trajectory(
        timestamps_ms,
        lc4_spike_counts,
        gf_voltages,
        gf_spikes_list,
        save_path=output_plot,
    )
    print("=" * 70)


if __name__ == "__main__":
    run_mvp()
