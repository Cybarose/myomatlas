"""Combined Dice + cross-entropy loss for multi-class segmentation.

Cross-entropy drives per-pixel classification; soft Dice counters the strong
class imbalance (myoma and nabothian occupy far fewer voxels than background or
wall). Background is excluded from the Dice term by default so it does not
dominate the score. Optional per-class weights up-weight the rare small classes
(cavity, nabothian) in the cross-entropy term.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def median_frequency_weights(
    counts: np.ndarray, cap: float = 10.0, eps: float = 1e-8
) -> np.ndarray:
    """Median-frequency-balanced class weights from per-class voxel counts.

    Frequent classes (background, wall) get weights below 1, rare ones (cavity,
    nabothian) above 1, capped to keep training stable. Absent classes get the
    cap but contribute no pixels, so they do not affect the loss.
    """
    counts = np.asarray(counts, dtype=np.float64)
    total = float(counts.sum())
    freq = counts / max(total, eps)
    present = freq[freq > 0]
    median = float(np.median(present)) if present.size else 1.0
    weights = np.where(freq > 0, median / np.maximum(freq, eps), cap)
    return np.clip(weights, 0.0, cap).astype(np.float32)


class DiceCELoss(nn.Module):
    def __init__(
        self,
        num_classes: int,
        dice_weight: float = 1.0,
        ce_weight: float = 1.0,
        include_background: bool = False,
        class_weights: np.ndarray | list[float] | None = None,
        eps: float = 1e-6,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.dice_weight = dice_weight
        self.ce_weight = ce_weight
        self.include_background = include_background
        self.eps = eps
        # Registered as a buffer so .to(device) moves it with the module.
        if class_weights is not None:
            self.register_buffer(
                "class_weights", torch.as_tensor(class_weights, dtype=torch.float32)
            )
        else:
            self.class_weights = None

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(logits, target, weight=self.class_weights)

        probs = F.softmax(logits, dim=1)
        onehot = F.one_hot(target, self.num_classes).permute(0, 3, 1, 2).float()
        dims = (0, 2, 3)
        intersection = torch.sum(probs * onehot, dims)
        cardinality = torch.sum(probs + onehot, dims)
        dice = (2.0 * intersection + self.eps) / (cardinality + self.eps)
        if not self.include_background:
            dice = dice[1:]
        dice_loss = 1.0 - dice.mean()

        return self.ce_weight * ce + self.dice_weight * dice_loss
