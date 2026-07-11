"""Combined Dice + cross-entropy loss for multi-class segmentation.

Cross-entropy drives per-pixel classification; soft Dice counters the strong
class imbalance (myoma and nabothian occupy far fewer voxels than background or
wall). Background is excluded from the Dice term by default so it does not
dominate the score.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DiceCELoss(nn.Module):
    def __init__(
        self,
        num_classes: int,
        dice_weight: float = 1.0,
        ce_weight: float = 1.0,
        include_background: bool = False,
        eps: float = 1e-6,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.dice_weight = dice_weight
        self.ce_weight = ce_weight
        self.include_background = include_background
        self.eps = eps

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(logits, target)

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
