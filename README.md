# MyoMap

An open, image-based decision-support and patient-education tool for abnormal
uterine bleeding (AUB). Computer vision segments myomas (fibroids) in pelvic MRI,
a Claude agent classifies them by FIGO / PALM-COEIN from a structured rules file,
produces a structured clinical report plus a patient-friendly explanation, and a
3D view shows the location. The tool self-verifies against open ground-truth data.

Concept, background, and build plan: see [CONCEPT_AND_PLAN.md](CONCEPT_AND_PLAN.md).

This is decision support with a human in the loop, not an approved medical device.

## Repo structure

```
backend/
  app/
    main.py            FastAPI entry point, endpoints
    cv/                loader, measurements, segmentation, mesh generation
    agent/             Claude agent logic and tools
    rules/             figo_palm_coein.json (the rules file)
    verification/      held-out eval: Dice + FIGO agreement
  requirements.txt
frontend/
  src/
    components/
    viewer/            three.js 3D view
    report/            report and patient-explanation panels
data/                  derived artifacts (gitignored); the dataset lives outside the repo
```

## Setup

This project is bring-your-own-key. Whoever clones it sets their own
`ANTHROPIC_API_KEY` and pays for their own API usage.

### Backend

```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then fill .env with your real key
uvicorn app.main:app --reload
```

Health check: http://localhost:8000/health

### Frontend

```
cd frontend
npm install
npm run dev
```

Dev server: http://localhost:5173

## Dataset

UMD (Uterine Myoma MRI Dataset), Scientific Data 2024,
DOI 10.1038/s41597-024-03170-x. 300 cases of sagittal T2WI pelvic MRI with
pixel-level masks for four regions. Obtain it via the paper's "Data Availability"
section and respect its license and access terms.

The dataset lives outside the repo and is never copied into it. Point the code at
it with the `UMD_DATA_DIR` environment variable (a local default is used when the
variable is unset). Each case is a folder such as `UMD_221129_001` containing
`<case>_t2.nii.gz` (T2WI volume) and `<case>_seg.nii.gz` (mask). The per-slice
`.dcm` files are ignored. Mask labels: `1` uterine wall, `2` uterine cavity,
`3` myoma, `4` nabothian cyst. Voxel spacing is read from the NIfTI header.

## Phase 1: loader and measurements

The `backend/app/cv` package loads a case, computes per-myoma geometry (size,
contact with the uterine cavity and the serosa, and an intramural percentage),
and writes a structured JSON plus a PNG overlay of one slice for inspection.

```
cd backend
source .venv/bin/activate
python -m app.cv.run_case                    # first case in the dataset
python -m app.cv.run_case --case UMD_221129_003
UMD_DATA_DIR=/path/to/UMD python -m app.cv.run_case --case UMD_221129_003
```

Outputs are written under `data/phase1/` (gitignored).

## Phase 2: segmentation model

A 2D U-Net predicts the four regions from the T2 volume. Training operates on
native sagittal slices (the acquisition plane, full in-plane resolution), so no
resampling crosses the thick slice direction. The train/val split is deterministic
(seed 42, 80/20) and persisted to `data/splits.json`. Weights and the split live
under `data/` (gitignored). The inference output matches the Phase 1 mask
structure, so `measure_case` runs on predictions unchanged.

Each epoch logs mean train loss and per-class validation Dice (wall, cavity,
myoma, nabothian) computed by full-volume inference on the val split, uses a
cosine learning-rate schedule, mixes a share of background slices so the model
does not overpredict, and keeps the best checkpoint by mean foreground val Dice
(`<name>_best.pt`) alongside the last one.

```
cd backend
source .venv/bin/activate

# Smoke test: a few iterations on a handful of cases (CPU), end to end.
python -m app.cv.train --limit-cases 4 --max-iters 3 --size 128 \
    --base-channels 8 --batch-size 2 --device cpu --out data/models/unet_smoke.pt

# Real run (uses CUDA or Apple MPS automatically when available).
python -m app.cv.train --epochs 50 --size 256 --base-channels 32
```

Inference returns a `Case` carrying the predicted mask:

```python
from app.cv.inference import predict_case
from app.cv.measurements import measure_case

case = predict_case("UMD_221129_002", "data/models/unet.pt")
report = measure_case(case)
```
