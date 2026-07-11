"""Run the Phase 1 pipeline on one UMD case.

Loads the case, computes the measurement JSON, writes it next to a PNG overlay
of one slice, and prints the JSON. Derived artifacts go under data/ (gitignored)
by default, so nothing from the dataset is copied into tracked files.

Usage:
    python -m app.cv.run_case                 # first case in the dataset
    python -m app.cv.run_case --case UMD_221129_003
    python -m app.cv.run_case --case UMD_221129_003 --out-dir /tmp/out
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import default_output_dir
from .measurements import measure_case
from .overlay import save_overlay_png
from .umd_loader import list_cases, load_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure one UMD case (Phase 1).")
    parser.add_argument("--case", help="Case id, e.g. UMD_221129_003.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=default_output_dir(),
        help="Directory for the JSON and PNG outputs.",
    )
    parser.add_argument(
        "--no-png", action="store_true", help="Skip writing the overlay PNG."
    )
    args = parser.parse_args()

    case_id = args.case or list_cases()[0]
    case = load_case(case_id)

    result = measure_case(case)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{case_id}.json"
    json_path.write_text(json.dumps(result, indent=2))

    print(json.dumps(result, indent=2))
    print(f"\nwrote {json_path}")

    if not args.no_png:
        png_path = save_overlay_png(case, out_dir / f"{case_id}_overlay.png")
        print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
