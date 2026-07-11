"""Run one end-to-end agent example on a case with a sample intake.

    python -m app.agent.run_example --case UMD_221129_003
    python -m app.agent.run_example --case UMD_221129_003 --save

With --save, the full result (structured JSON) and a readable text rendering are
written under data/phase5_example/ (gitignored).
"""

from __future__ import annotations

import argparse
import json
import logging

from ..cv.config import REPO_ROOT
from .agent import analyze_case, measurements_for_case


def render_text(case_id: str, measurements: dict, result: dict) -> str:
    report = result["clinician_report"]
    lines: list[str] = []
    lines.append(f"MyoMap analysis: {case_id}")
    lines.append(f"modality: {measurements.get('modality')}")
    lines.append(f"model: {result['model']}  rules_version: {result['rules_version']}")
    lines.append("")
    lines.append("CLINICIAN REPORT")
    for m in report["myomas"]:
        lines.append(
            f"- Myoma {m['id']}: FIGO {m['figo_type']} ({m['figo_type_name']}) "
            f"[confidence: {m['confidence']}, provisional: {m['provisional']}]"
        )
        lines.append(f"    size: {m['size_summary']}")
        lines.append(f"    location: {m['location_summary']}")
        lines.append(f"    justification: {m['justification']}")
        lines.append("    management: " + "; ".join(m["management_options"]))
    lines.append("")
    lines.append("PALM-COEIN")
    lines.append("  structural present:")
    for item in report["palm_coein"]["structural_present"]:
        lines.append(f"    - {item}")
    lines.append("  nonstructural to consider:")
    for item in report["palm_coein"]["nonstructural_to_consider"]:
        lines.append(f"    - {item}")
    lines.append(f"  summary: {report['palm_coein']['summary']}")
    lines.append("")
    lines.append(f"MALIGNANCY FLAG: {report['malignancy_flag']['flag']}")
    lines.append(f"  reason: {report['malignancy_flag']['reason']}")
    lines.append("")
    lines.append(f"OVERALL SUMMARY: {report['overall_summary']}")
    lines.append("")
    lines.append("PATIENT EXPLANATION")
    lines.append(result["patient_explanation"])
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Agent end-to-end example (Phase 5).")
    parser.add_argument("--case", default="UMD_221129_003")
    parser.add_argument("--save", action="store_true", help="Write result files under data/phase5_example/.")
    args = parser.parse_args()

    measurements = measurements_for_case(args.case)

    intake = {
        "age": 44,
        "menopausal_status": "premenopausal",
        "bleeding_severity": "heavy",
        "fertility_desire": "desired",
        "risk_factors": [],
        "notes": "Wants to preserve the uterus and future fertility.",
    }

    print(f"case: {args.case} | modality: {measurements['modality']} | myoma_count: {measurements['myoma_count']}\n")

    result = analyze_case(measurements, intake)

    if not result.get("ok"):
        print(f"AGENT ERROR: {result.get('error')}")
        print(f"(rules_version {result.get('rules_version')}, model {result.get('model')})")
        return

    print(f"model: {result['model']} | rules_version: {result['rules_version']} | usage: {result['usage']}\n")
    print("=== CLINICIAN REPORT ===")
    print(json.dumps(result["clinician_report"], indent=2))
    print("\n=== PATIENT EXPLANATION ===")
    print(result["patient_explanation"])

    if args.save:
        out_dir = REPO_ROOT / "data" / "phase5_example"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"{args.case}_analysis.json"
        text_path = out_dir / f"{args.case}_report.txt"
        json_path.write_text(json.dumps(result, indent=2))
        text_path.write_text(render_text(args.case, measurements, result))
        print(f"\nsaved: {json_path}")
        print(f"saved: {text_path}")


if __name__ == "__main__":
    main()
