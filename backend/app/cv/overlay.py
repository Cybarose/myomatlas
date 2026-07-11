"""Save a single sagittal slice with the four mask regions overlaid as a PNG.

For visual inspection only. The slice with the most myoma voxels is chosen so
the myoma is visible; fall back to the most-labeled slice when no myoma exists.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless, file-only rendering

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from .config import LABEL_CAVITY, LABEL_MYOMA, LABEL_NABOTHIAN, LABEL_WALL
from .umd_loader import Case

# Region colors: wall, cavity, myoma, nabothian.
_REGION_COLORS = {
    LABEL_WALL: (0.20, 0.55, 0.95),
    LABEL_CAVITY: (0.20, 0.85, 0.45),
    LABEL_MYOMA: (0.95, 0.35, 0.30),
    LABEL_NABOTHIAN: (0.95, 0.80, 0.20),
}
_REGION_LABELS = {
    LABEL_WALL: "wall",
    LABEL_CAVITY: "cavity",
    LABEL_MYOMA: "myoma",
    LABEL_NABOTHIAN: "nabothian",
}


def choose_slice(seg: np.ndarray) -> int:
    """Pick the axis-2 slice index best showing the myoma (or any labels)."""
    myoma_per_slice = (seg == LABEL_MYOMA).sum(axis=(0, 1))
    if myoma_per_slice.max() > 0:
        return int(myoma_per_slice.argmax())
    labeled_per_slice = (seg > 0).sum(axis=(0, 1))
    return int(labeled_per_slice.argmax())


def save_overlay_png(
    case: Case, out_path: Path, slice_index: int | None = None
) -> Path:
    """Render one slice of the T2 image with colored masks to out_path."""
    if slice_index is None:
        slice_index = choose_slice(case.seg)

    image_slice = case.image[:, :, slice_index]
    seg_slice = case.seg[:, :, slice_index]

    # Build an RGBA overlay that is transparent where there is no label.
    overlay = np.zeros((*seg_slice.shape, 4), dtype=np.float32)
    for label, color in _REGION_COLORS.items():
        overlay[seg_slice == label, :3] = color
        overlay[seg_slice == label, 3] = 0.45

    # In-plane spacing is isotropic, so an equal aspect ratio is correct.
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(image_slice.T, cmap="gray", origin="lower")
    ax.imshow(np.transpose(overlay, (1, 0, 2)), origin="lower")
    ax.set_title(f"{case.case_id}  slice {slice_index}")
    ax.axis("off")

    present = [lbl for lbl in _REGION_COLORS if (seg_slice == lbl).any()]
    handles = [
        Patch(facecolor=_REGION_COLORS[lbl], label=_REGION_LABELS[lbl])
        for lbl in present
    ]
    if handles:
        ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.7)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path
