# Myomatlas

Open, image-based decision support for abnormal uterine bleeding.

Myomatlas turns a pelvic MRI into a structured, guideline-based reading of uterine
fibroids. Computer vision segments each fibroid, a Claude agent classifies it by the
FIGO and PALM-COEIN systems from an encoded guideline, and the tool produces a
structured clinical report, a plain-language patient explanation, and an interactive
3D view. The analysis adapts to patient context such as age, menopausal status and
fertility desire.

This is decision support, not a diagnosis. A clinician makes the final decision.

Built for the Built with Claude: Life Sciences hackathon (Anthropic and Cerebral Valley,
in partnership with Gladstone Institutes).

## Demo

Watch the demo video: https://youtu.be/LOoYQ1xTpTA?si=1nQa9fMtH0KfOnne

<img width="1271" height="794" alt="Bildschirmfoto 2026-07-13 um 15 53 56" src="https://github.com/user-attachments/assets/031ee87a-bf6c-4971-8264-75167f89cd93" />


## The problem

Heavy or abnormal uterine bleeding affects a large share of women, is a leading cause
of iron-deficiency anemia, and is often normalized or under-investigated. When fibroids
are the cause, their location (the FIGO type) drives the right treatment, but this is
reported inconsistently and rarely explained to the patient in an understandable way.
The location also determines fertility impact and whether a uterus-preserving option
is possible. Myomatlas makes this location-to-options-to-fertility logic explicit and
understandable.

## What it does

- Computer vision (a 2D U-Net trained on the open UMD dataset) segments the uterine
  wall, cavity and each fibroid from the MRI, and measures size, count and location
  relative to the cavity and serosa.
- A Claude agent reasons strictly from an encoded FIGO / PALM-COEIN rules file to
  assign a FIGO type per fibroid with a shown justification, place the case in
  PALM-COEIN, flag when malignancy exclusion is warranted, and derive management
  options including uterus- and fertility-preserving ones. It flags provisional cases
  honestly where a fine threshold or pedunculation cannot be resolved from the masks.
- A patient intake form (age, menopausal status, bleeding severity, fertility desire,
  risk factors) makes the analysis context-aware: the malignancy assessment and the
  ordering of management options change with the patient.
- An interactive 3D workspace shows the uterus with color-coded fibroids, connector
  lines to per-fibroid cards, a per-fibroid mini 3D view, a structured clinical report,
  a plain-language patient explanation, and a PDF export of the full report.
- Self-verification: the segmentation is evaluated against the open ground-truth masks,
  and the FIGO reasoning is checked against the dataset labels, so the tool reports
  measured accuracy rather than claims.

See the difference the patient context makes: the same scan produces two different
reports depending on the patient. Example PDF exports are in the reports folder

## Data

- UMD dataset (Uterine Myoma MRI Dataset), Pan et al., Scientific Data 11, 410 (2024),
  DOI 10.1038/s41597-024-03170-x. 300 T2WI sagittal pelvic MRI cases with pixel-level
  annotations for uterine wall, cavity, myoma and nabothian cyst, covering all nine
  FIGO types. Openly available under CC-BY-4.0 on Figshare
  (https://doi.org/10.6084/m9.figshare.23541312.v3).
- The dataset is myoma-focused: cases with adenomyosis, malignancy and pregnancy were
  excluded by the authors. The CV therefore covers the leiomyoma (L) branch of
  PALM-COEIN from imaging, and the agent reasons about the remaining categories from the
  clinical intake.

## Guideline sources

The rules file encodes:
- FIGO leiomyoma subclassification, Munro et al. 2011 (and the 2018 revision).
- ACOG Practice Bulletin No. 228, Management of Symptomatic Uterine Leiomyomas (2021).
- NICE NG88 where relevant.
The FIGO type definitions and citations were checked against these primary sources.

## Architecture

- Backend: Python, FastAPI. CV with PyTorch (segmentation, measurements, marching-cubes
  mesh reconstruction). The Claude agent uses the Anthropic API and reasons from
  backend/app/rules/figo_palm_coein.json.
- Frontend: React, Vite, TypeScript, Tailwind, three.js for the 3D workspace.

## Running it

Requirements: the UMD dataset on disk, an Anthropic API key, Python and Node.

1. Get the data. Download UMD.zip from the Figshare link above and unzip it. Note the
   path to the folder that contains the case folders (for example
   /path/to/umd-data/UMD).

2. Set the API key. Copy the example env file and add your key. The key is only read
   locally and is never committed.
   ```
   cp .env.example .env
   # then set ANTHROPIC_API_KEY=... in .env
   ```

3. Backend (terminal 1):
   ```
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   export UMD_DATA_DIR=/path/to/umd-data/UMD
   python -m app.serve
   ```
   By default the agent uses Claude Sonnet (`claude-sonnet-5`). To choose a different
   model, set the `AGENT_MODEL` environment variable before starting the backend, for
   example to use Opus:
​  ```
   AGENT_MODEL=claude-opus-4-8 python -m app.serve
​  ```

   The demo video was recorded using Opus for the strongest reasoning.

4. Frontend (terminal 2):
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Open the URL Vite prints. Click Load case to pick one of the 300 cases, and Patient
   details to provide optional clinical context.

Pretrained weights are not committed (they live in the gitignored data folder). They are
provided as a GitHub Release: download unet_best.pt from the Releases page of this repo
and place it in data/models/. Alternatively, train the model yourself (see below).

## Training the segmentation model

The full training pipeline is included. On a CUDA GPU:
```
cd backend
source .venv/bin/activate
export UMD_DATA_DIR=/path/to/umd-data/UMD
python -m app.cv.preprocess --size 256
python -m app.cv.train --use-preextracted --size 256 --base-channels 32 --batch-size 16 --workers 4 --epochs 50 --lr-schedule cosine --class-weights auto --class-weight-cap 4 --augment --device cuda
```
The best checkpoint is saved to data/models/unet_best.pt.

## Limitations

- The CV is trained on a myoma-only dataset, so imaging covers fibroids; other
  PALM-COEIN causes are reasoned from the clinical intake, not seen in the image.
- The intramural percentage is a surface-adjacency proxy, so FIGO type calls that hinge
  on a fine 50 percent threshold or on pedunculation are marked provisional.
- Retrospective research data, decision support only. Not a validated medical device.

## License

Code is released under the MIT License (see LICENSE). The UMD dataset is CC-BY-4.0 and
must be cited as above. The pretrained weights were trained on the UMD dataset and are
shared under the same attribution requirement.
