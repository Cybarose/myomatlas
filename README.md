# AUB-Tool

Offenes, bildgestuetztes Entscheidungs- und Aufklaerungs-Tool fuer starke/abnorme
Regelblutung (AUB). Computer Vision segmentiert Myome im Becken-MRT, ein Claude-Agent
ordnet sie nach FIGO/PALM-COEIN ein, erzeugt einen strukturierten Befund plus eine
patientenverstaendliche Erklaerung, und eine 3D-Ansicht zeigt die Lage.

Konzept, Hintergrund und Bauplan: siehe [CONCEPT_AND_PLAN.md](CONCEPT_AND_PLAN.md).

## Repo-Struktur

```
backend/
  app/
    main.py            FastAPI-Einstieg, Endpunkte
    cv/                Segmentierung, Messwerte, Mesh-Erzeugung
    agent/             Claude-Agent-Logik und Tools
    rules/             figo_palm_coein.json (die Regeldatei)
    verification/      Held-out-Eval: Dice + FIGO-Uebereinstimmung
  requirements.txt
frontend/
  src/
    components/
    viewer/            three.js 3D-Ansicht
    report/            Befund- und Patientenerklaerung-Panel
data/                  UMD-Datensatz (per .gitignore ausgeschlossen)
```

## Setup

Dieses Projekt ist "bring your own key". Wer es klont, setzt seinen eigenen
`ANTHROPIC_API_KEY` und zahlt seine eigene API-Nutzung.

### Backend

```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # dann .env mit echtem Key fuellen
uvicorn app.main:app --reload
```

Health-Check: http://localhost:8000/health

### Frontend

```
cd frontend
npm install
npm run dev
```

Dev-Server: http://localhost:5173

## Datensatz

UMD (Uterine Myoma MRI Dataset), Scientific Data 2024, DOI 10.1038/s41597-024-03170-x.
Der Datensatz liegt unter `data/` und ist nicht Teil des Repos. Beziehe ihn ueber den
Abschnitt "Data Availability" des Papers und beachte dessen Lizenz-/Zugangsbedingungen.

## Hinweis

Entscheidungsunterstuetzung mit Mensch in der Schleife, kein zugelassenes Medizingeraet.
