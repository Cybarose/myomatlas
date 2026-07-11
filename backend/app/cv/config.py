"""Configuration for the UMD dataset and CV measurements.

The dataset lives outside the repo and must never be copied in. Its location is
read from the UMD_DATA_DIR environment variable and falls back to the local
default below, so the path is defined in exactly one place.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root is four levels up from this file: backend/app/cv/config.py
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

# Fallback used when UMD_DATA_DIR is not set in the environment.
DEFAULT_UMD_DIR: str = "/Users/sarahtraore/Downloads/umd-data/UMD"

# Mask label values as documented for the UMD dataset.
LABEL_WALL: int = 1
LABEL_CAVITY: int = 2
LABEL_MYOMA: int = 3
LABEL_NABOTHIAN: int = 4

REGION_NAMES: dict[int, str] = {
    LABEL_WALL: "wall",
    LABEL_CAVITY: "cavity",
    LABEL_MYOMA: "myoma",
    LABEL_NABOTHIAN: "nabothian",
}

# Connected components below this physical volume are treated as segmentation
# speckle and dropped when counting individual myomas.
MIN_MYOMA_VOLUME_MM3: float = 30.0


def umd_dir() -> Path:
    """Return the UMD dataset root, honoring the UMD_DATA_DIR override."""
    return Path(os.environ.get("UMD_DATA_DIR", DEFAULT_UMD_DIR))


def default_output_dir() -> Path:
    """Return the directory for derived artifacts (gitignored under data/)."""
    return REPO_ROOT / "data" / "phase1"
