"""Slice-based dataset for 2D multi-class segmentation of the UMD regions.

Orientation: UMD is acquired as sagittal T2 with high in-plane resolution
(~0.45 mm) and thick slices (5 to 6.6 mm) along the last axis. Each 2D slice
along that last axis is therefore a native sagittal plane at full in-plane
resolution. We train on those slices so the network never has to resample across
the thick, anisotropic slice direction (an axial or coronal reformat would blur
anatomy). In-plane spacing is near isotropic, so a square resize introduces no
meaningful geometric distortion; slices are resized to a fixed matrix because
cases differ in size (672 vs 560) and in-plane spacing.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from skimage.transform import resize
from torch.utils.data import Dataset

from .umd_loader import load_case, load_seg

# Background plus the four UMD regions (wall, cavity, myoma, nabothian).
NUM_CLASSES: int = 5
DEFAULT_SIZE: int = 256


def normalize_volume(volume: np.ndarray) -> np.ndarray:
    """Scale intensities to roughly [0, 1] per volume using a high percentile."""
    hi = float(np.percentile(volume, 99.5))
    hi = hi if hi > 0 else 1.0
    return (np.clip(volume, 0.0, hi) / hi).astype(np.float32)


def resize_image(img2d: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Bilinear resize for the grayscale image."""
    return resize(
        img2d, out_shape, order=1, mode="reflect", anti_aliasing=True, preserve_range=True
    ).astype(np.float32)


def resize_mask(mask2d: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Nearest-neighbor resize for the integer label map (no class blending)."""
    return (
        resize(
            mask2d.astype(np.float32),
            out_shape,
            order=0,
            mode="edge",
            anti_aliasing=False,
            preserve_range=True,
        )
        .round()
        .astype(np.int64)
    )


class UMDSliceDataset(Dataset):
    """Yields (image [1, H, W] float32, mask [H, W] int64) for sagittal slices.

    Volumes are cached in memory up to cache_size to avoid reloading; with the
    default single-process loader this keeps training I/O cheap. For a large real
    run, raise cache_size to cover the training set or pre-extract slices to disk.
    """

    def __init__(
        self,
        case_ids: list[str],
        size: int = DEFAULT_SIZE,
        foreground_only: bool = False,
        background_fraction: float = 0.3,
        augment: bool = False,
        cache_size: int = 16,
        root: Path | None = None,
        seed: int = 0,
    ) -> None:
        self.case_ids = list(case_ids)
        self.size = size
        self.augment = augment
        self.root = root
        self._cache: "OrderedDict[str, tuple[np.ndarray, np.ndarray]]" = OrderedDict()
        self._cache_size = cache_size
        self._rng = np.random.RandomState(seed)
        self.index = self._build_index(foreground_only, background_fraction)

    def _build_index(
        self, foreground_only: bool, background_fraction: float
    ) -> list[tuple[str, int]]:
        # Split slices into those carrying a label and pure-background ones, then
        # keep all foreground slices plus a sampled share of background so the
        # model sees empty anatomy and does not overpredict.
        foreground: list[tuple[str, int]] = []
        background: list[tuple[str, int]] = []
        for case_id in self.case_ids:
            seg = load_seg(case_id, self.root)
            for z in range(seg.shape[2]):
                bucket = foreground if bool((seg[:, :, z] > 0).any()) else background
                bucket.append((case_id, z))

        if foreground_only or not background or background_fraction <= 0:
            return foreground

        n_bg = min(len(background), int(round(background_fraction * len(foreground))))
        if n_bg > 0:
            picks = self._rng.choice(len(background), size=n_bg, replace=False)
            foreground = foreground + [background[i] for i in picks]
        return foreground

    def _get_case(self, case_id: str) -> tuple[np.ndarray, np.ndarray]:
        if case_id in self._cache:
            self._cache.move_to_end(case_id)
            return self._cache[case_id]
        case = load_case(case_id, self.root)
        entry = (normalize_volume(case.image), case.seg)
        self._cache[case_id] = entry
        self._cache.move_to_end(case_id)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return entry

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        case_id, z = self.index[i]
        volume, seg = self._get_case(case_id)
        out_shape = (self.size, self.size)
        img = resize_image(volume[:, :, z], out_shape)
        mask = resize_mask(seg[:, :, z], out_shape)

        if self.augment and self._rng.rand() < 0.5:
            # Left-right flip of a sagittal plane (anterior-posterior mirror).
            img = np.ascontiguousarray(img[:, ::-1])
            mask = np.ascontiguousarray(mask[:, ::-1])

        return torch.from_numpy(img).unsqueeze(0), torch.from_numpy(mask)
