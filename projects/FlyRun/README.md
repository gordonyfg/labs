# Project FlyRun: Biological Reflex Architecture for Autonomous Navigation

An event-driven, neuromorphic perception-and-control stack for high-speed 3D corridor navigation derived directly from the *Drosophila melanogaster* connectome (MaleCNS v1.0 / FlyWire / Hemibrain).

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Latency](https://img.shields.io/badge/latency-%3C1.0ms-blue)](benchmarks/)
[![Backend](https://img.shields.io/badge/PyTorch-sparse__csr-red)](engine/)

---

## Key Features

1. **Biological Drosophila Sub-Circuits**:
   - **Looming Collision Reflex (`circuits/looming.py`)**: Lobula Columnar (LC4, LPLC2) neurons projecting onto descending Giant Fiber (GF / DNp01) motor neurons for emergency takeoff (jump/slide).
   - **Directional Optomotor Stabilization (`circuits/optomotor.py`)**: Hassenstein-Reichardt Elementary Motion Detectors (EMDs, T4/T5) feeding into Lobula Plate Horizontal (HS) and Vertical (VS) tangential cells for yaw balance and lane centering.
   - **Contextual Adaptation (`circuits/mushroom_body.py`)**: Kenyon Cell sparse population coding ($< 5\%$ sparsity via APL feedback) and Mushroom Body Output Neurons (MBONs) modulated by Dopaminergic Neurons (PPL1/PAM) using **3-Factor STDP** with synaptic eligibility traces.
2. **Neuromorphic Spiking Engine (`engine/`)**:
   - Vectorized Leaky Integrate-and-Fire (LIF) dynamics with exact exponential decay at 1 kHz ($\Delta t = 1.0\text{ ms}$).
   - Memory-efficient `torch.sparse_csr_tensor` graph propagation with $\mathcal{O}(E)$ complexity.
   - Zero-copy circular ring buffers for spike histories and continuous traces (`engine/buffers.py`).
3. **Connectome Data Pipeline (`data/`)**:
   - Dual-mode extraction: Automated Cypher query generation for NeuPrint API (`neuprint-python`) and validated offline compressed Parquet caches with neurotransmitter polarity mapping ($\text{ACh} > 0$, $\text{GABA/Glut} < 0$).
4. **Sub-Millisecond Edge Performance (`benchmarks/`)**:
   - Single-step inference latency: **~0.70 ms median** on standard CPU, beating the $< 1.0\text{ ms}$ edge latency deadline.
   - Neuromorphic energy profiling: Tracks Synaptic Operations (SynOps), spike counts, and estimated dynamic power consumption (~0.03 mW at 1 kHz).

---

## Directory Structure

```
FlyRun/
├── ARCHITECTURE.md            # Deep mathematical and theoretical specification
├── configs/
│   └── circuits.yaml          # Biophysical parameters (tau, v_thresh, STDP)
├── data/
│   ├── artifacts/             # Parquet-serialized connectome subgraphs
│   ├── neuprint_client.py     # NeuPrint API Cypher query interface
│   ├── export_subgraphs.py    # Subgraph extraction CLI
│   └── synthetic_subgraphs.py # Biological ground-truth topology generator
├── engine/
│   ├── lif.py                 # Vectorized sparse PyTorch LIF simulation backend
│   ├── buffers.py             # Zero-allocation circular spike ring buffers
│   └── stdp.py                # 3-Factor STDP with synaptic eligibility traces
├── circuits/
│   ├── looming.py             # LC4/LPLC2 -> Giant Fiber collision reflex
│   ├── optomotor.py           # T4/T5 EMD -> Lobula Plate HS/VS heading circuit
│   └── mushroom_body.py       # Kenyon Cells -> MBONs with dopamine modulation
├── sim/
│   ├── corridor.py            # Procedural 3D corridor runner environment
│   └── eye.py                 # 48x48 compound eye ommatidia optical model
├── telemetry/
│   ├── profiler.py            # Microsecond timer and SynOps / energy estimator
│   └── visualizer.py          # Spike raster and membrane potential plotter
├── tests/
│   ├── test_lif.py            # Unit tests for LIF dynamics & ring buffers
│   └── test_circuits.py       # Deterministic validation for biological circuits
├── scripts/
│   └── run_mvp_looming.py     # Phase 1 MVP end-to-end runnable demonstration
└── benchmarks/
    └── benchmark_latency.py   # Latency benchmarks against < 1.0 ms deadline
```

---

## Quick Start

### 1. Installation

```bash
# Create virtual environment with uv
uv venv --python 3.12 .venv
source .venv/bin/activate

# Install dependencies and editable package
uv pip install -e .
```

### 2. Launch Interactive 3D Temple Runner Web Simulation & Connectome HUD

FlyRun includes a full 3D browser-based corridor navigation game wired in real time to the biological connectome:

```bash
# Start the HTTP server (port 8080) and WebSocket SNN bridge (port 8765)
python3 scripts/run_game_bridge.py
```
Open **`http://localhost:8080`** in any modern web browser.
- **Auto-Pilot Mode**: Click `🪰 Fly Brain Mode` to let the 24-PN / 128-KC / 4-MBON network navigate autonomously.
- **Manual Mode**: Control with Arrow keys / WASD (Up = Jump, Down = Slide, Left/Right = Steer).
- **Live Connectome HUD**: Real-time 3D brain point cloud, 48x48 compound eye ommatidia visualization, 9/128 KC sparsity readout, and 3-factor STDP weight convergence curve.
- **10 Hz Flight Data Recorder (Black Box)**: Click `✈ Black Box` to inspect incident forensics, kinematics, and synaptic valences.

### 3. Run Phase 1 MVP (Looming Stimulus to Giant Fiber Reflex)

```bash
python3 scripts/run_mvp_looming.py
```
Outputs trajectory telemetry and generates `looming_trajectory.png`.

### 4. Run Latency Benchmarks

```bash
python3 benchmarks/benchmark_latency.py
```

### 5. Run Unit Test Suite

```bash
pytest tests/ -v
```

### 6. Export Connectome Subgraphs

To query live Janelia NeuPrint servers (requires authentication token):
```bash
export NEUPRINT_APPLICATION_CREDENTIALS="<YOUR_TOKEN>"
python3 data/export_subgraphs.py --dataset hemibrain:v1.2.1
```
Or generate high-fidelity offline Parquet caches:
```bash
python3 data/export_subgraphs.py --force-synthetic
```

---

## High-Dimensional Connectome Model (24 PNs & 128 KCs)

- **24-Channel Sensory Receptor Array (Projection Neurons)**:
  - $PN_{0..8}$: Obstacle identity & geometry (Hurdle, Arch, Monolith across 3 lanes within 38m).
  - $PN_{9..11}$: Downstream secondary hazard depth (20m to 55m).
  - $PN_{12..15}$: Haltere gyroscopic lateral velocity & jumping/sliding mechanoreceptors.
  - $PN_{16..20}$: Lobula LC4 Looming optical expansion rate & T4/T5 optomotor horizontal flow.
  - $PN_{21..23}$: Spatial position one-hot (Lane 0, 1, 2).
- **128 Kenyon Cells & APL Feedback Inhibition**:
  - Calyx divergence ($K=5$ random PNs per KC) and Anterior Paired Lateral (APL) GABAergic feedback inhibition enforcing ~7% sparse coding (9 / 128 active KCs).
- **4 Motor Output Neurons (MBONs) & 512 Plastic Synapses**:
  - $4 \times 128$ synaptic weight matrix with 3-factor STDP modulated by $+0.75$ PAM (clearance) and $-1.4$ PPL1 (collision) dopamine bursts.

---

## Theoretical Architecture

For complete mathematical derivations, LaTeX formulas for LIF/EMD/STDP, latency budget tables, and Drosophila-to-robotics mapping, refer to [ARCHITECTURE.md](ARCHITECTURE.md).
