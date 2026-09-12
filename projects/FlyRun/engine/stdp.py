"""Vectorized 3-Factor STDP Plasticity Engine with Synaptic Eligibility Traces.

Implements pre/post coincidence tagging modulated by delayed neuromodulatory dopamine bursts.
"""

from __future__ import annotations
import math
import torch
import torch.nn as nn
from typing import Union, Tuple, Optional


class ThreeFactorSTDP(nn.Module):
    """3-Factor STDP with synaptic eligibility traces for delayed reinforcement.

    Dynamics:
        1. Pre- and post-synaptic spike traces:
           x_pre[t]  = x_pre[t-1]  * exp(-dt / tau_plus) + S_pre[t]
           y_post[t] = y_post[t-1] * exp(-dt / tau_minus) + S_post[t]
        2. Coincidence-induced eligibility increment:
           Delta_e[i, j] = A_plus * (S_post[i] * x_pre[j]) - A_minus * (y_post[i] * S_pre[j])
        3. Eligibility trace decay:
           E[t] = E[t-1] * exp(-dt / tau_e) + Delta_e
        4. Dopamine-gated synaptic update:
           Delta_W = eta * Dopamine[t] * E[t] - lambda_decay * W
           W = clip(W + Delta_W, w_min, w_max)
    """

    def __init__(
        self,
        num_pre: int,
        num_post: int,
        dt_ms: float = 1.0,
        tau_eligibility_ms: float = 1000.0,
        tau_plus_ms: float = 20.0,
        tau_minus_ms: float = 25.0,
        a_plus: float = 0.01,
        a_minus: float = 0.012,
        learning_rate_eta: float = 0.05,
        weight_decay_lambda: float = 0.0001,
        w_min: float = 0.0,
        w_max: float = 2.0,
        initial_weights: Optional[torch.Tensor] = None,
        device: Union[torch.device, str] = "cpu",
        dtype: torch.dtype = torch.float32,
    ):
        super().__init__()
        self.num_pre = num_pre
        self.num_post = num_post
        self.dt_ms = dt_ms
        self.device = torch.device(device)
        self.dtype = dtype

        self.tau_e = tau_eligibility_ms
        self.tau_plus = tau_plus_ms
        self.tau_minus = tau_minus_ms
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.eta = learning_rate_eta
        self.weight_decay = weight_decay_lambda
        self.w_min = w_min
        self.w_max = w_max

        # Decay constants
        self.alpha_e = math.exp(-dt_ms / tau_eligibility_ms)
        self.alpha_plus = math.exp(-dt_ms / tau_plus_ms)
        self.alpha_minus = math.exp(-dt_ms / tau_minus_ms)

        # Pre and post continuous spike traces
        self.register_buffer("x_pre", torch.zeros(num_pre, dtype=dtype, device=self.device))
        self.register_buffer("y_post", torch.zeros(num_post, dtype=dtype, device=self.device))

        # Eligibility matrix E: shape (num_post, num_pre)
        self.register_buffer("eligibility", torch.zeros((num_post, num_pre), dtype=dtype, device=self.device))

        # Synaptic weights W: shape (num_post, num_pre)
        if initial_weights is not None:
            self.weights = nn.Parameter(initial_weights.clone().to(device=self.device, dtype=dtype))
        else:
            init_w = torch.empty((num_post, num_pre), dtype=dtype, device=self.device)
            nn.init.uniform_(init_w, 0.1, 0.5)
            self.weights = nn.Parameter(init_w)

    def forward(self, pre_spikes: torch.Tensor) -> torch.Tensor:
        """Compute post-synaptic current I_post = W @ S_pre."""
        if not pre_spikes.any():
            return torch.zeros(self.num_post, dtype=self.dtype, device=self.device)
        return torch.matmul(self.weights, pre_spikes.unsqueeze(1)).squeeze(1)

    def update_traces(self, pre_spikes: torch.Tensor, post_spikes: torch.Tensor) -> None:
        """Advance spike traces and eligibility matrix for a single time step."""
        if pre_spikes.dim() > 1:
            pre_spikes = pre_spikes.squeeze()
        if post_spikes.dim() > 1:
            post_spikes = post_spikes.squeeze()

        # Update continuous presynaptic and postsynaptic trace integrators
        self.x_pre.mul_(self.alpha_plus).add_(pre_spikes)
        self.y_post.mul_(self.alpha_minus).add_(post_spikes)

        # Eligibility trace exponential decay
        self.eligibility.mul_(self.alpha_e)

        # STDP coincidence tagging:
        # LTP contribution: post_spikes[i] * x_pre[j]
        # LTD contribution: y_post[i] * pre_spikes[j]
        if post_spikes.any():
            ltp_increment = self.a_plus * torch.outer(post_spikes, self.x_pre)
            self.eligibility.add_(ltp_increment)

        if pre_spikes.any():
            ltd_increment = self.a_minus * torch.outer(self.y_post, pre_spikes)
            self.eligibility.sub_(ltd_increment)

    def apply_dopamine(self, dopamine: float) -> torch.Tensor:
        """Modulate synaptic weights using the third factor (Dopamine signal).

        Args:
            dopamine: Scalar reinforcement signal, typically in [-1.0, 1.0].
                     Positive: Reward (PAM DANs)
                     Negative: Punishment (PPL1 DANs)

        Returns:
            Delta weight tensor applied.
        """
        if abs(dopamine) < 1e-6:
            return torch.zeros_like(self.weights)

        # Weight delta = eta * dopamine * eligibility - lambda * weights
        delta_w = self.eta * dopamine * self.eligibility - self.weight_decay * self.weights
        with torch.no_grad():
            self.weights.add_(delta_w)
            self.weights.clamp_(min=self.w_min, max=self.w_max)

        return delta_w

    def reset_traces(self) -> None:
        """Reset eligibility and spike trace states."""
        self.x_pre.zero_()
        self.y_post.zero_()
        self.eligibility.zero_()
