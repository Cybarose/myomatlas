"""Train the 2D U-Net on UMD sagittal slices.

Each epoch logs mean train loss and per-class validation Dice (wall, cavity,
myoma, nabothian), computed by full-volume inference on the val split. The best
checkpoint by mean foreground val Dice is kept alongside the last one. Runs on
CPU and uses CUDA or Apple MPS automatically. Weights are saved under data/
(gitignored).

Examples:
    python -m app.cv.train --limit-cases 4 --max-iters 3 --size 128 \
        --base-channels 8 --device cpu --out data/models/unet_smoke.pt
    python -m app.cv.train --epochs 50 --size 256 --base-channels 32
"""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch.utils.data import DataLoader

from .config import default_models_dir
from .dataset import DEFAULT_SIZE, NUM_CLASSES, UMDSliceDataset
from .device import host_peak_rss_bytes, mps_allocated_bytes, pick_device
from .inference import predict_volume
from .losses import DiceCELoss
from .metrics import dice_from_counts, overlap_counts
from .splits import DEFAULT_SEED, DEFAULT_VAL_FRACTION, load_or_make_split
from .umd_loader import load_case
from .unet import UNet

# Foreground class order for logging (background is class 0).
FOREGROUND_NAMES = ["wall", "cavity", "myoma", "nabothian"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the UMD segmentation U-Net.")
    p.add_argument("--split", type=Path, default=None, help="Path to splits.json.")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--val-fraction", type=float, default=DEFAULT_VAL_FRACTION)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--max-iters", type=int, default=0, help="Cap optimizer steps (0 = no cap).")
    p.add_argument("--limit-cases", type=int, default=0, help="Use only N train cases (0 = all).")
    p.add_argument("--limit-val-cases", type=int, default=0, help="Use only N val cases (0 = all).")
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--lr-schedule", choices=["cosine", "step", "none"], default="cosine")
    p.add_argument("--size", type=int, default=DEFAULT_SIZE)
    p.add_argument("--base-channels", type=int, default=32)
    p.add_argument("--background-fraction", type=float, default=0.3)
    p.add_argument("--foreground-only", action="store_true", help="Train on labeled slices only.")
    p.add_argument("--cache-size", type=int, default=16)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--augment", action="store_true")
    p.add_argument("--device", default="auto", help="auto | cpu | cuda | mps")
    p.add_argument("--out", type=Path, default=None, help="Checkpoint output path (last).")
    p.add_argument("--log-every", type=int, default=20)
    return p.parse_args()


def build_scheduler(
    optimizer: torch.optim.Optimizer, name: str, epochs: int
) -> torch.optim.lr_scheduler._LRScheduler | None:
    if name == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(epochs, 1))
    if name == "step":
        return torch.optim.lr_scheduler.StepLR(
            optimizer, step_size=max(epochs // 3, 1), gamma=0.5
        )
    return None


@torch.no_grad()
def evaluate(
    model: UNet,
    val_ids: list[str],
    config: dict,
    device: torch.device,
    num_classes: int,
    limit: int = 0,
) -> np.ndarray:
    """Per-class micro-averaged Dice over the val split by full-volume inference."""
    model.eval()
    ids = val_ids[:limit] if limit else val_ids
    inter = np.zeros(num_classes, dtype=np.float64)
    card = np.zeros(num_classes, dtype=np.float64)
    for case_id in ids:
        case = load_case(case_id)
        pred = predict_volume(model, case.image, config, device)
        i, c = overlap_counts(pred, case.seg, num_classes)
        inter += i
        card += c
    model.train()
    return dice_from_counts(inter, card)


def _format_dice(dice: np.ndarray) -> str:
    return " ".join(f"{n}={dice[k + 1]:.3f}" for k, n in enumerate(FOREGROUND_NAMES))


def save_checkpoint(path: Path, model: UNet, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "config": config}, path)


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
    val_ids = split["val"]
    n_eval = args.limit_val_cases if args.limit_val_cases else len(val_ids)
    print(f"train cases: {len(train_ids)} (of {split['n_train']}) | val cases: {n_eval} (of {len(val_ids)})")

    train_ds = UMDSliceDataset(
        train_ids,
        size=args.size,
        foreground_only=args.foreground_only,
        background_fraction=args.background_fraction,
        augment=args.augment,
        cache_size=args.cache_size,
        seed=args.seed,
    )
    print(f"train slices: {len(train_ds)}")
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers
    )

    model = UNet(in_channels=1, num_classes=NUM_CLASSES, base_channels=args.base_channels).to(device)
    loss_fn = DiceCELoss(NUM_CLASSES)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = build_scheduler(optimizer, args.lr_schedule, args.epochs)

    config = {
        "in_channels": 1,
        "num_classes": NUM_CLASSES,
        "base_channels": args.base_channels,
        "size": args.size,
        "normalization": "per_volume_percentile_99.5",
        "orientation": "sagittal_slices_axis2",
    }
    out_path = args.out or (default_models_dir() / "unet.pt")
    best_path = out_path.parent / f"{out_path.stem}_best{out_path.suffix}"

    step = 0
    peak_mps = 0
    best_mean_fg = -1.0
    stop = False
    for epoch in range(args.epochs):
        model.train()
        t_train = perf_counter()
        running = 0.0
        n_batches = 0
        for images, masks in train_loader:
            images = images.to(device)
            masks = masks.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = loss_fn(logits, masks)
            loss.backward()
            optimizer.step()
            step += 1
            running += loss.item()
            n_batches += 1
            peak_mps = max(peak_mps, mps_allocated_bytes())
            if step % args.log_every == 0:
                print(f"  epoch {epoch} step {step} loss {loss.item():.4f}")
            if args.max_iters and step >= args.max_iters:
                stop = True
                break
        train_time = perf_counter() - t_train
        train_loss = running / max(n_batches, 1)

        t_val = perf_counter()
        dice = evaluate(model, val_ids, config, device, NUM_CLASSES, limit=args.limit_val_cases)
        val_time = perf_counter() - t_val
        mean_fg = float(np.nanmean(dice[1:]))

        print(
            f"epoch {epoch}: train_loss {train_loss:.4f} | val_dice {_format_dice(dice)} "
            f"mean_fg {mean_fg:.3f} | train {train_time:.1f}s val {val_time:.1f}s"
        )

        if scheduler is not None:
            scheduler.step()

        if mean_fg > best_mean_fg:
            best_mean_fg = mean_fg
            save_checkpoint(best_path, model, config)
            print(f"  new best mean_fg {mean_fg:.3f} -> {best_path}")

        if stop:
            break

    save_checkpoint(out_path, model, config)
    print(f"saved last checkpoint: {out_path}  (steps trained: {step})")
    print(f"best mean_fg val dice: {best_mean_fg:.3f}  ({best_path})")
    if peak_mps > 0:
        print(f"peak MPS allocated: {peak_mps / 1e9:.2f} GB")
    print(f"peak host RSS: {host_peak_rss_bytes() / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
