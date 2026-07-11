"""Segmentation metrics: per-class Dice via accumulated overlap.

Overlap counts are accumulated across cases so Dice can be micro-averaged over a
whole validation split (stable, and it sidesteps the undefined per-case Dice when
a class is absent from a single case).
"""

from __future__ import annotations

import numpy as np


def overlap_counts(
    pred: np.ndarray, gt: np.ndarray, num_classes: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return per-class intersection and cardinality (|pred_c| + |gt_c|)."""
    inter = np.zeros(num_classes, dtype=np.float64)
    card = np.zeros(num_classes, dtype=np.float64)
    for c in range(num_classes):
        p = pred == c
        g = gt == c
        inter[c] = float(np.logical_and(p, g).sum())
        card[c] = float(p.sum() + g.sum())
    return inter, card


def dice_from_counts(inter: np.ndarray, card: np.ndarray) -> np.ndarray:
    """Dice per class from accumulated counts; NaN where a class never appears."""
    dice = np.full(len(inter), np.nan, dtype=np.float64)
    nonzero = card > 0
    dice[nonzero] = 2.0 * inter[nonzero] / card[nonzero]
    return dice
