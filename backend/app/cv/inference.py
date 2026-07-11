"""Inference: run the trained U-Net over a volume to produce a UMD-style mask.

The output is an integer label volume (0 background, 1 wall, 2 cavity, 3 myoma,
4 nabothian) on the native voxel grid, identical in structure to the ground-truth
masks. So the Phase 1 loader and measurement code run on predicted masks unchanged
via predicted_case().
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import torch

from .dataset import normalize_volume, resize_image, resize_mask
from .device import pick_device
from .umd_loader import Case, load_case
from .unet import UNet


def load_model(checkpoint_path: Path, device: torch.device) -> tuple[UNet, dict]:
    """Load a trained model and its config from a checkpoint."""
    checkpoint = torch.load(str(checkpoint_path), map_location=device, weights_only=False)
    config = checkpoint["config"]
    model = UNet(
        in_channels=config["in_channels"],
        num_classes=config["num_classes"],
        base_channels=config["base_channels"],
    )
    model.load_state_dict(checkpoint["model_state"])
    model.to(device).eval()
    return model, config


@torch.no_grad()
def predict_volume(
    model: UNet, image: np.ndarray, config: dict, device: torch.device
) -> np.ndarray:
    """Predict a label volume on the native grid, slice by slice along axis 2."""
    size = int(config["size"])
    volume = normalize_volume(image)
    x_dim, y_dim, z_dim = volume.shape
    out = np.zeros((x_dim, y_dim, z_dim), dtype=np.int16)

    for z in range(z_dim):
        slice_in = resize_image(volume[:, :, z], (size, size))
        tensor = torch.from_numpy(slice_in).unsqueeze(0).unsqueeze(0).to(device)
        pred = model(tensor).argmax(dim=1)[0].cpu().numpy().astype(np.int64)
        # Resize the prediction back to the native slice grid so measurements align.
        out[:, :, z] = resize_mask(pred, (x_dim, y_dim)).astype(np.int16)

    return out


def predicted_case(case: Case, seg_pred: np.ndarray) -> Case:
    """Return a copy of the case with its mask replaced by the prediction.

    Spacing and affine come from the image header and are preserved, so
    measure_case() produces valid millimeter measurements on the prediction.
    """
    return dataclasses.replace(case, seg=seg_pred)


def predict_case(
    case_id: str,
    checkpoint_path: Path,
    device: str = "auto",
    root: Path | None = None,
) -> Case:
    """Load a case, predict its mask, and return a Case carrying the prediction."""
    dev = pick_device(device)
    model, config = load_model(checkpoint_path, dev)
    case = load_case(case_id, root)
    seg_pred = predict_volume(model, case.image, config, dev)
    return predicted_case(case, seg_pred)
