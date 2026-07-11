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


def mps_allocated_bytes() -> int:
    """Current MPS allocation in bytes, or 0 when MPS is not in use."""
    mps = getattr(torch, "mps", None)
    if mps is None:
        return 0
    try:
        return int(torch.mps.current_allocated_memory())
    except Exception:
        return 0


def host_peak_rss_bytes() -> int:
    """Peak resident set size of this process (bytes on macOS, KiB on Linux)."""
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
