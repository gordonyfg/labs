"""Compound Eye Vision Sensor Model.

Models Drosophila compound eye optics:
- Hexagonal/planar ommatidial array (48x48 resolution).
- Acceptance angle and angular receptive fields.
- Contrast normalization and event generation.
"""

from __future__ import annotations
import math
import numpy as np
import torch
from typing import Tuple


class CompoundEye:
    """Simulates a wide-angle compound eye sensor.

    Attributes:
        height: Number of ommatidia rows (elevation).
        width: Number of ommatidia columns (azimuth).
        fov_azimuth_deg: Total horizontal field of view in degrees.
        fov_elevation_deg: Total vertical field of view in degrees.
    """

    def __init__(
        self,
        height: int = 48,
        width: int = 48,
        fov_azimuth_deg: float = 180.0,
        fov_elevation_deg: float = 120.0,
        device: str = "cpu",
    ):
        self.height = height
        self.width = width
        self.fov_azimuth = math.radians(fov_azimuth_deg)
        self.fov_elevation = math.radians(fov_elevation_deg)
        self.device = torch.device(device)

        # Precompute viewing angles (azimuth phi, elevation theta) for each ommatidium
        half_az = self.fov_azimuth / 2.0
        half_el = self.fov_elevation / 2.0

        phi = torch.linspace(-half_az, half_az, width, device=self.device)
        theta = torch.linspace(half_el, -half_el, height, device=self.device)

        self.theta_grid, self.phi_grid = torch.meshgrid(theta, phi, indexing="ij")
        
        # Unit direction vectors in runner-centric coordinates (Forward=+Z, Right=+X, Up=+Y)
        # x = sin(phi) * cos(theta)
        # y = sin(theta)
        # z = cos(phi) * cos(theta)
        self.ray_dirs_x = torch.sin(self.phi_grid) * torch.cos(self.theta_grid)
        self.ray_dirs_y = torch.sin(self.theta_grid)
        self.ray_dirs_z = torch.cos(self.phi_grid) * torch.cos(self.theta_grid)

    def render_point_cloud(
        self,
        points_xyz: torch.Tensor,
        intensities: torch.Tensor,
        background_val: float = 0.85,
    ) -> torch.Tensor:
        """Fast approximate splatting of 3D points onto compound eye array.

        Args:
            points_xyz: Tensor of shape (N, 3) in runner coordinate frame.
            intensities: Tensor of shape (N,) in [0, 1].
            background_val: Default luminance of the visual field.

        Returns:
            Retinal luminance tensor of shape (height, width).
        """
        frame = torch.full((self.height, self.width), background_val, dtype=torch.float32, device=self.device)
        if points_xyz.shape[0] == 0:
            return frame

        # Filter points in front of the runner (z > 0.1)
        valid = points_xyz[:, 2] > 0.1
        pts = points_xyz[valid]
        vals = intensities[valid]
        if pts.shape[0] == 0:
            return frame

        # Compute azimuth and elevation
        x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
        phi = torch.atan2(x, z)
        hyp = torch.sqrt(x * x + z * z)
        theta = torch.atan2(y, hyp)

        # Map to pixel coordinates
        half_az = self.fov_azimuth / 2.0
        half_el = self.fov_elevation / 2.0

        col = ((phi + half_az) / self.fov_azimuth * (self.width - 1)).round().long()
        row = ((half_el - theta) / self.fov_elevation * (self.height - 1)).round().long()

        mask = (col >= 0) & (col < self.width) & (row >= 0) & (row < self.height)
        c = col[mask]
        r = row[mask]
        v = vals[mask]

        # Draw onto frame
        frame[r, c] = v
        return frame
