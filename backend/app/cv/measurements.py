"""Per-case and per-myoma geometric measurements from the UMD masks.

All physical quantities use the header voxel spacing so the anisotropic slice
thickness (~6.6 mm) is respected. Distances are in millimeters via anisotropic
Euclidean distance transforms.

FIGO typing (Phase 5) needs, per myoma: size, whether it touches the uterine
cavity (submucosal side), whether it reaches the serosa (subserosal side), and
how much of it is buried in the myometrium. The intramural percentage here is a
surface-adjacency proxy computed from the segmentation, documented as such so it
is not overclaimed as a validated volumetric protrusion measure.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from .config import (
    LABEL_CAVITY,
    LABEL_MYOMA,
    LABEL_NABOTHIAN,
    LABEL_WALL,
    MIN_MYOMA_VOLUME_MM3,
)
from .umd_loader import Case

# 6-connectivity keeps distinct myomas that only touch at a corner separate.
_STRUCT_FACE = ndimage.generate_binary_structure(3, 1)
# 26-connectivity is used for contact tests so any touch counts as adjacency.
_STRUCT_FULL = ndimage.generate_binary_structure(3, 3)


def _voxel_volume_mm3(spacing: tuple[float, float, float]) -> float:
    return float(spacing[0] * spacing[1] * spacing[2])


def _contacts(mask_a: np.ndarray, mask_b: np.ndarray) -> bool:
    """True if any voxel of mask_a is 26-adjacent to a voxel of mask_b."""
    if not mask_b.any():
        return False
    return bool((ndimage.binary_dilation(mask_a, _STRUCT_FULL) & mask_b).any())


def _min_distance_mm(
    component: np.ndarray,
    target: np.ndarray,
    spacing: tuple[float, float, float],
) -> float | None:
    """Closest approach in mm from a component to a target region."""
    if not target.any():
        return None
    # Distance from every voxel to the nearest target voxel.
    dist = ndimage.distance_transform_edt(~target, sampling=spacing)
    return float(dist[component].min())


def label_myomas(
    seg: np.ndarray, spacing: tuple[float, float, float]
) -> tuple[np.ndarray, int]:
    """Label individual myomas, dropping components below the volume floor."""
    voxel_vol = _voxel_volume_mm3(spacing)
    labeled, num = ndimage.label(seg == LABEL_MYOMA, structure=_STRUCT_FACE)
    if num == 0:
        return labeled, 0

    keep = np.zeros_like(labeled)
    next_id = 0
    for comp_id in range(1, num + 1):
        component = labeled == comp_id
        if component.sum() * voxel_vol >= MIN_MYOMA_VOLUME_MM3:
            next_id += 1
            keep[component] = next_id
    return keep, next_id


def _measure_myoma(
    component: np.ndarray,
    seg: np.ndarray,
    spacing: tuple[float, float, float],
    myoma_id: int,
) -> dict:
    voxel_vol = _voxel_volume_mm3(spacing)
    voxel_count = int(component.sum())
    volume_mm3 = voxel_count * voxel_vol

    # Bounding-box extents per axis, converted to mm.
    coords = np.argwhere(component)
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    extent_vox = (maxs - mins) + 1
    bbox_extent_mm = [float(extent_vox[i] * spacing[i]) for i in range(3)]

    equiv_diameter_mm = (6.0 * volume_mm3 / math.pi) ** (1.0 / 3.0)

    cavity = seg == LABEL_CAVITY
    exterior = seg == 0  # background outside the organ

    contacts_cavity = _contacts(component, cavity)
    contacts_serosa = _contacts(component, exterior)

    dist_cavity = 0.0 if contacts_cavity else _min_distance_mm(component, cavity, spacing)
    dist_serosa = 0.0 if contacts_serosa else _min_distance_mm(component, exterior, spacing)

    surface = component & ~ndimage.binary_erosion(component, _STRUCT_FACE)
    if not surface.any():
        surface = component  # thin component: whole thing is surface
    n_surface = int(surface.sum())

    wall = seg == LABEL_WALL
    dil_cavity = ndimage.binary_dilation(cavity, _STRUCT_FULL)
    dil_exterior = ndimage.binary_dilation(exterior, _STRUCT_FULL)
    dil_wall = ndimage.binary_dilation(wall, _STRUCT_FULL)

    surf_cavity = int((surface & dil_cavity).sum())
    surf_serosa = int((surface & dil_exterior).sum())
    # Buried surface: touches myometrium and neither the cavity nor the exterior.
    surf_intramural = int((surface & dil_wall & ~dil_cavity & ~dil_exterior).sum())

    def pct(part: int) -> float:
        return round(100.0 * part / n_surface, 1) if n_surface else 0.0

    return {
        "id": myoma_id,
        "voxel_count": voxel_count,
        "volume_mm3": round(volume_mm3, 1),
        "volume_ml": round(volume_mm3 / 1000.0, 2),
        "equivalent_diameter_mm": round(equiv_diameter_mm, 1),
        "bbox_extent_mm": [round(v, 1) for v in bbox_extent_mm],
        "max_diameter_mm": round(max(bbox_extent_mm), 1),
        "contacts_cavity": contacts_cavity,
        "distance_to_cavity_mm": None if dist_cavity is None else round(dist_cavity, 1),
        "contacts_serosa": contacts_serosa,
        "distance_to_serosa_mm": None if dist_serosa is None else round(dist_serosa, 1),
        "surface_voxels": n_surface,
        "cavity_surface_pct": pct(surf_cavity),
        "serosa_surface_pct": pct(surf_serosa),
        "intramural_pct": pct(surf_intramural),
    }


def _region_volumes_mm3(
    seg: np.ndarray, spacing: tuple[float, float, float]
) -> dict[str, float]:
    voxel_vol = _voxel_volume_mm3(spacing)
    return {
        "wall": round(int((seg == LABEL_WALL).sum()) * voxel_vol, 1),
        "cavity": round(int((seg == LABEL_CAVITY).sum()) * voxel_vol, 1),
        "myoma_total": round(int((seg == LABEL_MYOMA).sum()) * voxel_vol, 1),
        "nabothian": round(int((seg == LABEL_NABOTHIAN).sum()) * voxel_vol, 1),
    }


def measure_case(case: Case) -> dict:
    """Compute the structured measurement JSON for one case."""
    spacing = case.spacing_mm
    seg = case.seg

    labeled, count = label_myomas(seg, spacing)
    myomas = [
        _measure_myoma(labeled == mid, seg, spacing, mid)
        for mid in range(1, count + 1)
    ]
    # Report the largest myomas first; they usually drive the clinical picture.
    myomas.sort(key=lambda m: m["volume_mm3"], reverse=True)
    for new_id, myoma in enumerate(myomas, start=1):
        myoma["id"] = new_id

    present = sorted(int(v) for v in np.unique(seg))

    return {
        "case_id": case.case_id,
        "voxel_spacing_mm": [round(s, 4) for s in spacing],
        "voxel_volume_mm3": round(_voxel_volume_mm3(spacing), 4),
        "volume_shape": list(seg.shape),
        "labels_present": present,
        "region_volumes_mm3": _region_volumes_mm3(seg, spacing),
        "myoma_count": count,
        "myomas": myomas,
        "measurement_method": {
            "connectivity": "6 for labeling, 26 for contact tests",
            "distances": "anisotropic Euclidean transform in mm, 0.0 on contact",
            "intramural_pct": (
                "surface-adjacency proxy: share of myoma surface voxels buried "
                "in myometrium (touching wall, not cavity or exterior)"
            ),
            "min_myoma_volume_mm3": MIN_MYOMA_VOLUME_MM3,
        },
    }
