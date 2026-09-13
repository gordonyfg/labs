# FlyRun architecture and model assumptions

## Execution paths

The browser and Python experiments are independent. Neither consumes the exported
Parquet tables. The browser sends incident logs, not sensor streams, to Python.

```text
Browser game objects → exact sensory features → sparse continuous KC-like code
                                              → learned action preferences
Game geometry → avoidance rules ──────────────→ action arbitration → physics
                                      incidents → optional Python file logger

Separate experiments: synthetic frames → contrast / EMD → Python LIF circuits
Separate data utility: NeuPrint OR explicit synthetic generation → Parquet + manifest
```

## Browser controller

Inputs include obstacle identity, exact lane/distance and player state. The 48×48
eye illustration is not an input. Five randomly chosen inputs feed each of 128
units; a deterministic top-k operation activates at most nine (7.03%). These are
continuous values, not spikes. Four weighted readouts bias hand-written steering,
jump and slide rules. The brain point cloud and neural labels are illustrative.

Eligibility decays according to `e ← e exp(-dt / 1 second)`. Only an action
accepted by the dispatcher adds `0.35 × KC activity` to its row. Rewards apply
`W ← clip(W + 0.08 × reward × e, 0.02, 1.95)`. This is reward-modulated associative
learning, not STDP. Switching modes or restarting clears transient eligibility;
weights persist across normal episodes. Frozen-learning and fresh seeded runs
are available for evaluation. Obstacles that were collided with receive no
clearance reward. Rewards remain a simplified global signal, not a proven credit
assignment solution.

A control step runs once per animation frame. Trace decay uses the same capped
simulation time increment as physics; time discarded after a long stall does not
advance the model. This removes frame-count-based decay but does not establish
frame-rate-invariant trajectories. Lateral-transition protection considers the
player's swept horizontal segment and prioritizes the nearest collision face.
It is a heuristic, not a complete trajectory planner or safety guarantee.

## Python LIF model

With `alpha = exp(-dt / tau_m)`, the implemented update is:

```text
V_candidate = V_rest + alpha (V - V_rest) + synaptic_input + external_input
spike = (V_candidate >= threshold) and not refractory
V = V_reset on a spike or while refractory
```

Decay is exact for the passive leak. Inputs are per-step voltage increments;
this is not exact integration of a constant physical current. For a physical
current, the corresponding voltage term would include `R (1-alpha) I`.
Recurrent synapses use the previous step's spikes. Feedforward circuit calls can
propagate spikes between populations within one model step; this is a numerical
convention, not a measured conduction delay.

The KC circuit combines feedback inhibition with a top-k cap of
`floor(num_kc × target_sparsity)` spikes per step, including tied inputs.
The cap is an explicit engineering approximation. Python KC→MBON weights use
pre/post spike traces, eligibility decay and dopamine modulation from
`engine/stdp.py`. These experiments are not the browser's learning implementation.

## Contrast and motion experiments

The escape model computes `max(previous-current - median(previous-current), 0)`
and pools 3×3 patches into LIF units with hand-selected LC4→GF weights. Median
subtraction rejects additive global illumination shifts. The model does not
implement a separate LPLC2 radial-motion population or validate expansion
selectivity; translation and spatial lighting changes can still excite it.

The optomotor experiment uses an antisymmetric Hassenstein–Reichardt correlator:
`delayed(A) × B - A × delayed(B)`, on ON/OFF temporal contrast. Horizontal
hemifield flow produces a steering value. HS LIF activity is telemetry; steering
is decoded directly from flow. Vertical EMD/VS processing is not implemented.

## Data and biology

Neuron names provide inspiration, not proof of functional or anatomical fidelity.
The synthetic graph distributions, IDs and weights are model choices. Live exports
retain measured counts but map neurotransmitters to assumed signs and scale
counts into effective weights. This does not identify biological conductances,
receptor-specific effects, compartment dynamics or valid robotic actions.
Unknown polarity is rejected. Export errors do not trigger synthetic fallback.
Manifests record provenance and hashes; legacy bundled files are unverified.

## Memory, latency and energy

Ring-buffer insertion copies a vector into preallocated storage. `latest()` is a
view; `window()` returns an allocating chronological copy of available history.
CSR graph propagation costs O(stored edges) plus population work; it is not a
sparse-event engine proportional only to fired synapses. Tensor intermediates
allocate memory and GPU scalar reads may synchronize execution.

Benchmarks measure isolated Python calls, publish distribution tails and count
misses of a 1 ms target. They exclude browser waiting, rendering, transport and
actuation. No measured CPU/GPU end-to-end comparison or guaranteed deadline is
claimed. Browser compute time is sampled independently in the HUD.

For operation energies in pJ and a 1 ms model step:

```text
E_total = SynOps_total × pJ_per_synop + neuron_updates_total × pJ_per_neuron
P_model_mW = (E_total / steps) × 1000 / 1e9
```

This hypothetical model is not measured hardware power, and limited event counts
must not be presented as full-system energy. Neuromorphic hardware efficiency
cannot be inferred from running a PyTorch simulation on a conventional CPU.
