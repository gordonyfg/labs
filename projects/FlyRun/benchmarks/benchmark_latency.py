"""High-throughput latency benchmarking for FlyRun Neuromorphic Engine.

Measures isolated kernels; this does not measure end-to-end gameplay latency.
"""

from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path
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
        "num_synapses": w_sparse._nnz(),
        "steps": num_steps,
        "mean_ms": float(np.mean(arr) / 1000.0),
        "median_ms": float(np.median(arr) / 1000.0),
        "p95_ms": float(np.percentile(arr, 95) / 1000.0),
        "p99_ms": float(np.percentile(arr, 99) / 1000.0),
        "min_ms": float(np.min(arr) / 1000.0),
        "max_ms": float(np.max(arr) / 1000.0),
        "deadline_ms": 1.0,
        "deadline_misses": int(np.count_nonzero(arr >= 1000.0)),
        "deadline_miss_rate": float(np.mean(arr >= 1000.0)),
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
        "deadline_ms": 1.0,
        "deadline_misses": int(np.count_nonzero(arr >= 1000.0)),
        "deadline_miss_rate": float(np.mean(arr >= 1000.0)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--require-deadline", action="store_true",
                        help="Exit unsuccessfully if ANY measured step reaches 1 ms")
    args = parser.parse_args()
    if args.steps <= 0 or args.threads <= 0:
        parser.error("steps and threads must be positive")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    results = [benchmark_looming_circuit(args.steps, args.device),
               benchmark_snn_sparse_step(num_steps=args.steps, device_str=args.device)]
    print(json.dumps({
        "scope": "Isolated Python kernels; excludes browser, rendering, transport and actuation",
        "platform": platform.platform(), "processor": platform.processor(),
        "cpu_model": next((line.split(":", 1)[1].strip() for line in
                           Path("/proc/cpuinfo").read_text().splitlines()
                           if line.startswith("model name")), platform.processor())
                     if Path("/proc/cpuinfo").exists() else platform.processor(),
        "torch": torch.__version__, "threads": torch.get_num_threads(),
        "seed": args.seed,
        "device_name": torch.cuda.get_device_name() if args.device == "cuda" else platform.machine(),
        "results": results,
    }, indent=2))
    if args.require_deadline and any(r["deadline_misses"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
