"""Prompt assembly for the reasoning agent.

The rules file is the source of truth and is placed in the system prompt (cached).
Case-specific measurements and intake go in the user message. The model is forced
to answer through the submit_analysis tool so the output is structured JSON.
"""

from __future__ import annotations

import json

SYSTEM_INSTRUCTIONS = (
    "You are a clinical decision-support reasoning assistant for uterine myomas "
    "(leiomyomas) and abnormal uterine bleeding. This is decision support with a "
    "human in the loop, not a diagnosis.\n\n"
    "Reason strictly and only from the RULES FILE provided below. Do not use outside "
    "medical knowledge beyond it. Every conclusion must be traceable to that file.\n\n"
    "Tasks:\n"
    "1. For each myoma in the measurements, assign a FIGO type from the rules. In the "
    "justification, cite the specific measurement values you used (for example "
    "contacts_cavity, distance_to_cavity_mm, contacts_serosa, intramural_pct, "
    "cavity_surface_pct, serosa_surface_pct, volume, diameter).\n"
    "2. Respect the confidence and reasoning_notes.uncertainty_policy fields. When a "
    "type decision hinges on the fine 50 percent threshold (types 1 vs 2, 5 vs 6), on "
    "pedunculation (types 0, 7), or on anatomical location (type 8), mark the myoma "
    "provisional and use lower confidence, and state the ambiguity. Treat intramural_pct "
    "and the surface percentages as proxies, not exact measurements.\n"
    "   Notation: the hyphen form (for example 2-5) is reserved only for a transmural "
    "hybrid myoma that reaches both the endometrium and the serosa. For a single myoma "
    "that is merely ambiguous between two single types (for example 6 vs 7, where "
    "pedunculation cannot be resolved from masks), do not write a hyphenated type. Set "
    "figo_type to the single more likely type (for example \"6\") and express the "
    "alternative in figo_type_name and justification (for example figo_type_name "
    "'Subserosal, less than 50 percent intramural; type 7 pedunculated cannot be "
    "excluded from masks'). Keep provisional and confidence as they would be.\n"
    "3. Take management_options from the assigned type's management_options in the rules, "
    "then tailor them to the intake instead of copying the whole list: select and order "
    "the options that fit this patient. When fertility is desired, lead with uterus- and "
    "fertility-preserving options and do not lead with hysterectomy. When fertility is not "
    "desired, or the patient is postmenopausal, definitive options may lead and "
    "fertility-preserving framing should be dropped. When the intake is empty, keep the "
    "list neutral. Never invent an option that is not in the rules for that type. Also "
    "report figo_group as the type's category in the rules (a hybrid is Transmural), and "
    "bleeding_relevance as exactly one of the words high, medium or low, judged from that "
    "type's symptom_relevance_aub rather than copied from it.\n"
    "4. Place the case in PALM-COEIN using the rules. Distinguish image-visible causes "
    "from history or lab based ones. These masks show only wall, cavity, myoma, and "
    "nabothian cyst, so state what cannot be assessed from imaging alone.\n"
    "5. Apply malignancy_exclusion_rule using the intake to decide the malignancy flag, "
    "and give the reason. If information needed for the rule (for example menopausal "
    "status or age) is missing, be conservative and say so.\n\n"
    "Clinical intake fields may be null. Do not invent them and do not invent "
    "measurements; use only the values provided. State the imaging modality from the "
    "measurements 'modality' field and do not assume a different one.\n\n"
    "Write the patient_explanation in plain language with no medical jargon: what the "
    "finding means, what the options are (including uterus- and fertility-preserving "
    "ones where relevant), and that a clinician makes the final decisions.\n\n"
    "Return your answer only by calling the submit_analysis tool. Provide "
    "clinician_report as a JSON object and patient_explanation as a separate "
    "non-empty plain-text string; do not put the report inside a string or merge "
    "the two fields."
)

# Forced structured output. Tool use guarantees valid JSON matching this schema.
OUTPUT_TOOL = {
    "name": "submit_analysis",
    "description": "Return the structured clinician report and the patient explanation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "clinician_report": {
                "type": "object",
                "properties": {
                    "myomas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "description": "Matches the myoma id in the measurements.",
                                },
                                "figo_type": {
                                    "type": "string",
                                    "description": "FIGO type 0-8, a hybrid like 2-5, or 'uncertain'.",
                                },
                                "figo_type_name": {"type": "string"},
                                "figo_group": {
                                    "type": "string",
                                    "enum": [
                                        "Submucosal",
                                        "Intramural",
                                        "Subserosal",
                                        "Transmural",
                                        "Other",
                                    ],
                                    "description": "Group of the assigned type, from the rules file category. A hybrid is Transmural.",
                                },
                                "bleeding_relevance": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "description": "Exactly one of the words high, medium or low. Judge it from the assigned type's symptom_relevance_aub. Do not copy that sentence.",
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["higher", "moderate", "lower"],
                                },
                                "provisional": {
                                    "type": "boolean",
                                    "description": "True when the call depends on a fine 50 percent threshold, pedunculation, or location.",
                                },
                                "justification": {
                                    "type": "string",
                                    "description": "Short reasoning that cites the specific measurement values used.",
                                },
                                "size_summary": {"type": "string"},
                                "location_summary": {"type": "string"},
                                "management_options": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [
                                "id",
                                "figo_type",
                                "figo_type_name",
                                "figo_group",
                                "bleeding_relevance",
                                "confidence",
                                "provisional",
                                "justification",
                                "size_summary",
                                "location_summary",
                                "management_options",
                            ],
                        },
                    },
                    "palm_coein": {
                        "type": "object",
                        "properties": {
                            "structural_present": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "PALM causes supported by the imaging measurements.",
                            },
                            "nonstructural_to_consider": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "COEIN categories to consider from history or labs.",
                            },
                            "summary": {"type": "string"},
                        },
                        "required": ["structural_present", "nonstructural_to_consider", "summary"],
                    },
                    "malignancy_flag": {
                        "type": "object",
                        "properties": {
                            "flag": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": ["flag", "reason"],
                    },
                    "overall_summary": {"type": "string"},
                },
                "required": ["myomas", "palm_coein", "malignancy_flag", "overall_summary"],
            },
            "patient_explanation": {
                "type": "string",
                "description": "Plain-language explanation with no jargon.",
            },
        },
        "required": ["clinician_report", "patient_explanation"],
    },
}


def build_system_blocks(rules: dict) -> list[dict]:
    """System prompt: instructions plus the rules file as a cached source of truth."""
    return [
        {"type": "text", "text": SYSTEM_INSTRUCTIONS},
        {
            "type": "text",
            "text": "RULES FILE (source of truth, reason only from this):\n"
            + json.dumps(rules, ensure_ascii=False),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def build_user_message(measurements: dict, intake: dict) -> str:
    """User message: the case measurements and the clinical intake."""
    return (
        "CASE MEASUREMENTS (from the CV pipeline):\n"
        + json.dumps(measurements, ensure_ascii=False)
        + "\n\nCLINICAL INTAKE (fields may be null):\n"
        + json.dumps(intake, ensure_ascii=False)
        + "\n\nProduce the analysis by calling submit_analysis."
    )
