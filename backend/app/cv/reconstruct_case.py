"""Reconstruct one UMD case to a GLB and report per-region mesh stats.

Works on ground-truth masks (loaded here) or model predictions (any Case). The
GLB is written under data/ (gitignored).

Usage:
    python -m app.cv.reconstruct_case                 # UMD_221129_003
    python -m app.cv.reconstruct_case --case UMD_221129_045
"""

from __future__ import annotations

import argparse
from pathlib import Path

import trimesh

from .config import default_meshes_dir
from .reconstruct import build_scene, export_glb
from .umd_loader import load_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct a case to GLB (Phase 3).")
    parser.add_argument("--case", default="UMD_221129_003")
    parser.add_argument("--out-dir", type=Path, default=default_meshes_dir())
    parser.add_argument("--smooth-sigma", type=float, default=0.7)
    args = parser.parse_args()

    case = load_case(args.case)
    scene = build_scene(case, smooth_sigma=args.smooth_sigma)

    print(f"case {args.case}: {len(scene.geometry)} meshes")
    for name, geom in scene.geometry.items():
        print(f"  {name}: verts={len(geom.vertices)} faces={len(geom.faces)}")

    out_path = export_glb(scene, args.out_dir / f"{args.case}.glb")
    size_kb = out_path.stat().st_size / 1024.0
    print(f"\nwrote {out_path} ({size_kb:.1f} KB)")

    # Confirm the GLB loads back with the same named nodes.
    reloaded = trimesh.load(out_path)
    names = sorted(reloaded.geometry.keys())
    print(f"reloaded OK: {len(names)} meshes -> {names}")


if __name__ == "__main__":
    main()
