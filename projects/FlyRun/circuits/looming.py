"""Lobula Columnar (LC4 / LPLC2) to Giant Fiber (GF / DNp01) Looming Circuit.

Detects rapid optical expansion (looming) and triggers emergency escape reflex (Jump).
"""

from __future__ import annotations
import math
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, Optional, Dict, Any

from engine.lif import LIFPopulation, SparseSynapse


class LoomingEscapeCircuit(nn.Module):
    """Biological Looming Escape Circuit.

    Architecture:
        Visual Retinotopic Input (Ommatidia grid)
                     │
                     ▼ (OFF-pathway luminance decrement)
           LC4 / LPLC2 Population (Lobula Columnar)
                     │
                     ▼ (Sparse Excitatory Cholinergic Synapses)
           Giant Fiber (GF / DNp01) (Descending Motor Command)
    """

    def __init__(
        self,
        grid_height: int = 48,
        grid_width: int = 48,
        num_lc4: int = 256,
        dt_ms: float = 1.0,
        device: str = "cpu",
    ):
        super().__init__()
        self.grid_height = grid_height
        self.grid_width = grid_width
        self.num_lc4 = num_lc4
        self.dt_ms = dt_ms
        self.device = torch.device(device)

        # 1. LC4 Population: Fast integration, medium threshold
        self.lc4 = LIFPopulation(
            num_neurons=num_lc4,
            dt_ms=dt_ms,
            tau_m=10.0,
            v_thresh=1.0,
            v_reset=0.0,
            v_rest=0.0,
            tau_ref_ms=2.0,
            device=self.device,
        )

        # 2. Giant Fiber (GF / DNp01): 2 units (Left GF, Right GF)
        self.giant_fiber = LIFPopulation(
            num_neurons=2,
            dt_ms=dt_ms,
            tau_m=8.0,
            v_thresh=1.8,
            v_reset=-0.5,
            v_rest=0.0,
            tau_ref_ms=15.0,  # Extended refractory period prevents multiple rapid triggers
            device=self.device,
        )

        # 3. Retinotopic to LC4 Receptive Fields
        # Each LC4 neuron has a receptive field center on the visual grid
        self._init_receptive_fields()

        # 4. Sparse Synapses: LC4 -> Giant Fiber
        # Biological ground truth: LC4 neurons synapse heavily and directly onto GF dendrites
        self._init_lc4_to_gf_synapses()

        # Optical luminance memory for temporal contrast detection
        self.prev_frame: Optional[torch.Tensor] = None

    def _init_receptive_fields(self) -> None:
        """Map LC4 neurons retinotopically across the visual field via sparse matrix."""
        side = int(math.ceil(math.sqrt(self.num_lc4)))
        ys = torch.linspace(0.1, 0.9, side, device=self.device)
        xs = torch.linspace(0.1, 0.9, side, device=self.device)
        grid_y, grid_x = torch.meshgrid(ys, xs, indexing="ij")
        
        centers_y = (grid_y.flatten()[: self.num_lc4] * (self.grid_height - 1)).round().long()
        centers_x = (grid_x.flatten()[: self.num_lc4] * (self.grid_width - 1)).round().long()
        self.register_buffer("rf_centers_y", centers_y)
        self.register_buffer("rf_centers_x", centers_x)

        # Precompute sparse receptive field mapping: (num_lc4, grid_height * grid_width)
        rows = []
        cols = []
        vals = []
        for i in range(self.num_lc4):
            cy = centers_y[i].item()
            cx = centers_x[i].item()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy = max(0, min(self.grid_height - 1, cy + dy))
                    xx = max(0, min(self.grid_width - 1, cx + dx))
                    flat_idx = yy * self.grid_width + xx
                    rows.append(i)
                    cols.append(flat_idx)
                    vals.append(1.0)

        indices = torch.tensor([rows, cols], dtype=torch.long, device=self.device)
        values = torch.tensor(vals, dtype=torch.float32, device=self.device)
        rf_sparse = torch.sparse_coo_tensor(
            indices, values, (self.num_lc4, self.grid_height * self.grid_width)
        ).coalesce()
        self.register_buffer("w_rf", rf_sparse.to_sparse_csr())

    def _init_lc4_to_gf_synapses(self) -> None:
        """Initialize sparse excitatory synaptic connectivity matrix from LC4 to Giant Fiber."""
        # Bilateral convergence: left hemifield LC4 -> Left GF, right hemifield LC4 -> Right GF,
        # with strong central convergence to both
        rows = []
        cols = []
        weights = []

        half_w = (self.grid_width - 1) / 2.0
        for i in range(self.num_lc4):
            cx = self.rf_centers_x[i].item()
            # Left GF (index 0)
            if cx <= half_w + 4:
                rows.append(0)
                cols.append(i)
                weights.append(0.045)  # Excitatory weight
            # Right GF (index 1)
            if cx >= half_w - 4:
                rows.append(1)
                cols.append(i)
                weights.append(0.045)

        indices = torch.tensor([rows, cols], dtype=torch.long, device=self.device)
        values = torch.tensor(weights, dtype=torch.float32, device=self.device)
        w_sparse = torch.sparse_coo_tensor(indices, values, (2, self.num_lc4)).coalesce()
        self.syn_lc4_gf = SparseSynapse(self.num_lc4, 2, w_sparse, device=self.device)

    def reset(self) -> None:
        """Reset neural populations and visual history."""
        self.lc4.reset_states()
        self.giant_fiber.reset_states()
        self.prev_frame = None

    def process_frame(self, visual_frame: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        """Process a compound eye retinal luminance frame and step the circuit.

        Args:
            visual_frame: 2D Tensor of shape (grid_height, grid_width) with values in [0, 1].

        Returns:
            Tuple of:
                gf_spikes: Tensor of shape (2,) representing Left and Right GF spikes.
                lc4_spikes: Tensor of shape (num_lc4,) representing LC4 spikes.
                telemetry: Dictionary containing intermediate activations.
        """
        frame = visual_frame.to(device=self.device, dtype=torch.float32)

        # 1. Temporal Luminance Decrement (OFF-pathway transient contrast)
        if self.prev_frame is None:
            self.prev_frame = frame.clone()
            temporal_contrast = torch.zeros_like(frame)
        else:
            # Darkening edge: previous frame was brighter than current frame
            # I_contrast = max(0, prev - current)
            temporal_contrast = torch.clamp(self.prev_frame - frame, min=0.0)
            self.prev_frame.copy_(frame)

        # 2. Receptive Field Integration for LC4 Population via precomputed sparse projection
        flat_contrast = temporal_contrast.flatten().unsqueeze(1)
        lc4_drive = torch.sparse.mm(self.w_rf, flat_contrast).squeeze(1)
        
        # Scaling constant for synaptic input drive
        lc4_input_current = lc4_drive * 1.8

        # 3. Step LC4 LIF population
        lc4_spikes, lc4_v = self.lc4(i_ext=lc4_input_current)

        # 4. Sparse Synaptic Transmission: LC4 -> Giant Fiber
        gf_syn_current = self.syn_lc4_gf(lc4_spikes)

        # 5. Step Giant Fiber LIF population
        gf_spikes, gf_v = self.giant_fiber(synaptic_input=gf_syn_current)

        # Action: Jump trigger if either GF fires
        jump_command = (gf_spikes.sum() > 0).item()

        telemetry = {
            "lc4_spikes_count": int(lc4_spikes.sum().item()),
            "lc4_mean_v": float(lc4_v.mean().item()),
            "gf_v": [float(v.item()) for v in gf_v],
            "gf_spikes": [int(s.item()) for s in gf_spikes],
            "jump_command": jump_command,
        }

        return gf_spikes, lc4_spikes, telemetry


def generate_synthetic_looming_stimulus(
    grid_height: int = 48,
    grid_width: int = 48,
    num_steps: int = 150,
    r_over_v: float = 40.0,
    t_collision: int = 120,
    center_y: Optional[float] = None,
    center_x: Optional[float] = None,
) -> torch.Tensor:
    """Generate a sequence of synthetic looming stimulus frames.

    An expanding dark disk on a bright background simulating an oncoming obstacle.
    Angular size theta(t) follows:
        theta(t) = 2 * arctan( (r / v) / (t_collision - t) )

    Args:
        grid_height: Height in ommatidia.
        grid_width: Width in ommatidia.
        num_steps: Total frames in sequence.
        r_over_v: Ratio of object half-size to approach speed in ms.
        t_collision: Time step of collision impact.

    Returns:
        Tensor of shape (num_steps, grid_height, grid_width).
    """
    if center_y is None:
        center_y = grid_height / 2.0
    if center_x is None:
        center_x = grid_width / 2.0

    frames = torch.ones((num_steps, grid_height, grid_width), dtype=torch.float32)

    ys = torch.arange(grid_height, dtype=torch.float32).unsqueeze(1).repeat(1, grid_width)
    xs = torch.arange(grid_width, dtype=torch.float32).unsqueeze(0).repeat(grid_height, 1)
    dist_sq = (ys - center_y) ** 2 + (xs - center_x) ** 2

    max_radius = min(grid_height, grid_width) * 0.9

    for t in range(num_steps):
        time_to_collision = max(1.0, float(t_collision - t))
        # Angular expansion formula
        theta = 2.0 * math.atan((r_over_v) / time_to_collision)
        # Map angular size to pixel radius
        radius = (theta / math.pi) * (max_radius)
        if radius > 0.5:
            disk_mask = dist_sq <= (radius**2)
            # Disk is dark (0.1), background is bright (0.9)
            frames[t][disk_mask] = 0.1

    return frames
