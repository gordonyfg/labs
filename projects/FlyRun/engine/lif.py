"""High-performance vectorized Leaky Integrate-and-Fire (LIF) simulation backend.

Utilizes torch.sparse for memory-efficient and low-latency graph propagation.
"""

from __future__ import annotations
import math
import torch
import torch.nn as nn
from typing import Optional, Union, Tuple


class LIFPopulation(nn.Module):
    """Vectorized Leaky Integrate-and-Fire neuron population.

    Implements discrete-time exact exponential integration:
        V[t] = V[t-1] * exp(-dt / tau_m) + W_sparse @ S[t-1] + I_ext[t]
        S[t] = 1 if V[t] >= V_thresh and ref_count == 0 else 0
        V[t] = V_reset if S[t] == 1
    """

    def __init__(
        self,
        num_neurons: int,
        dt_ms: float = 1.0,
        tau_m: Union[float, torch.Tensor] = 10.0,
        v_thresh: Union[float, torch.Tensor] = 1.0,
        v_reset: Union[float, torch.Tensor] = 0.0,
        v_rest: Union[float, torch.Tensor] = 0.0,
        tau_ref_ms: Union[float, torch.Tensor] = 2.0,
        device: Union[torch.device, str] = "cpu",
        dtype: torch.dtype = torch.float32,
    ):
        super().__init__()
        self.num_neurons = num_neurons
        self.dt_ms = dt_ms
        self.device = torch.device(device)
        self.dtype = dtype

        # Biophysical parameters (scalar or per-neuron vector)
        if isinstance(tau_m, (int, float)):
            self.tau_m = torch.full((num_neurons,), float(tau_m), dtype=dtype, device=self.device)
        else:
            self.tau_m = tau_m.to(device=self.device, dtype=dtype)

        if isinstance(v_thresh, (int, float)):
            self.v_thresh = torch.full((num_neurons,), float(v_thresh), dtype=dtype, device=self.device)
        else:
            self.v_thresh = v_thresh.to(device=self.device, dtype=dtype)

        if isinstance(v_reset, (int, float)):
            self.v_reset = torch.full((num_neurons,), float(v_reset), dtype=dtype, device=self.device)
        else:
            self.v_reset = v_reset.to(device=self.device, dtype=dtype)

        if isinstance(v_rest, (int, float)):
            self.v_rest = torch.full((num_neurons,), float(v_rest), dtype=dtype, device=self.device)
        else:
            self.v_rest = v_rest.to(device=self.device, dtype=dtype)

        # Precompute exponential decay factor: alpha = exp(-dt / tau_m)
        self.alpha = torch.exp(-self.dt_ms / self.tau_m)

        # Refractory period in integer simulation steps
        if isinstance(tau_ref_ms, (int, float)):
            self.ref_steps = torch.full(
                (num_neurons,), int(round(tau_ref_ms / dt_ms)), dtype=torch.int32, device=self.device
            )
        else:
            self.ref_steps = torch.round(tau_ref_ms / dt_ms).to(device=self.device, dtype=torch.int32)

        # Dynamic state buffers
        self.register_buffer("v", torch.zeros(num_neurons, dtype=dtype, device=self.device))
        self.register_buffer("spikes", torch.zeros(num_neurons, dtype=dtype, device=self.device))
        self.register_buffer("ref_counter", torch.zeros(num_neurons, dtype=torch.int32, device=self.device))

        # Synaptic recurrent connectivity (sparse)
        self.has_recurrent_synapses = False
        self.register_buffer("w_recurrent", None, persistent=False)

    def set_recurrent_weights(self, w_sparse: torch.Tensor) -> None:
        """Assign sparse synaptic connectivity matrix W of shape (num_neurons, num_neurons)."""
        w = w_sparse.to(device=self.device, dtype=self.dtype)
        if not w.is_sparse and not w.is_sparse_csr:
            w = w.to_sparse_csr()
        elif w.is_sparse:
            # Convert COO to CSR for fast sparse-dense matrix multiplication
            w = w.to_sparse_csr()
        self.w_recurrent = w
        self.has_recurrent_synapses = True

    def reset_states(self) -> None:
        """Reset membrane potential, spike state, and refractory counters."""
        self.v.copy_(self.v_rest)
        self.spikes.zero_()
        self.ref_counter.zero_()

    def forward(
        self,
        i_ext: Optional[torch.Tensor] = None,
        synaptic_input: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Perform a single discrete-time simulation step (1 ms).

        Args:
            i_ext: External current vector of shape (num_neurons,).
            synaptic_input: External synaptic current vector of shape (num_neurons,).

        Returns:
            Tuple of (spikes, membrane_potential) at time step t.
        """
        # 1. Decrement refractory counter
        dec_ref = torch.clamp(self.ref_counter - 1, min=0)

        # 2. Accumulate synaptic inputs
        i_syn = torch.zeros(self.num_neurons, dtype=self.dtype, device=self.device)
        if self.has_recurrent_synapses and self.spikes.any():
            spikes_col = self.spikes.unsqueeze(1)
            recurrent_current = torch.sparse.mm(self.w_recurrent, spikes_col).squeeze(1)
            i_syn.add_(recurrent_current)

        if synaptic_input is not None:
            if synaptic_input.dim() > 1:
                synaptic_input = synaptic_input.squeeze()
            i_syn.add_(synaptic_input)

        if i_ext is not None:
            if i_ext.dim() > 1:
                i_ext = i_ext.squeeze()
            i_syn.add_(i_ext)

        # 3. Leaky integration with exact exponential decay
        v_decay = (self.v - self.v_rest) * self.alpha + self.v_rest + i_syn
        v_cand = torch.where(self.ref_counter > 0, self.v_reset, v_decay)

        # 4. Spike generation (only non-refractory neurons can fire)
        spike_mask = (v_cand >= self.v_thresh) & (self.ref_counter == 0)
        self.spikes.copy_(spike_mask.to(self.dtype))

        # 5. Membrane reset and trigger refractory counter
        self.v.copy_(torch.where(spike_mask, self.v_reset, v_cand))
        self.ref_counter.copy_(torch.where(spike_mask, self.ref_steps, dec_ref))

        return self.spikes, self.v


class SparseSynapse(nn.Module):
    """Feedforward sparse synaptic projection between two populations."""

    def __init__(
        self,
        num_pre: int,
        num_post: int,
        w_sparse: torch.Tensor,
        device: Union[torch.device, str] = "cpu",
        dtype: torch.dtype = torch.float32,
    ):
        super().__init__()
        self.num_pre = num_pre
        self.num_post = num_post
        self.device = torch.device(device)
        self.dtype = dtype

        w = w_sparse.to(device=self.device, dtype=dtype)
        if not w.is_sparse and not w.is_sparse_csr:
            w = w.to_sparse_csr()
        elif w.is_sparse:
            w = w.to_sparse_csr()
        self.register_buffer("weight", w)

    def forward(self, pre_spikes: torch.Tensor) -> torch.Tensor:
        """Compute post-synaptic current I_post = W @ S_pre.

        Args:
            pre_spikes: Tensor of shape (num_pre,) or (num_pre, 1).

        Returns:
            Tensor of shape (num_post,) representing synaptic current.
        """
        if not pre_spikes.any():
            return torch.zeros(self.num_post, dtype=self.dtype, device=self.device)

        if pre_spikes.dim() == 1:
            pre_spikes = pre_spikes.unsqueeze(1)

        post_current = torch.sparse.mm(self.weight, pre_spikes).squeeze(1)
        return post_current
