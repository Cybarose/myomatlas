"""Loader for the UMD (Uterine Myoma MRI Dataset) cases.

Each case is a folder such as UMD_221129_001 that contains a T2WI volume
(<case>_t2.nii.gz) and a multi-label mask (<case>_seg.nii.gz). Only these two
nii.gz files are used; the per-slice .dcm files are ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np

from .config import umd_dir


@dataclass
class Case:
    """One loaded UMD case with image, mask, and physical voxel spacing."""

    case_id: str
    image: np.ndarray  # T2WI volume, float32, shape (X, Y, Z)
    seg: np.ndarray  # integer mask, same shape, labels 0..4
    spacing_mm: tuple[float, float, float]  # per-axis voxel size from header
    affine: np.ndarray
    image_path: Path
    seg_path: Path


def case_dir(case_id: str, root: Path | None = None) -> Path:
    """Return the folder for a case id, defaulting to the configured dataset."""
    return (root or umd_dir()) / case_id


def list_cases(root: Path | None = None) -> list[str]:
    """Return sorted case ids (folders named UMD_*), skipping stray entries."""
    base = root or umd_dir()
    if not base.is_dir():
        raise FileNotFoundError(f"UMD dataset directory not found: {base}")
    return sorted(p.name for p in base.iterdir() if p.is_dir() and p.name.startswith("UMD_"))


def _load_nii(path: Path) -> nib.Nifti1Image:
    """Load a NIfTI, tolerating files that carry a .gz name but are not gzipped.

    Some UMD masks are shipped as plain (uncompressed) NIfTI despite the .nii.gz
    extension, which makes nibabel's extension-based gunzip fail. We route by the
    gzip magic bytes instead.
    """
    with path.open("rb") as handle:
        magic = handle.read(2)
    if magic == b"\x1f\x8b":
        return nib.load(str(path))
    with path.open("rb") as handle:
        return nib.Nifti1Image.from_bytes(handle.read())


def _find_t2(folder: Path, case_id: str) -> Path:
    exact = folder / f"{case_id}_t2.nii.gz"
    if exact.is_file():
        return exact
    matches = sorted(folder.glob("*_t2.nii.gz"))
    if not matches:
        raise FileNotFoundError(f"No T2 volume (*_t2.nii.gz) in {folder}")
    return matches[0]


def _find_seg(folder: Path, image_path: Path) -> Path:
    """Locate the mask file, tolerating known UMD filename typos.

    Some cases misname the mask (_seq instead of _seg, or a doubled digit in the
    case id). Each case folder holds exactly one non-T2 nii.gz, so the mask is the
    nii.gz that is not the image, preferring a seg/seq-looking name when present.
    """
    exact = image_path.parent / f"{folder.name}_seg.nii.gz"
    if exact.is_file():
        return exact
    candidates = [p for p in sorted(folder.glob("*.nii.gz")) if p != image_path]
    if not candidates:
        raise FileNotFoundError(f"No mask nii.gz found in {folder}")
    for key in ("seg", "seq"):
        for path in candidates:
            if key in path.name.lower():
                return path
    return candidates[0]


def _nii_paths(case_id: str, root: Path | None = None) -> tuple[Path, Path]:
    folder = case_dir(case_id, root)
    if not folder.is_dir():
        raise FileNotFoundError(f"Case folder not found: {folder}")
    image_path = _find_t2(folder, case_id)
    seg_path = _find_seg(folder, image_path)
    return image_path, seg_path


def load_case(case_id: str, root: Path | None = None) -> Case:
    """Load one case's T2WI volume and mask with header-derived spacing."""
    image_path, seg_path = _nii_paths(case_id, root)

    image_nii = _load_nii(image_path)
    seg_nii = _load_nii(seg_path)

    image = np.asarray(image_nii.get_fdata(), dtype=np.float32)
    # Masks are integer labels; round to guard against float storage.
    seg = np.rint(np.asanyarray(seg_nii.dataobj)).astype(np.int16)

    if image.shape != seg.shape:
        raise ValueError(
            f"{case_id}: image shape {image.shape} != mask shape {seg.shape}"
        )

    # Spacing comes from the image header, not the mask. The mask sits on the same
    # voxel grid, and some UMD masks ship with a placeholder header (1 mm isotropic,
    # wrong affine), so the image is the reliable geometric reference.
    zooms = image_nii.header.get_zooms()[:3]
    spacing_mm = (float(zooms[0]), float(zooms[1]), float(zooms[2]))

    return Case(
        case_id=case_id,
        image=image,
        seg=seg,
        spacing_mm=spacing_mm,
        affine=np.asarray(image_nii.affine, dtype=np.float64),
        image_path=image_path,
        seg_path=seg_path,
    )
