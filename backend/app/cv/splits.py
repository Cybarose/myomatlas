"""Deterministic train/val split over all UMD cases.

The split comes from a fixed seed and is persisted to JSON so it stays identical
across runs and is human-inspectable. Cases are sorted before shuffling so the
result never depends on filesystem enumeration order, and every case (including
the 34 with malformed mask files) is covered.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from .config import default_split_path
from .umd_loader import list_cases

DEFAULT_SEED: int = 42
DEFAULT_VAL_FRACTION: float = 0.2


def make_split(
    seed: int = DEFAULT_SEED,
    val_fraction: float = DEFAULT_VAL_FRACTION,
    cases: list[str] | None = None,
) -> dict:
    """Build a deterministic split dict from the case list and a fixed seed."""
    all_cases = sorted(cases if cases is not None else list_cases())
    shuffled = all_cases[:]
    random.Random(seed).shuffle(shuffled)

    n_val = round(len(shuffled) * val_fraction)
    val = sorted(shuffled[:n_val])
    train = sorted(shuffled[n_val:])
    return {
        "seed": seed,
        "val_fraction": val_fraction,
        "n_total": len(all_cases),
        "n_train": len(train),
        "n_val": len(val),
        "train": train,
        "val": val,
    }


def save_split(split: dict, path: Path | None = None) -> Path:
    out = Path(path) if path else default_split_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(split, indent=2))
    return out


def load_split(path: Path | None = None) -> dict:
    return json.loads((Path(path) if path else default_split_path()).read_text())


def load_or_make_split(
    seed: int = DEFAULT_SEED,
    val_fraction: float = DEFAULT_VAL_FRACTION,
    path: Path | None = None,
    force: bool = False,
) -> dict:
    """Load the persisted split, or create and save it on first use."""
    out = Path(path) if path else default_split_path()
    if out.is_file() and not force:
        return load_split(out)
    split = make_split(seed=seed, val_fraction=val_fraction)
    save_split(split, out)
    return split
