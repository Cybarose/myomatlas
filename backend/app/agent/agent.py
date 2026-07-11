"""Core reasoning agent: measurements plus intake to a structured report.

Uses the Anthropic Python SDK. The API key comes from ANTHROPIC_API_KEY (loaded
from a repo .env if present), never hardcoded. FIGO assignment is not computed in
Python: the model reasons from the rules file. Errors are returned as a clear
message instead of raising, so callers never crash.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from ..rules import load_and_validate
from .prompt import OUTPUT_TOOL, build_system_blocks, build_user_message

logger = logging.getLogger("myomap.agent")

# Load a repo-root .env so ANTHROPIC_API_KEY is available for local runs.
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-5")
# Enough headroom for several myomas plus the patient explanation; a truncated
# tool call (stop_reason max_tokens) is detected and reported rather than
# returned as silent nulls.
DEFAULT_MAX_TOKENS = 8000


def measurements_for_case(case_id: str) -> dict:
    """Compute the CV measurement JSON for a case (lazy CV import)."""
    from ..cv.measurements import measure_case
    from ..cv.umd_loader import load_case

    return measure_case(load_case(case_id))


def _extract_tool_input(response: anthropic.types.Message) -> dict | None:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == OUTPUT_TOOL["name"]:
            return dict(block.input)
    return None


def _normalize_tool_input(raw: dict) -> dict:
    """Repair a common model glitch where clinician_report is a JSON string.

    Sometimes the model serializes the report object into the string field and
    appends the patient explanation after it, leaving patient_explanation null.
    Parse the leading JSON object and recover any trailing text as the patient
    explanation.
    """
    report = raw.get("clinician_report")
    patient = raw.get("patient_explanation")
    if isinstance(report, str):
        try:
            obj, end = json.JSONDecoder().raw_decode(report.strip())
            trailing = report.strip()[end:].strip()
            report = obj
            if not patient and trailing:
                patient = trailing
        except json.JSONDecodeError:
            pass
    return {"clinician_report": report, "patient_explanation": patient}


def analyze_case(
    measurements: dict,
    intake: dict | None = None,
    model: str | None = None,
    rules: dict | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Run the reasoning step, returning a structured result or an error dict."""
    rules = rules if rules is not None else load_and_validate()
    rules_version = rules.get("schema_version")
    model = model or DEFAULT_MODEL
    logger.info("Analyzing case with FIGO/PALM-COEIN rules schema_version %s", rules_version)

    base = {
        "ok": False,
        "rules_version": rules_version,
        "model": model,
        "case_id": (measurements or {}).get("case_id"),
    }

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {
            **base,
            "error": "ANTHROPIC_API_KEY is not set. Set it in the environment or a "
            ".env file at the repo root (bring your own key).",
        }

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=build_system_blocks(rules),
            messages=[{"role": "user", "content": build_user_message(measurements, intake or {})}],
            tools=[OUTPUT_TOOL],
            tool_choice={"type": "tool", "name": OUTPUT_TOOL["name"]},
        )
    except anthropic.APIError as exc:
        return {**base, "error": f"Anthropic API call failed: {exc}"}
    except Exception as exc:  # network, config, unexpected
        return {**base, "error": f"Unexpected error calling the model: {exc}"}

    tool_input = _extract_tool_input(response)
    if tool_input is not None:
        tool_input = _normalize_tool_input(tool_input)
    if tool_input is None or not isinstance(tool_input.get("clinician_report"), dict):
        detail = "output was truncated (raise max_tokens)" if response.stop_reason == "max_tokens" else "structured output was malformed"
        return {**base, "error": f"Model did not return a complete report: {detail}.", "stop_reason": response.stop_reason}

    return {
        "ok": True,
        "rules_version": rules_version,
        "model": model,
        "case_id": base["case_id"],
        "clinician_report": tool_input.get("clinician_report"),
        "patient_explanation": tool_input.get("patient_explanation"),
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
