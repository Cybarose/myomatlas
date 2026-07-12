"""3D reconstruction of a case mask into a GLB scene.

Each region becomes a surface mesh through marching cubes, with three things done to it:

Orientation. Vertices are placed with the image affine, so every case lands in the same
anatomical frame (superior up, anterior toward the camera) instead of in raw voxel axes,
which had all 300 cases sitting upside down. The image affine is used, not the mask
affine, because a number of the mask headers in this dataset are malformed.

Smoothing. The 6.6 mm slices leave a staircase whose wavelength is the slice pitch, so
the surface is resampled onto an isotropic grid, blurred against that pitch, and relaxed
with Taubin. Blurring that hard would normally erode the small myomas away, so the
isolevel is not left at the usual 0.5 but solved for the volume the segmentation actually
measured. That decouples how smooth the mesh looks from how faithful it is, and it also
repairs the bite marching cubes takes out of every convex corner.

Specks. The segmentation leaves floating fragments, so only the largest connected piece
of each region survives, ranked by enclosed volume.

Wall, cavity and every individual myoma stay separate named meshes so the frontend can
color, label and toggle them. This works on any integer label volume, so it is identical
for ground-truth masks and model predictions (both arrive as a Case).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage
from skimage.measure import marching_cubes
from trimesh.smoothing import filter_taubin
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

# Meshing happens on an isotropic millimeter grid, not on the raw voxels. The
# acquisition is 0.45 mm in plane and 6.6 mm across slices, so a mesh built straight
# from the voxels has a wildly uneven vertex density: smoothing then just averages
# within a slice and never flattens the terraces between them. Resampling first is what
# makes the smoothing work at all.
_ISO_MM = 1.0
_MIN_ISO_MM = 0.35
_MARGIN_MM = 4.0

# The staircase is not local roughness, it is a ripple whose wavelength is the slice
# pitch, so the blur has to be sized against that pitch rather than against the voxel.
# A gaussian damps a ripple of wavelength L by exp(-2 pi^2 sigma^2 / L^2): at 0.15 of the
# pitch the terraces survive almost untouched, at 0.6 they are gone. Blurring this hard
# would normally eat the small myomas, but the isolevel below is solved for the segmented
# volume, so smoothing strength no longer trades against volume fidelity.
_SMOOTH_SLICE_FRACTION = 0.6

# Never blur a region by more than its own inscribed radius, so a small myoma stays a
# myoma and the thin cavity stripe survives.
_MAX_SMOOTH_THICKNESS_FRACTION = 1.0

# A disconnected piece smaller than this share of the main body is segmentation noise
# rather than anatomy. See _clean_mask for why the line sits where it does.
_KEEP_COMPONENT_FRACTION = 0.30

# Taubin alternates a shrinking and an inflating pass, so the surface relaxes without
# the volume collapsing the way plain Laplacian smoothing would.
_TAUBIN_LAMB = 0.5
_TAUBIN_NU = 0.53
_TAUBIN_ITERATIONS = 15

# Bisection bounds for the isolevel that reproduces the segmented volume.
_LEVEL_LO = 0.02
_LEVEL_HI = 0.98
_LEVEL_STEPS = 8

# The image affine maps voxel indices to RAS millimeters (x right, y anterior,
# z superior). This puts superior up and anterior toward the camera, and keeps the
# frame right handed so face winding survives.
_RAS_TO_SCENE = np.array(
    [
        [-1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 1.0, 0.0],
    ]
)


def _world_transform(affine: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Linear part and offset mapping voxel indices to scene millimeters."""
    linear = _RAS_TO_SCENE @ affine[:3, :3]
    offset = _RAS_TO_SCENE @ affine[:3, 3]
    return linear, offset


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    """Drop the segmentation's floating fragments, keep the real structure.

    Pruning the mask rather than the finished mesh is what makes this safe: the isolevel
    below is solved against this mask's volume, so a fragment dropped after meshing would
    be silently pushed back into whatever survived, inflating and displacing it.

    Pieces are judged against the main body rather than by an absolute size. A wall can
    carry a ten milliliter blob fifty millimeters away that is still only a tenth of the
    myometrium, which is noise, while a thin cavity stripe breaks into pieces that are
    two thirds of each other, which is one real endometrium the segmentation cut apart.
    """
    labels, count = ndimage.label(mask)
    if count <= 1:
        return mask

    sizes = np.bincount(labels.ravel())[1:]
    keep = np.flatnonzero(sizes >= _KEEP_COMPONENT_FRACTION * sizes.max()) + 1
    return np.isin(labels, keep)


def _thickness_mm(mask: np.ndarray, spacing: tuple[float, float, float]) -> float:
    """Radius of the largest sphere that fits inside the region.

    This is how thick the structure actually is, which a same-volume sphere radius badly
    overstates for anything elongated. It keeps the thin cavity stripe from being blurred
    as hard as a solid myoma of the same volume.
    """
    return float(ndimage.distance_transform_edt(mask, sampling=spacing).max())


def _mesh_at_level(
    field: np.ndarray,
    level: float,
    origin: np.ndarray,
    step: np.ndarray,
    linear: np.ndarray,
    offset: np.ndarray,
) -> trimesh.Trimesh | None:
    """Extract, place and smooth the isosurface of the occupancy field at one level."""
    try:
        verts, faces, _normals, _values = marching_cubes(field, level=level)
    except (ValueError, RuntimeError):
        return None
    if len(faces) == 0:
        return None

    verts = origin + verts * step  # isotropic index back to voxel index
    verts = verts @ linear.T + offset  # voxel index to scene millimeters

    # Marching cubes winds faces so the normals point into the object, so reverse them.
    # A mirroring affine (negative determinant) reverses the winding again, which cancels.
    if np.linalg.det(linear) > 0:
        faces = faces[:, ::-1]

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    filter_taubin(mesh, lamb=_TAUBIN_LAMB, nu=_TAUBIN_NU, iterations=_TAUBIN_ITERATIONS)
    return mesh


def _region_mesh(
    mask: np.ndarray,
    spacing: tuple[float, float, float],
    linear: np.ndarray,
    offset: np.ndarray,
    smooth_mm: float,
) -> trimesh.Trimesh | None:
    """Smoothed, speck-free surface for one binary region, in scene millimeters."""
    if int(mask.sum()) < _MIN_MESH_VOXELS:
        return None

    spacing_mm = np.asarray(spacing, dtype=np.float64)
    mask = _clean_mask(mask)

    # Crop before the distance pass, which is the expensive one, and give the crop enough
    # room for the blur: the kernel must not reach the border and bite into the region from
    # outside. smooth_mm bounds the blur, so the margin can be fixed before it is sized.
    margin_mm = max(_MARGIN_MM, 3.0 * smooth_mm)
    coords = np.argwhere(mask)
    margin = np.ceil(margin_mm / spacing_mm).astype(int)
    lo = np.maximum(coords.min(axis=0) - margin, 0)
    hi = np.minimum(coords.max(axis=0) + margin + 1, np.array(mask.shape))
    region = mask[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]

    # A myoma can be a thousand times smaller than the wall, so the grid and the blur are
    # sized to the region as well as to the slice pitch.
    thickness = _thickness_mm(region, spacing)
    iso_mm = float(np.clip(thickness / 3.0, _MIN_ISO_MM, _ISO_MM))
    sigma_mm = min(smooth_mm, thickness * _MAX_SMOOTH_THICKNESS_FRACTION)

    sub = np.pad(region.astype(np.float32), 2, mode="constant")  # blank border, closes it
    origin = lo.astype(np.float64) - 2.0

    shape = np.array(sub.shape)
    counts = np.maximum(np.ceil((shape - 1) * spacing_mm / iso_mm).astype(int) + 1, 2)
    axes = [np.linspace(0.0, shape[i] - 1.0, counts[i]) for i in range(3)]
    step = np.array([(shape[i] - 1.0) / (counts[i] - 1) for i in range(3)])

    grid = np.meshgrid(*axes, indexing="ij")
    field = ndimage.map_coordinates(sub, grid, order=1, mode="constant", cval=0.0)
    if sigma_mm > 0:
        field = ndimage.gaussian_filter(
            field, sigma=sigma_mm / iso_mm, mode="constant", cval=0.0
        )

    # Meshing occupancy at the usual level 0.5 shaves a systematic slice off every convex
    # corner: a lone voxel comes out as an octahedron holding a sixth of its volume, and
    # the blur deepens the bite on the smallest myomas. Instead of accepting that loss, the
    # level is solved for, so the surface encloses the volume the segmentation actually
    # measured. Enclosed volume falls monotonically with the level, so bisection is enough.
    target_mm3 = float(mask.sum()) * float(np.prod(spacing_mm))
    low = max(_LEVEL_LO, float(field.min()) + 1e-3)
    high = min(_LEVEL_HI, float(field.max()) - 1e-3)
    if high <= low:
        return None

    best: trimesh.Trimesh | None = None
    best_error = np.inf
    for _ in range(_LEVEL_STEPS):
        level = 0.5 * (low + high)
        mesh = _mesh_at_level(field, level, origin, step, linear, offset)
        if mesh is None:
            high = level  # nothing survives this high, look lower
            continue

        volume_mm3 = abs(float(mesh.volume))
        error = abs(volume_mm3 - target_mm3)
        if error < best_error:
            best, best_error = mesh, error

        if volume_mm3 > target_mm3:
            low = level
        else:
            high = level

    return best


def _paint(mesh: trimesh.Trimesh, name: str, rgba: tuple[float, float, float, float]) -> None:
    blend = rgba[3] < 1.0
    mesh.visual = trimesh.visual.TextureVisuals(
        material=PBRMaterial(
            name=f"{name}_mat",
            baseColorFactor=[rgba[0], rgba[1], rgba[2], rgba[3]],
            alphaMode="BLEND" if blend else "OPAQUE",
            doubleSided=True,
        )
    )


def build_scene(case: Case, smooth_mm: float | None = None) -> trimesh.Scene:
    """Build a centered trimesh Scene with named meshes per region and myoma.

    smooth_mm defaults to a fraction of this case's own slice pitch, which is what sets
    the staircase, so a thicker acquisition is smoothed harder.
    """
    seg = case.seg
    spacing = case.spacing_mm
    if smooth_mm is None:
        smooth_mm = _SMOOTH_SLICE_FRACTION * float(np.max(spacing))
    linear, offset = _world_transform(case.affine)

    named: list[tuple[str, trimesh.Trimesh]] = []

    wall = _region_mesh(seg == LABEL_WALL, spacing, linear, offset, smooth_mm)
    if wall is not None:
        named.append(("wall", wall))

    cavity = _region_mesh(seg == LABEL_CAVITY, spacing, linear, offset, smooth_mm)
    if cavity is not None:
        named.append(("cavity", cavity))

    # Largest first, so the ids match the measurement ids.
    for i, component in enumerate(myoma_components_by_volume(seg, spacing), start=1):
        mesh = _region_mesh(component, spacing, linear, offset, smooth_mm)
        if mesh is not None:
            named.append((f"myoma_{i}", mesh))

    if not named:
        return trimesh.Scene()

    # Center the shared coordinate frame on the combined bounding box.
    all_verts = np.concatenate([mesh.vertices for _, mesh in named], axis=0)
    center = (all_verts.min(axis=0) + all_verts.max(axis=0)) / 2.0

    scene = trimesh.Scene()
    myoma_i = 0
    for name, mesh in named:
        if name.startswith("myoma_"):
            rgba = _MYOMA_PALETTE[myoma_i % len(_MYOMA_PALETTE)]
            myoma_i += 1
        elif name == "wall":
            rgba = _WALL_RGBA
        else:
            rgba = _CAVITY_RGBA

        mesh.vertices = mesh.vertices - center
        _paint(mesh, name, rgba)
        scene.add_geometry(mesh, node_name=name, geom_name=name)

    return scene


def export_glb(scene: trimesh.Scene, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(scene.export(file_type="glb"))
    return out_path


def reconstruct_case_to_glb(
    case: Case, out_path: Path, smooth_mm: float | None = None
) -> Path:
    """Reconstruct a case and write a single GLB with named region/myoma nodes."""
    scene = build_scene(case, smooth_mm=smooth_mm)
    return export_glb(scene, out_path)
