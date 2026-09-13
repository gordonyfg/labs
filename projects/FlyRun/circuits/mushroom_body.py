"""Mushroom Body Circuit for Associative Plasticity and Contextual Reinforcement.

Architecture:
    Sensory Projection Neurons (PNs)
                  │
                  ▼ (Sparse Random Expansion)
    Kenyon Cells (KCs, ~1000 units) ◄───► APL (Global GABAergic Feedback)
                  │
                  ▼ (Plastic Synapses: 3-Factor STDP)
    Mushroom Body Output Neurons (MBONs: Approach vs. Avoid)
                  ▲
                  │ (Dopaminergic Gating: PAM=Reward, PPL1=Punishment)
    Dopaminergic Neurons (DANs)
"""

from __future__ import annotations
import math
import torch
import torch.nn as nn
from typing import Tuple, Dict, Any, Optional

from engine.lif import LIFPopulation
from engine.stdp import ThreeFactorSTDP


class MushroomBodyCircuit(nn.Module):
    """Mushroom Body associative learning circuit with dopamine-gated 3-factor STDP."""

    def __init__(
        self,
        num_pn: int = 32,
        num_kc: int = 512,
        num_mbon: int = 4,
        dt_ms: float = 1.0,
        target_kc_sparsity: float = 0.05,
        device: str = "cpu",
    ):
        super().__init__()
        self.num_pn = num_pn
        self.num_kc = num_kc
        self.num_mbon = num_mbon
        self.dt_ms = dt_ms
        if not 0 < target_kc_sparsity <= 1:
            raise ValueError("target_kc_sparsity must be in (0, 1]")
        self.target_sparsity = target_kc_sparsity
        self.device = torch.device(device)

        # 1. Kenyon Cell Population (LIF)
        self.kc = LIFPopulation(
            num_neurons=num_kc,
            dt_ms=dt_ms,
            tau_m=15.0,
            v_thresh=1.2,
            v_reset=0.0,
            v_rest=0.0,
            tau_ref_ms=3.0,
            device=self.device,
        )

        # 2. MBON Population (LIF)
        self.mbon = LIFPopulation(
            num_neurons=num_mbon,
            dt_ms=dt_ms,
            tau_m=20.0,
            v_thresh=1.0,
            v_reset=0.0,
            v_rest=0.0,
            tau_ref_ms=2.0,
            device=self.device,
        )

        # 3. Sparse Random PN -> KC Projection Matrix
        # Each KC receives input from ~4-8 random PNs
        self._init_pn_to_kc_matrix()

        # 4. Plastic KC -> MBON Synaptic Layer with 3-Factor STDP
        self.kc_to_mbon_synapses = ThreeFactorSTDP(
            num_pre=num_kc,
            num_post=num_mbon,
            dt_ms=dt_ms,
            tau_eligibility_ms=1000.0,
            tau_plus_ms=20.0,
            tau_minus_ms=25.0,
            a_plus=0.015,
            a_minus=0.012,
            learning_rate_eta=0.08,
            device=self.device,
        )

        # APL feedback inhibition parameter
        self.apl_inhibition_gain = 0.4

    def _init_pn_to_kc_matrix(self) -> None:
        """Construct biologically grounded sparse random PN -> KC connectivity."""
        # Each KC samples ~5 random PNs
        k_connections = 5
        rows = []
        cols = []
        for kc_idx in range(self.num_kc):
            chosen_pns = torch.randperm(self.num_pn)[:k_connections]
            for pn_idx in chosen_pns:
                rows.append(kc_idx)
                cols.append(pn_idx.item())

        indices = torch.tensor([rows, cols], dtype=torch.long, device=self.device)
        values = torch.full((len(rows),), 0.35, dtype=torch.float32, device=self.device)
        w_sparse = torch.sparse_coo_tensor(indices, values, (self.num_kc, self.num_pn)).coalesce()
        self.register_buffer("w_pn_kc", w_sparse.to_sparse_csr())

    def reset(self) -> None:
        """Reset neural population states and eligibility traces."""
        self.kc.reset_states()
        self.mbon.reset_states()
        self.kc_to_mbon_synapses.reset_traces()

    def forward(
        self,
        pn_activity: torch.Tensor,
        dopamine: float = 0.0,
    ) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        """Step the mushroom body circuit.

        Args:
            pn_activity: Tensor of shape (num_pn,) representing sensory features.
            dopamine: Scalar reinforcement signal (-1.0 to +1.0) delivered by DANs.

        Returns:
            Tuple of:
                mbon_spikes: Tensor of shape (num_mbon,) output spikes.
                kc_spikes: Tensor of shape (num_kc,) sparse representations.
                telemetry: Activation and plasticity statistics.
        """
        pn = pn_activity.to(device=self.device, dtype=torch.float32)
        if pn.dim() == 1:
            pn_col = pn.unsqueeze(1)
        else:
            pn_col = pn

        # 1. PN -> KC feedforward excitation
        kc_drive = torch.sparse.mm(self.w_pn_kc, pn_col).squeeze(1)

        # 2. APL Global Feedback Inhibition:
        # APL integrates KC activity and provides proportional GABAergic feedback
        prev_kc_activity = self.kc.spikes.sum()
        apl_inhibition = prev_kc_activity * self.apl_inhibition_gain
        kc_net_current = torch.clamp(kc_drive - apl_inhibition, min=0.0)

        # 3. Step Kenyon Cell Population
        kc_spikes, kc_v = self.kc(i_ext=kc_net_current,
                                   max_spikes=int(self.num_kc * self.target_sparsity))

        # 4. KC -> MBON Synaptic Current via STDP weights
        mbon_syn_current = self.kc_to_mbon_synapses(kc_spikes)

        # 5. Step MBON Population
        mbon_spikes, mbon_v = self.mbon(synaptic_input=mbon_syn_current)

        # 6. Update STDP Eligibility Traces and Apply Dopamine
        self.kc_to_mbon_synapses.update_traces(kc_spikes, mbon_spikes)
        delta_w = self.kc_to_mbon_synapses.apply_dopamine(dopamine)

        kc_active_count = int(kc_spikes.sum().item())
        kc_sparsity = kc_active_count / self.num_kc

        telemetry = {
            "kc_active_count": kc_active_count,
            "kc_sparsity": kc_sparsity,
            "mbon_spikes": [int(s.item()) for s in mbon_spikes],
            "mbon_v": [float(v.item()) for v in mbon_v],
            "mean_synaptic_weight": float(self.kc_to_mbon_synapses.weights.mean().item()),
            "delta_w_norm": float(delta_w.norm().item()) if abs(dopamine) > 1e-6 else 0.0,
        }

        return mbon_spikes, kc_spikes, telemetry
