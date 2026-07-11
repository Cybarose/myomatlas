"""Train the 2D U-Net on UMD sagittal slices.

Runs on CPU by default sizing (small model, few cases) and uses CUDA or Apple
MPS automatically when available. A smoke run limits cases and optimizer steps to
check the full loop end to end. Weights are saved under data/ (gitignored).

Examples:
    python -m app.cv.train --limit-cases 4 --max-iters 3 --size 128 \
        --base-channels 8 --device cpu --out data/models/unet_smoke.pt
    python -m app.cv.train --epochs 50 --size 256 --base-channels 32
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .config import default_models_dir
from .dataset import DEFAULT_SIZE, NUM_CLASSES, UMDSliceDataset
from .device import pick_device
from .losses import DiceCELoss
from .splits import DEFAULT_SEED, DEFAULT_VAL_FRACTION, load_or_make_split
from .unet import UNet


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the UMD segmentation U-Net.")
    p.add_argument("--split", type=Path, default=None, help="Path to splits.json.")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--val-fraction", type=float, default=DEFAULT_VAL_FRACTION)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--max-iters", type=int, default=0, help="Cap optimizer steps (0 = no cap).")
    p.add_argument("--limit-cases", type=int, default=0, help="Use only N train cases (0 = all).")
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--size", type=int, default=DEFAULT_SIZE)
    p.add_argument("--base-channels", type=int, default=32)
    p.add_argument("--cache-size", type=int, default=16)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--augment", action="store_true")
    p.add_argument("--foreground-only", action="store_true", default=True)
    p.add_argument("--device", default="auto", help="auto | cpu | cuda | mps")
    p.add_argument("--out", type=Path, default=None, help="Checkpoint output path.")
    p.add_argument("--log-every", type=int, default=10)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    device = pick_device(args.device)
    print(f"device: {device}")

    split = load_or_make_split(
        seed=args.seed, val_fraction=args.val_fraction, path=args.split
    )
    train_ids = split["train"]
    if args.limit_cases > 0:
        train_ids = train_ids[: args.limit_cases]
    print(f"train cases: {len(train_ids)} (of {split['n_train']})")

    train_ds = UMDSliceDataset(
        train_ids,
        size=args.size,
        foreground_only=args.foreground_only,
        augment=args.augment,
        cache_size=args.cache_size,
        root=None,
        seed=args.seed,
    )
    print(f"train slices: {len(train_ds)}")
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers
    )

    model = UNet(in_channels=1, num_classes=NUM_CLASSES, base_channels=args.base_channels).to(device)
    loss_fn = DiceCELoss(NUM_CLASSES)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    model.train()
    step = 0
    stop = False
    for epoch in range(args.epochs):
        for images, masks in train_loader:
            images = images.to(device)
            masks = masks.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = loss_fn(logits, masks)
            loss.backward()
            optimizer.step()
            step += 1
            if step % args.log_every == 0 or step == 1:
                print(f"epoch {epoch} step {step} loss {loss.item():.4f}")
            if args.max_iters and step >= args.max_iters:
                stop = True
                break
        if stop:
            break

    out_path = args.out or (default_models_dir() / "unet.pt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "in_channels": 1,
        "num_classes": NUM_CLASSES,
        "base_channels": args.base_channels,
        "size": args.size,
        "normalization": "per_volume_percentile_99.5",
        "orientation": "sagittal_slices_axis2",
    }
    torch.save({"model_state": model.state_dict(), "config": config}, out_path)
    print(f"saved checkpoint: {out_path}  (steps trained: {step})")


if __name__ == "__main__":
    main()
