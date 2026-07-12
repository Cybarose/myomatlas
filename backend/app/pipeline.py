"""Case pipeline: predicted masks, measurements and mesh, cached on disk.

The mesh and the measurements are both derived from the same predicted mask, so the
myoma ids in the 3D scene (myoma_1, myoma_2 and so on) always line up with the ids in
the analysis. Segmentation is the expensive step, so it is computed once per case and
reused.
"""

from __future__ import annotations

import dataclasses
import json
import os
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

from .cv.config import REPO_ROOT, default_models_dir
from .cv.device import pick_device
from .cv.inference import load_model, predict_volume
from .cv.measurements import measure_case
from .cv.reconstruct import reconstruct_case_to_glb
from .cv.umd_loader import Case, load_case
from .cv.unet import UNet

CACHE_DIR: Path = REPO_ROOT / "data" / "cache"
CHECKPOINT: Path = default_models_dir() / "unet_best.pt"

# FastAPI runs sync routes in a worker thread, and torch MPS deadlocks when driven from
# one. A single case on CPU takes seconds, so CPU is the safe default here. Override
# with MYOMATLAS_DEVICE if the server runs on a machine with CUDA.
DEVICE: str = os.environ.get("MYOMATLAS_DEVICE", "cpu")

# Segmentation and meshing are slow, so a cache miss is computed once even if two
# requests for the same case arrive together. Reentrant, because mesh_path holds the
# lock and then calls predicted_case, which takes it again on the same thread.
_LOCK = threading.RLock()


class PipelineError(RuntimeError):
    """Raised when a case cannot be segmented, measured or reconstructed."""


@lru_cache(maxsize=1)
def _model() -> tuple[UNet, dict, torch.device]:
    if not CHECKPOINT.is_file():
        raise PipelineError(f"Model weights not found: {CHECKPOINT}")
    device = pick_device(DEVICE)
    model, config = load_model(CHECKPOINT, device)
    return model, config, device


def predicted_case(case_id: str) -> Case:
    """Return the case carrying the U-Net predicted mask."""
    case = load_case(case_id)
    cache = CACHE_DIR / f"{case_id}_seg.npy"
    if cache.is_file():
        return dataclasses.replace(case, seg=np.load(cache))

    with _LOCK:
        if cache.is_file():
            return dataclasses.replace(case, seg=np.load(cache))
        model, config, device = _model()
        seg = predict_volume(model, case.image, config, device)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.save(cache, seg)
    return dataclasses.replace(case, seg=seg)


def measurements(case_id: str) -> dict:
    """Measurement JSON for the predicted mask."""
    cache = CACHE_DIR / f"{case_id}_measurements.json"
    if cache.is_file():
        return json.loads(cache.read_text())

    result = measure_case(predicted_case(case_id))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


def mesh_path(case_id: str) -> Path:
    """Path to the GLB reconstructed from the same predicted mask."""
    out = CACHE_DIR / f"{case_id}.glb"
    if out.is_file():
        return out

    with _LOCK:
        if out.is_file():
            return out
        reconstruct_case_to_glb(predicted_case(case_id), out)
    return out
