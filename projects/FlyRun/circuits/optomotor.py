"""Directional Optomotor Balance Circuit: T4/T5 to Lobula Plate Tangential Cells (HS/VS).

Implements retinotopic Hassenstein-Reichardt Elementary Motion Detectors (EMDs)
and wide-field integration for heading stabilization and lane centering.
"""

from __future__ import annotations
import math
import torch
import torch.nn as nn
from typing import Tuple, Dict, Any

from engine.lif import LIFPopulation


class OptomotorCircuit(nn.Module):
    """Directional Optomotor Balance Circuit using Hassenstein-Reichardt Correlators.

    Architecture:
        Retinal Grid (H x W)
                 │
                 ▼
        Lamina Contrast Filter (L1: ON, L2: OFF)
                 │
                 ▼
        Medulla T4 / T5 EMD Correlator Array (Left/Right & Up/Down)
                 │
                 ▼
        Lobula Plate Tangential Cells:
            - Horizontal System (HS): HSN, HSE, HSS -> Yaw balance
            - Vertical System (VS): VS1 - VS6 -> Pitch/Altitude balance
    """

    def __init__(
        self,
        grid_height: int = 48,
        grid_width: int = 48,
        dt_ms: float = 1.0,
        tau_delay_ms: float = 20.0,
        tau_lamina_ms: float = 15.0,
        device: str = "cpu",
    ):
        super().__init__()
        self.grid_height = grid_height
        self.grid_width = grid_width
        self.dt_ms = dt_ms
        self.device = torch.device(device)

        # Decay constants
        self.alpha_delay = math.exp(-dt_ms / tau_delay_ms)
        self.alpha_lamina = math.exp(-dt_ms / tau_lamina_ms)

        # State buffers for low-pass temporal filters
        self.register_buffer("retina_mean", torch.zeros((grid_height, grid_width), device=self.device))
        self.register_buffer("l1_delayed", torch.zeros((grid_height, grid_width), device=self.device))
        self.register_buffer("l2_delayed", torch.zeros((grid_height, grid_width), device=self.device))

        # Lobula Plate Tangential Neurons (HS and VS) modeled as graded / leaky integrators
        # 3 HS cells (HSN, HSE, HSS) for left eye and 3 for right eye -> 6 units
        # 6 VS cells for vertical flow -> 6 units
        self.hs_population = LIFPopulation(
            num_neurons=6,
            dt_ms=dt_ms,
            tau_m=25.0,
            v_thresh=2.5,
            v_reset=0.0,
            v_rest=0.0,
            tau_ref_ms=1.0,
            device=self.device,
        )

        self.initialized = False

    def reset(self) -> None:
        """Reset temporal state filters and membrane potentials."""
        self.retina_mean.zero_()
        self.l1_delayed.zero_()
        self.l2_delayed.zero_()
        self.hs_population.reset_states()
        self.initialized = False

    def forward(self, visual_frame: torch.Tensor) -> Tuple[float, float, Dict[str, Any]]:
        """Compute directional motion vectors and heading correction.

        Args:
            visual_frame: Tensor of shape (grid_height, grid_width) with values in [0, 1].

        Returns:
            Tuple of:
                yaw_correction: Float in [-1.0, 1.0] indicating steering command.
                forward_expansion: Float estimating forward optic flow magnitude.
                telemetry: Detailed activation metrics.
        """
        frame = visual_frame.to(device=self.device, dtype=torch.float32)

        if not self.initialized:
            self.retina_mean.copy_(frame)
            self.l1_delayed.zero_()
            self.l2_delayed.zero_()
            self.initialized = True
            return 0.0, 0.0, {"yaw_correction": 0.0, "hs_l": 0.0, "hs_r": 0.0}

        # 1. Lamina Contrast Filtering
        # Update running mean: mean[t] = mean[t-1] * alpha + frame * (1 - alpha)
        self.retina_mean.mul_(self.alpha_lamina).add_(frame * (1.0 - self.alpha_lamina))
        contrast = frame - self.retina_mean

        # Split into ON (L1) and OFF (L2) channels
        l1 = torch.clamp(contrast, min=0.0)
        l2 = torch.clamp(-contrast, min=0.0)

        # 2. Hassenstein-Reichardt Correlator (EMD) Calculation
        # Delayed signals
        delayed_l1 = self.l1_delayed.clone()
        delayed_l2 = self.l2_delayed.clone()

        # Update delayed filters for next step
        self.l1_delayed.mul_(self.alpha_delay).add_(l1 * (1.0 - self.alpha_delay))
        self.l2_delayed.mul_(self.alpha_delay).add_(l2 * (1.0 - self.alpha_delay))

        # Horizontal motion: EMD_x = delayed[x] * current[x+1] - current[x] * delayed[x+1]
        # Positive represents Left-to-Right motion, negative represents Right-to-Left motion
        emd_h_l1 = delayed_l1[:, :-1] * l1[:, 1:] - l1[:, :-1] * delayed_l1[:, 1:]
        emd_h_l2 = delayed_l2[:, :-1] * l2[:, 1:] - l2[:, :-1] * delayed_l2[:, 1:]
        emd_horizontal = emd_h_l1 + emd_h_l2

        # 3. Bilateral Lobula Plate Horizontal System (HS) Integration
        # Divide visual field into Left Hemifield and Right Hemifield
        w_half = emd_horizontal.shape[1] // 2
        left_hemifield = emd_horizontal[:, :w_half]
        right_hemifield = emd_horizontal[:, w_half:]

        # Progressive outward optic flow during forward motion:
        # Left hemifield moves Right-to-Left (negative values in our coordinate system)
        # Right hemifield moves Left-to-Right (positive values)
        flow_left = -left_hemifield.mean().item()   # Invert so outward flow is positive
        flow_right = right_hemifield.mean().item()  # Outward flow is positive

        # 4. Optomotor Balance & Steering Output
        # If drifting left, left wall approaches -> flow_left surges -> steer right (+yaw)
        # If drifting right, right wall approaches -> flow_right surges -> steer left (-yaw)
        asymmetry = flow_left - flow_right
        yaw_correction = float(torch.tanh(torch.tensor(asymmetry * 15.0)).item())

        forward_expansion = float((flow_left + flow_right) / 2.0)

        # Drive HS LIF population
        # Units 0-2: Left HS cells; Units 3-5: Right HS cells
        hs_drive = torch.zeros(6, dtype=torch.float32, device=self.device)
        hs_drive[0:3] = max(0.0, flow_left) * 5.0
        hs_drive[3:6] = max(0.0, flow_right) * 5.0
        hs_spikes, hs_v = self.hs_population(i_ext=hs_drive)

        telemetry = {
            "yaw_correction": yaw_correction,
            "flow_left": flow_left,
            "flow_right": flow_right,
            "forward_expansion": forward_expansion,
            "hs_spikes": [int(s.item()) for s in hs_spikes],
            "hs_v": [float(v.item()) for v in hs_v],
        }

        return yaw_correction, forward_expansion, telemetry
