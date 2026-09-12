"""Unit tests for Leaky Integrate-and-Fire (LIF) dynamics and ring buffers."""

import math
import pytest
import torch
from engine.lif import LIFPopulation, SparseSynapse
from engine.buffers import SpikeRingBuffer, StateTraceBuffer


def test_lif_exponential_decay():
    """Verify subthreshold potential decays exponentially according to tau_m."""
    tau_m = 20.0
    dt = 1.0
    expected_alpha = math.exp(-dt / tau_m)

    pop = LIFPopulation(num_neurons=4, dt_ms=dt, tau_m=tau_m, v_thresh=10.0, v_reset=0.0)
    # Set initial voltage
    pop.v.fill_(5.0)

    # Step without input
    spikes, v = pop(i_ext=None)
    assert spikes.sum() == 0
    assert torch.allclose(v, torch.full((4,), 5.0 * expected_alpha), atol=1e-5)


def test_lif_spike_and_reset():
    """Verify threshold crossing generates spike and resets to v_reset."""
    pop = LIFPopulation(num_neurons=2, dt_ms=1.0, tau_m=10.0, v_thresh=1.0, v_reset=-0.5)

    # Inject current above threshold
    i_strong = torch.tensor([2.0, 0.2])
    spikes, v = pop(i_ext=i_strong)

    # Neuron 0 should fire and reset
    assert spikes[0].item() == 1.0
    assert v[0].item() == -0.5

    # Neuron 1 should not fire
    assert spikes[1].item() == 0.0
    assert v[1].item() > 0.0


def test_lif_refractory_period():
    """Verify refractory counter clamps voltage and prevents firing."""
    pop = LIFPopulation(num_neurons=1, dt_ms=1.0, tau_m=10.0, v_thresh=1.0, v_reset=0.0, tau_ref_ms=3.0)

    # Step 1: Force a spike
    pop(i_ext=torch.tensor([2.0]))
    assert pop.ref_counter[0].item() == 3

    # Step 2: Inject large current while in refractory period
    spikes, v = pop(i_ext=torch.tensor([10.0]))
    assert spikes[0].item() == 0.0
    assert v[0].item() == 0.0  # Clamped at v_reset
    assert pop.ref_counter[0].item() == 2

    # Step 3: Still in refractory
    spikes, _ = pop(i_ext=torch.tensor([10.0]))
    assert spikes[0].item() == 0.0
    assert pop.ref_counter[0].item() == 1

    # Step 4: Final refractory step
    spikes, _ = pop(i_ext=torch.tensor([10.0]))
    assert spikes[0].item() == 0.0
    assert pop.ref_counter[0].item() == 0

    # Step 5: Now out of refractory, should fire
    spikes, _ = pop(i_ext=torch.tensor([10.0]))
    assert spikes[0].item() == 1.0


def test_sparse_synapse():
    """Verify sparse matrix multiplication produces equivalent results to dense."""
    num_pre = 10
    num_post = 4
    
    # Dense random matrix
    dense_w = torch.randn((num_post, num_pre))
    dense_w[dense_w.abs() < 0.5] = 0.0  # Make sparse
    sparse_w = dense_w.to_sparse_coo()

    syn = SparseSynapse(num_pre, num_post, sparse_w)

    pre_spikes = torch.tensor([1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0])
    out_sparse = syn(pre_spikes)
    out_dense = torch.matmul(dense_w, pre_spikes)

    assert torch.allclose(out_sparse, out_dense, atol=1e-5)


def test_spike_ring_buffer():
    """Verify circular ring buffer FIFO ordering and window retrieval."""
    buf = SpikeRingBuffer(capacity=5, num_units=2)

    # Push 3 vectors
    buf.push(torch.tensor([1.0, 0.0]))
    buf.push(torch.tensor([0.0, 1.0]))
    buf.push(torch.tensor([1.0, 1.0]))

    assert torch.allclose(buf.latest(), torch.tensor([1.0, 1.0]))

    win = buf.window(2)
    expected = torch.tensor([[0.0, 1.0], [1.0, 1.0]])
    assert torch.allclose(win, expected)

    # Overflow capacity
    buf.push(torch.tensor([0.0, 0.0]))
    buf.push(torch.tensor([1.0, 0.0]))
    buf.push(torch.tensor([0.0, 1.0]))  # Wraps around

    win5 = buf.window(5)
    assert win5.shape == (5, 2)
    assert torch.allclose(buf.latest(), torch.tensor([0.0, 1.0]))
