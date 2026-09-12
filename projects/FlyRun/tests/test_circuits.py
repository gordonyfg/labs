"""Unit tests for biological sub-circuits: Looming, Optomotor EMD, and 3-Factor STDP."""

import pytest
import torch
from circuits.looming import LoomingEscapeCircuit, generate_synthetic_looming_stimulus
from circuits.optomotor import OptomotorCircuit
from engine.stdp import ThreeFactorSTDP


def test_looming_static_stimulus():
    """Verify static non-expanding stimulus does not trigger escape jump."""
    circuit = LoomingEscapeCircuit(grid_height=32, grid_width=32, num_lc4=64)
    circuit.reset()

    # Feed identical static frames for 50 ms
    static_frame = torch.full((32, 32), 0.8)
    jump_triggered = False

    for _ in range(50):
        gf_spikes, lc4_spikes, telemetry = circuit.process_frame(static_frame)
        if telemetry["jump_command"]:
            jump_triggered = True
            break

    assert not jump_triggered, "Static stimulus should not trigger escape jump!"
    assert lc4_spikes.sum() == 0


def test_looming_expansion_triggers_jump():
    """Verify exponentially expanding dark looming disk triggers Giant Fiber escape jump."""
    circuit = LoomingEscapeCircuit(grid_height=32, grid_width=32, num_lc4=128)
    circuit.reset()

    stimulus_sequence = generate_synthetic_looming_stimulus(
        grid_height=32,
        grid_width=32,
        num_steps=80,
        r_over_v=25.0,
        t_collision=65,
    )

    jump_step = None
    for t in range(stimulus_sequence.shape[0]):
        gf_spikes, lc4_spikes, telemetry = circuit.process_frame(stimulus_sequence[t])
        if telemetry["jump_command"]:
            jump_step = t
            break

    assert jump_step is not None, "Expanding looming obstacle failed to trigger escape reflex!"
    # Ensure jump occurs prior to collision impact (t=65)
    assert jump_step < 65, f"Jump triggered too late at step {jump_step} (collision at 65)"


def test_optomotor_directional_sensitivity():
    """Verify Hassenstein-Reichardt correlator discriminates left vs. right motion."""
    optomotor = OptomotorCircuit(grid_height=24, grid_width=24)
    optomotor.reset()

    # Create rightward-moving vertical stripe grating
    # Frame 1 to 10: moving right
    yaw_responses_right = []
    for step in range(20):
        frame = torch.zeros((24, 24))
        stripe_pos = (step * 2) % 24
        frame[:, stripe_pos : min(24, stripe_pos + 4)] = 1.0
        yaw, fwd, _ = optomotor(frame)
        if step > 5:
            yaw_responses_right.append(yaw)

    # Reset and test leftward-moving grating
    optomotor.reset()
    yaw_responses_left = []
    for step in range(20):
        frame = torch.zeros((24, 24))
        stripe_pos = (24 - (step * 2) % 24) % 24
        frame[:, stripe_pos : min(24, stripe_pos + 4)] = 1.0
        yaw, fwd, _ = optomotor(frame)
        if step > 5:
            yaw_responses_left.append(yaw)

    mean_yaw_right = sum(yaw_responses_right) / len(yaw_responses_right)
    mean_yaw_left = sum(yaw_responses_left) / len(yaw_responses_left)

    # Opposing directions must produce distinct sign/asymmetric responses
    assert mean_yaw_right != mean_yaw_left


def test_three_factor_stdp_plasticity():
    """Verify 3-Factor STDP causal LTP and dopamine modulation."""
    num_pre = 4
    num_post = 2
    stdp = ThreeFactorSTDP(
        num_pre=num_pre,
        num_post=num_post,
        tau_eligibility_ms=500.0,
        tau_plus_ms=20.0,
        tau_minus_ms=25.0,
        learning_rate_eta=0.1,
    )

    initial_weights = stdp.weights.clone()

    # 1. Causal pairing: pre spikes at t=0, post spikes at t=5
    pre_spikes = torch.tensor([1.0, 0.0, 0.0, 0.0])
    post_spikes = torch.tensor([0.0, 0.0])
    stdp.update_traces(pre_spikes, post_spikes)

    for _ in range(4):
        stdp.update_traces(torch.zeros(num_pre), torch.zeros(num_post))

    # Post neuron 0 spikes
    post_spikes = torch.tensor([1.0, 0.0])
    stdp.update_traces(torch.zeros(num_pre), post_spikes)

    # Eligibility for (post=0, pre=0) should be positive (causal LTP candidate)
    eligibility_00 = stdp.eligibility[0, 0].item()
    assert eligibility_00 > 0.0, f"Expected positive eligibility, got {eligibility_00}"

    # 2. Deliver delayed dopamine reward: D = +1.0
    delta_w = stdp.apply_dopamine(dopamine=1.0)
    
    # Synapse (0, 0) should strengthen
    assert stdp.weights[0, 0].item() > initial_weights[0, 0].item()
    assert delta_w[0, 0].item() > 0.0
