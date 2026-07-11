"""One-time slice pre-extraction for fast, I/O-cheap training.

Writes resized train (and val) slices to data/slices/<size>/ so a real run reads
small per-slice files with DataLoader workers instead of decoding NIfTI volumes
every step. Re-run per target size. Output lives under data/ (gitignored).

Example:
    python -m app.cv.preprocess --size 256
    python -m app.cv.train --use-preextracted --size 256 --workers 4 ...
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import default_slices_dir
from .dataset import extract_slices
from .splits import DEFAULT_SEED, DEFAULT_VAL_FRACTION, load_or_make_split


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pre-extract UMD slices to disk.")
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--split", type=Path, default=None, help="Path to splits.json.")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--val-fraction", type=float, default=DEFAULT_VAL_FRACTION)
    p.add_argument("--out", type=Path, default=None, help="Slice store dir.")
    p.add_argument("--train-only", action="store_true", help="Skip val extraction.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    split = load_or_make_split(
        seed=args.seed, val_fraction=args.val_fraction, path=args.split
    )
    out_dir = args.out or default_slices_dir(args.size)

    n_train = extract_slices(split["train"], args.size, out_dir, "train")
    print(f"train: {n_train} slices -> {out_dir}")
    if not args.train_only:
        n_val = extract_slices(split["val"], args.size, out_dir, "val")
        print(f"val: {n_val} slices -> {out_dir}")


if __name__ == "__main__":
    main()
