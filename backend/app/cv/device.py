"""Torch device selection shared by training and inference."""

from __future__ import annotations

import torch


def pick_device(name: str = "auto") -> torch.device:
    """Resolve a device string. 'auto' prefers CUDA, then Apple MPS, then CPU."""
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
