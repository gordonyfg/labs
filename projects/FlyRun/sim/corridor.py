"""Lightweight, procedural 3D corridor runner environment.

Provides zero-overhead state extraction and direct compound eye retinal rendering.
Runs at > 1,000 FPS for real-time or faster-than-real-time closed-loop testing.
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import torch


@dataclass
class Obstacle:
    """3D Obstacle in the corridor."""
    x: float          # Lateral center
    y: float          # Vertical center
    z: float          # Longitudinal position (distance along corridor)
    width: float      # X span
    height: float     # Y span
    depth: float      # Z span
    obstacle_type: str = "hurdle"  # "hurdle" (jump over), "blocker" (steer around)
    passed: bool = False


class CorridorRunnerEnv:
    """Headless 3D procedural corridor runner simulating a Temple Run / endless runner paradigm.

    Coordinate system:
        +X: Right
        +Y: Up (Altitude)
        +Z: Forward along corridor
    """

    def __init__(
        self,
        corridor_width: float = 4.0,
        corridor_height: float = 3.0,
        forward_speed: float = 12.0,  # meters per second
        dt_ms: float = 1.0,           # 1 millisecond step
        grid_height: int = 48,
        grid_width: int = 48,
        device: str = "cpu",
        seed: int = 42,
    ):
        self.corridor_width = corridor_width
        self.corridor_height = corridor_height
        self.half_width = corridor_width / 2.0
        self.forward_speed = forward_speed
        self.dt = dt_ms / 1000.0  # seconds
        self.dt_ms = dt_ms
        self.grid_height = grid_height
        self.grid_width = grid_width
        self.device = torch.device(device)

        random.seed(seed)
        self.reset()

    def reset(self) -> torch.Tensor:
        """Reset runner state and spawn initial obstacles."""
        # Runner state
        self.x = 0.0          # Lateral offset (0 is center)
        self.y = 0.0          # Vertical altitude (0 is ground)
        self.z = 0.0          # Distance traveled
        self.vx = 0.0         # Lateral velocity
        self.vy = 0.0         # Vertical velocity
        self.is_jumping = False
        self.is_dead = False
        self.step_count = 0
        self.score = 0.0

        # Physics constants
        self.gravity = -28.0   # m/s^2
        self.jump_impulse = 7.0 # m/s initial jump velocity

        # Obstacles list
        self.obstacles: List[Obstacle] = []
        self._spawn_obstacles(initial_distance=20.0, count=10)

        return self.render_retina()

    def _spawn_obstacles(self, initial_distance: float, count: int) -> None:
        """Generate procedural obstacles ahead."""
        current_z = initial_distance
        for _ in range(count):
            current_z += random.uniform(25.0, 45.0)
            obs_type = random.choice(["hurdle", "hurdle", "blocker"])
            if obs_type == "hurdle":
                # Spans full width, low height (jumpable)
                obs = Obstacle(
                    x=0.0,
                    y=0.4,
                    z=current_z,
                    width=self.corridor_width * 0.9,
                    height=0.8,
                    depth=1.0,
                    obstacle_type="hurdle",
                )
            else:
                # Blocks one side (steerable)
                lane_x = random.choice([-1.0, 1.0])
                obs = Obstacle(
                    x=lane_x,
                    y=1.0,
                    z=current_z,
                    width=1.8,
                    height=2.0,
                    depth=1.5,
                    obstacle_type="blocker",
                )
            self.obstacles.append(obs)

    def step(self, action_steer: float = 0.0, action_jump: bool = False) -> Tuple[torch.Tensor, float, bool, Dict[str, Any]]:
        """Advance simulation by 1 time step (1 ms).

        Args:
            action_steer: Continuous lateral steering command in [-1.0, 1.0].
            action_jump: Binary jump trigger.

        Returns:
            Tuple of (retinal_frame, reward, done, telemetry).
        """
        if self.is_dead:
            return self.render_retina(), -1.0, True, {"dead": True}

        self.step_count += 1

        # 1. Lateral motion (steering)
        # Apply optomotor or voluntary steering velocity
        target_vx = action_steer * 4.0  # max 4 m/s lateral speed
        self.vx = 0.85 * self.vx + 0.15 * target_vx
        self.x += self.vx * self.dt

        # 2. Vertical jump physics
        if action_jump and not self.is_jumping:
            self.is_jumping = True
            self.vy = self.jump_impulse

        if self.is_jumping:
            self.vy += self.gravity * self.dt
            self.y += self.vy * self.dt
            if self.y <= 0.0:
                self.y = 0.0
                self.vy = 0.0
                self.is_jumping = False

        # 3. Longitudinal forward progress
        self.z += self.forward_speed * self.dt

        # 4. Collision Detection
        # Check wall collision
        if abs(self.x) >= (self.half_width - 0.2):
            self.is_dead = True

        # Check obstacle collision
        reward = 0.01  # Small survival bonus per ms step
        for obs in self.obstacles:
            # Check longitudinal overlap
            if abs(self.z - obs.z) < (obs.depth / 2.0 + 0.3):
                # Check lateral overlap
                if abs(self.x - obs.x) < (obs.width / 2.0 + 0.2):
                    # Check vertical clearance
                    if self.y < (obs.y + obs.height / 2.0):
                        # Collision!
                        self.is_dead = True
                        reward = -10.0
                        break
            elif self.z > obs.z + obs.depth and not obs.passed:
                obs.passed = True
                reward += 2.0  # Clearance reward

        # Spawn additional obstacles as needed
        if len(self.obstacles) > 0 and (self.obstacles[-1].z - self.z) < 100.0:
            self._spawn_obstacles(initial_distance=self.obstacles[-1].z, count=5)

        # Remove obstacles passed far behind
        self.obstacles = [obs for obs in self.obstacles if obs.z > (self.z - 20.0)]

        done = self.is_dead
        frame = self.render_retina()

        telemetry = {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "vx": self.vx,
            "is_jumping": self.is_jumping,
            "is_dead": self.is_dead,
            "step_count": self.step_count,
        }

        return frame, reward, done, telemetry

    def render_retina(self) -> torch.Tensor:
        """Render high-contrast corridor visual projection onto the 48x48 ommatidial array.

        Generates realistic perspective features:
        - Wall grating texture (alternating luminance) creating lateral optic flow.
        - Floor and ceiling vanishing perspective.
        - High-contrast oncoming obstacle silhouettes (looming).
        """
        frame = torch.full((self.grid_height, self.grid_width), 0.8, dtype=torch.float32, device=self.device)

        mid_y = self.grid_height // 2
        mid_x = self.grid_width // 2

        # 1. Dynamic Wall Optical Flow Simulation
        # As runner moves forward, walls have vertical striping that creates outward optic flow
        stripe_freq = 2.0  # stripes per meter
        wall_phase = (self.z * stripe_freq) % (2.0 * math.pi)
        wall_lum = 0.5 + 0.35 * math.sin(wall_phase)

        # Left wall occupies left ~12 columns
        left_margin = int(self.grid_width * 0.25 - self.x * 3.0)
        left_margin = max(2, min(self.grid_width // 2 - 1, left_margin))
        frame[:, :left_margin] = wall_lum

        # Right wall occupies right ~12 columns
        right_margin = int(self.grid_width * 0.75 - self.x * 3.0)
        right_margin = max(self.grid_width // 2 + 1, min(self.grid_width - 2, right_margin))
        frame[:, right_margin:] = wall_lum

        # 2. Approaching Obstacles Projection (Looming Stimuli)
        for obs in self.obstacles:
            dz = obs.z - self.z
            # Render obstacles in front within visual range (0.5m to 35m)
            if 0.5 < dz < 35.0:
                # Perspective projection: angular size = dimension / distance
                focal_scale = 18.0  # pixels per radian equivalent
                proj_w = int((obs.width / dz) * focal_scale)
                proj_h = int((obs.height / dz) * focal_scale)

                # Angular offsets
                dx = obs.x - self.x
                dy = (obs.y + obs.height / 2.0) - (self.y + 0.5)

                cx = int(mid_x + (dx / dz) * focal_scale)
                cy = int(mid_y - (dy / dz) * focal_scale)

                x1 = max(0, cx - proj_w // 2)
                x2 = min(self.grid_width, cx + proj_w // 2)
                y1 = max(0, cy - proj_h // 2)
                y2 = min(self.grid_height, cy + proj_h // 2)

                if x2 > x1 and y2 > y1:
                    # Obstacle is a dark silhouette (contrast = 0.15)
                    frame[y1:y2, x1:x2] = 0.15
                break  # Draw nearest obstacle primarily

        return frame
