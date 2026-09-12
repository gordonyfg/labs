"""Circular ring buffers for zero-allocation spike history and state tracking."""

from __future__ import annotations
import torch


class SpikeRingBuffer:
    """Pre-allocated circular buffer storing spike events over a temporal window.

    Guarantees O(1) in-place insertion with zero memory reallocation.
    """

    def __init__(self, capacity: int, num_units: int, dtype: torch.dtype = torch.float32, device: torch.device | str = "cpu"):
        self.capacity = capacity
        self.num_units = num_units
        self.device = torch.device(device)
        self.dtype = dtype
        
        # Buffer shape: (capacity, num_units)
        self.buffer = torch.zeros((capacity, num_units), dtype=dtype, device=self.device)
        self.head: int = 0
        self.total_steps: int = 0

    def push(self, spikes: torch.Tensor) -> None:
        """Push a new time step of spikes into the circular buffer."""
        # Ensure 1D tensor matching num_units
        if spikes.dim() > 1:
            spikes = spikes.squeeze()
        self.buffer[self.head].copy_(spikes)
        self.head = (self.head + 1) % self.capacity
        self.total_steps += 1

    def latest(self) -> torch.Tensor:
        """Retrieve the most recently pushed spike vector."""
        idx = (self.head - 1 + self.capacity) % self.capacity
        return self.buffer[idx]

    def window(self, window_size: int | None = None) -> torch.Tensor:
        """Retrieve the last `window_size` steps in chronological order.
        
        Returns:
            Tensor of shape (window_size, num_units).
        """
        if window_size is None or window_size > self.capacity:
            window_size = min(self.capacity, self.total_steps)
            
        if window_size == 0:
            return torch.empty((0, self.num_units), dtype=self.dtype, device=self.device)
            
        indices = [(self.head - window_size + i) % self.capacity for i in range(window_size)]
        return self.buffer[indices]

    def reset(self) -> None:
        """Clear all buffer values and reset pointers."""
        self.buffer.zero_()
        self.head = 0
        self.total_steps = 0


class StateTraceBuffer:
    """Float ring buffer for continuous variables such as membrane potentials or currents."""

    def __init__(self, capacity: int, num_units: int, device: torch.device | str = "cpu"):
        self.capacity = capacity
        self.num_units = num_units
        self.device = torch.device(device)
        self.buffer = torch.zeros((capacity, num_units), dtype=torch.float32, device=self.device)
        self.head: int = 0
        self.total_steps: int = 0

    def push(self, state: torch.Tensor) -> None:
        """Push continuous state vector."""
        if state.dim() > 1:
            state = state.squeeze()
        self.buffer[self.head].copy_(state)
        self.head = (self.head + 1) % self.capacity
        self.total_steps += 1

    def window(self, window_size: int | None = None) -> torch.Tensor:
        """Retrieve chronological history."""
        if window_size is None or window_size > self.capacity:
            window_size = min(self.capacity, self.total_steps)
        if window_size == 0:
            return torch.empty((0, self.num_units), dtype=torch.float32, device=self.device)
        indices = [(self.head - window_size + i) % self.capacity for i in range(window_size)]
        return self.buffer[indices]

    def reset(self) -> None:
        self.buffer.zero_()
        self.head = 0
        self.total_steps = 0
