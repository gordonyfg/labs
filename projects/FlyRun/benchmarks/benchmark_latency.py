"""High-throughput latency benchmarking for FlyRun Neuromorphic Engine.

Validates that single-step forward pass latency meets the edge inference deadline (< 1.0 ms).
"""

from __future__ import annotations
import time
import numpy as np
import torch

from circuits.looming import LoomingEscapeCircuit
from engine.lif import LIFPopulation, SparseSynapse
from telemetry.profiler import LatencyProfiler


def benchmark_snn_sparse_step(
    num_neurons: int = 5000,
    synapses_per_neuron: int = 40,
    num_steps: int = 5000,
    device_str: str = "cpu",
) -> dict:
    """Benchmark sparse LIF population forward pass step latency."""
    device = torch.device(device_str)
    
    # 1. Build sparse recurrent weight matrix
    # Total synapses E = num_neurons * synapses_per_neuron (~200,000 non-zeros)
    rows = []
    cols = []
    for i in range(num_neurons):
        targets = torch.randint(0, num_neurons, (synapses_per_neuron,))
        for t in targets:
            rows.append(t.item())
            cols.append(i)

    indices = torch.tensor([rows, cols], dtype=torch.long, device=device)
    values = torch.randn(len(rows), dtype=torch.float32, device=device) * 0.01
    w_sparse = torch.sparse_coo_tensor(indices, values, (num_neurons, num_neurons), device=device).coalesce()

    pop = LIFPopulation(num_neurons=num_neurons, dt_ms=1.0, device=device)
    pop.set_recurrent_weights(w_sparse)

    # Pre-generate sparse spike activity (~5% active spikes per step)
    spike_rate = 0.05

    # Warmup
    for _ in range(100):
        i_ext = torch.randn(num_neurons, device=device) * 0.5
        pop(i_ext=i_ext)

    if device.type == "cuda":
        torch.cuda.synchronize()

    # Timed evaluation
    latencies_us = []
    for step in range(num_steps):
        i_ext = torch.randn(num_neurons, device=device) * 0.5

        if device.type == "cuda":
            start_event = torch.cuda.Event(enable_timing=True)
            end_event = torch.cuda.Event(enable_timing=True)
            start_event.record()
            pop(i_ext=i_ext)
            end_event.record()
            torch.cuda.synchronize()
            latencies_us.append(start_event.elapsed_time(end_event) * 1000.0)
        else:
            t0 = time.perf_counter_ns()
            pop(i_ext=i_ext)
            t1 = time.perf_counter_ns()
            latencies_us.append((t1 - t0) / 1000.0)

    arr = np.array(latencies_us)
    return {
        "device": device_str,
        "num_neurons": num_neurons,
        "num_synapses": len(rows),
        "steps": num_steps,
        "mean_ms": float(np.mean(arr) / 1000.0),
        "median_ms": float(np.median(arr) / 1000.0),
        "p95_ms": float(np.percentile(arr, 95) / 1000.0),
        "p99_ms": float(np.percentile(arr, 99) / 1000.0),
        "min_ms": float(np.min(arr) / 1000.0),
        "max_ms": float(np.max(arr) / 1000.0),
    }


def benchmark_looming_circuit(num_steps: int = 5000, device_str: str = "cpu") -> dict:
    """Benchmark full perception-to-spike LoomingEscapeCircuit loop."""
    device = torch.device(device_str)
    circuit = LoomingEscapeCircuit(grid_height=48, grid_width=48, num_lc4=256, device=device_str)

    # Random frames
    frames = [torch.rand((48, 48), device=device) for _ in range(50)]

    # Warmup
    for f in frames:
        circuit.process_frame(f)

    if device.type == "cuda":
        torch.cuda.synchronize()

    latencies_us = []
    for i in range(num_steps):
        f = frames[i % len(frames)]
        t0 = time.perf_counter_ns()
        circuit.process_frame(f)
        if device.type == "cuda":
            torch.cuda.synchronize()
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)

    arr = np.array(latencies_us)
    return {
        "device": device_str,
        "circuit": "LoomingEscapeCircuit (48x48 vision + 256 LC4 + 2 GF)",
        "steps": num_steps,
        "mean_ms": float(np.mean(arr) / 1000.0),
        "median_ms": float(np.median(arr) / 1000.0),
        "p95_ms": float(np.percentile(arr, 95) / 1000.0),
        "p99_ms": float(np.percentile(arr, 99) / 1000.0),
        "min_ms": float(np.min(arr) / 1000.0),
        "max_ms": float(np.max(arr) / 1000.0),
    }


def main():
    print("=" * 75)
    print("FlyRun Neuromorphic Engine - Latency Benchmark Suite")
    print("=" * 75)

    devices = ["cpu"]
    if torch.cuda.is_available():
        devices.append("cuda")

    for dev in devices:
        print(f"\nEvaluating on Device: {dev.upper()}")
        print("-" * 50)
        
        print("1. Benchmarking Looming Perception-to-Reflex Circuit (5,000 steps)...")
        res_circuit = benchmark_looming_circuit(num_steps=5000, device_str=dev)
        print(f"   Median: {res_circuit['median_ms']:.4f} ms ({res_circuit['median_ms']*1000:.1f} us)")
        print(f"   P95:    {res_circuit['p95_ms']:.4f} ms")
        print(f"   P99:    {res_circuit['p99_ms']:.4f} ms")
        print(f"   Max:    {res_circuit['max_ms']:.4f} ms")
        assert res_circuit['median_ms'] < 1.0, f"Failed < 1.0 ms deadline on {dev}!"

        print("\n2. Benchmarking Large SNN Graph (5,000 Neurons, 200,000 Synapses, 5,000 steps)...")
        res_sparse = benchmark_snn_sparse_step(num_neurons=5000, synapses_per_neuron=40, num_steps=5000, device_str=dev)
        print(f"   Median: {res_sparse['median_ms']:.4f} ms ({res_sparse['median_ms']*1000:.1f} us)")
        print(f"   P95:    {res_sparse['p95_ms']:.4f} ms")
        print(f"   P99:    {res_sparse['p99_ms']:.4f} ms")
        assert res_sparse['median_ms'] < 1.0, f"Sparse SNN failed < 1.0 ms deadline on {dev}!"

    print("\n" + "=" * 75)
    print("ALL LATENCY BENCHMARKS PASSED: Sub-millisecond (< 1.0 ms) target satisfied.")
    print("=" * 75)


if __name__ == "__main__":
    main()
