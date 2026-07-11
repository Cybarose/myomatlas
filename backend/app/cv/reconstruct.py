"""3D reconstruction of a case mask into a GLB scene.

Marching cubes turns each region into a surface mesh, with the anisotropic voxel
spacing applied so proportions are anatomically true. Wall, cavity, and every
individual myoma become separate named meshes so the frontend can color, label,
and toggle them independently. The whole scene is centered at the origin so it
loads nicely in three.js.

This works on any integer label volume, so it is identical for ground-truth masks
and model predictions (both arrive as a Case).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage
from skimage.measure import marching_cubes
from trimesh.visual.material import PBRMaterial

from .config import LABEL_CAVITY, LABEL_WALL
from .measurements import myoma_components_by_volume
from .umd_loader import Case

# RGBA base colors and blend mode per region type. Myomas cycle a palette so each
# is visually distinct until the frontend recolors them by FIGO type.
_WALL_RGBA = (0.60, 0.63, 0.68, 0.25)
_CAVITY_RGBA = (0.20, 0.75, 0.45, 0.55)
_MYOMA_PALETTE = [
    (0.90, 0.30, 0.30, 1.0),
    (0.95, 0.60, 0.20, 1.0),
    (0.55, 0.35, 0.85, 1.0),
    (0.20, 0.55, 0.95, 1.0),
    (0.85, 0.30, 0.65, 1.0),
    (0.30, 0.70, 0.70, 1.0),
]

# Components below this voxel count are too small to mesh meaningfully.
_MIN_MESH_VOXELS = 8


def _region_surface(
    mask: np.ndarray,
    spacing: tuple[float, float, float],
    smooth_sigma: float,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Marching-cubes vertices (in mm) and faces for one binary region, or None."""
    if int(mask.sum()) < _MIN_MESH_VOXELS:
        return None
    # Pad so surfaces touching the array border still close.
    volume = np.pad(mask.astype(np.float32), 1, mode="constant")
    if smooth_sigma > 0:
        volume = ndimage.gaussian_filter(volume, sigma=smooth_sigma)
    if volume.max() < 0.5:
        return None
    verts, faces, _normals, _values = marching_cubes(volume, level=0.5, spacing=spacing)
    # Undo the one-voxel pad offset so all regions share one coordinate frame.
    verts = verts - np.asarray(spacing, dtype=np.float64)
    return verts, faces


def _make_mesh(
    verts: np.ndarray, faces: np.ndarray, name: str, rgba: tuple[float, float, float, float]
) -> trimesh.Trimesh:
    blend = rgba[3] < 1.0
    material = PBRMaterial(
        name=f"{name}_mat",
        baseColorFactor=[rgba[0], rgba[1], rgba[2], rgba[3]],
        alphaMode="BLEND" if blend else "OPAQUE",
        doubleSided=True,
    )
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=material)
    return mesh


def build_scene(case: Case, smooth_sigma: float = 0.7) -> trimesh.Scene:
    """Build a centered trimesh Scene with named meshes per region and myoma."""
    spacing = case.spacing_mm
    seg = case.seg

    named: list[tuple[str, np.ndarray, np.ndarray]] = []

    wall = _region_surface(seg == LABEL_WALL, spacing, smooth_sigma)
    if wall is not None:
        named.append(("wall", wall[0], wall[1]))

    cavity = _region_surface(seg == LABEL_CAVITY, spacing, smooth_sigma)
    if cavity is not None:
        named.append(("cavity", cavity[0], cavity[1]))

    for i, component in enumerate(myoma_components_by_volume(seg, spacing), start=1):
        surface = _region_surface(component, spacing, smooth_sigma)
        if surface is not None:
            named.append((f"myoma_{i}", surface[0], surface[1]))

    if not named:
        return trimesh.Scene()

    # Center the shared coordinate frame on the combined bounding box.
    all_verts = np.concatenate([verts for _, verts, _ in named], axis=0)
    center = (all_verts.min(axis=0) + all_verts.max(axis=0)) / 2.0

    scene = trimesh.Scene()
    myoma_i = 0
    for name, verts, faces in named:
        if name.startswith("myoma_"):
            rgba = _MYOMA_PALETTE[myoma_i % len(_MYOMA_PALETTE)]
            myoma_i += 1
        elif name == "wall":
            rgba = _WALL_RGBA
        else:
            rgba = _CAVITY_RGBA
        mesh = _make_mesh(verts - center, faces, name, rgba)
        scene.add_geometry(mesh, node_name=name, geom_name=name)

    return scene


def export_glb(scene: trimesh.Scene, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(scene.export(file_type="glb"))
    return out_path


def reconstruct_case_to_glb(
    case: Case, out_path: Path, smooth_sigma: float = 0.7
) -> Path:
    """Reconstruct a case and write a single GLB with named region/myoma nodes."""
    scene = build_scene(case, smooth_sigma=smooth_sigma)
    return export_glb(scene, out_path)
