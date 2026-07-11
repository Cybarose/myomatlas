"""Loader and schema validator for the FIGO/PALM-COEIN rules file.

This module only loads and structurally validates the JSON. It holds no medical
logic: the criteria live in the JSON and the agent reasons from them (Phase 5).
Validation fails loudly with a specific message so a malformed file cannot pass
silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RULES_PATH: Path = Path(__file__).with_name("figo_palm_coein.json")

REQUIRED_FIGO_TYPES = {"0", "1", "2", "3", "4", "5", "6", "7", "8"}
REQUIRED_TOP_LEVEL = [
    "schema_version",
    "measurement_glossary",
    "figo_leiomyoma_types",
    "palm_coein",
    "malignancy_exclusion_rule",
]
REQUIRED_FIGO_STRING_FIELDS = [
    "type",
    "name",
    "category",
    "geometric_definition",
    "distinguishing_threshold",
    "symptom_relevance_aub",
    "fertility_relevance",
    "citation",
]
REQUIRED_MAPPING_FIELDS = ["signals", "expected", "proxy_caveat"]
REQUIRED_CONFIDENCE_FIELDS = ["level", "depends_on_fine_threshold", "note"]
CONFIDENCE_LEVELS = {"higher", "moderate", "lower"}
REQUIRED_MGMT_KEYS = [
    "medical_symptomatic",
    "uterus_preserving",
    "fertility_preserving",
    "definitive",
]
STRUCTURAL_CODES = {"P", "A", "L", "M"}
NONSTRUCTURAL_CODES = {"C", "O", "E", "I", "N"}
REQUIRED_PALM_STRING_FIELDS = ["code", "name", "group", "note", "citation"]
REQUIRED_MEASUREMENT_FIELDS = [
    "contacts_cavity",
    "distance_to_cavity_mm",
    "contacts_serosa",
    "distance_to_serosa_mm",
    "intramural_pct",
    "cavity_surface_pct",
    "serosa_surface_pct",
]


class RulesError(ValueError):
    """Raised when the rules file is missing, unreadable, or malformed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RulesError(message)


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def load_rules(path: Path | None = None) -> dict:
    """Read and parse the rules JSON, raising RulesError on any read problem."""
    target = Path(path) if path else RULES_PATH
    try:
        return json.loads(target.read_text())
    except FileNotFoundError as exc:
        raise RulesError(f"Rules file not found: {target}") from exc
    except json.JSONDecodeError as exc:
        raise RulesError(f"Rules file is not valid JSON: {exc}") from exc


def _validate_figo(types: Any) -> None:
    _require(_nonempty_list(types), "figo_leiomyoma_types must be a non-empty list")
    seen: set[str] = set()
    has_hybrid = False
    for entry in types:
        _require(isinstance(entry, dict), "each FIGO type must be an object")
        tid = entry.get("type")
        for field in REQUIRED_FIGO_STRING_FIELDS:
            _require(
                _nonempty_str(entry.get(field)),
                f"FIGO type {tid}: field '{field}' must be a non-empty string",
            )

        mapping = entry.get("measurement_mapping")
        _require(isinstance(mapping, dict), f"FIGO type {tid}: measurement_mapping must be an object")
        for field in REQUIRED_MAPPING_FIELDS:
            _require(field in mapping, f"FIGO type {tid}: measurement_mapping missing '{field}'")
        _require(_nonempty_list(mapping["signals"]), f"FIGO type {tid}: signals must be a non-empty list")
        _require(
            isinstance(mapping["expected"], dict) and len(mapping["expected"]) > 0,
            f"FIGO type {tid}: expected must be a non-empty object",
        )
        _require(_nonempty_str(mapping["proxy_caveat"]), f"FIGO type {tid}: proxy_caveat must be non-empty")

        confidence = entry.get("confidence")
        _require(isinstance(confidence, dict), f"FIGO type {tid}: confidence must be an object")
        for field in REQUIRED_CONFIDENCE_FIELDS:
            _require(field in confidence, f"FIGO type {tid}: confidence missing '{field}'")
        _require(
            confidence["level"] in CONFIDENCE_LEVELS,
            f"FIGO type {tid}: confidence.level must be one of {sorted(CONFIDENCE_LEVELS)}",
        )
        _require(
            isinstance(confidence["depends_on_fine_threshold"], bool),
            f"FIGO type {tid}: confidence.depends_on_fine_threshold must be a boolean",
        )
        _require(_nonempty_str(confidence["note"]), f"FIGO type {tid}: confidence.note must be non-empty")

        mgmt = entry.get("management_options")
        _require(isinstance(mgmt, dict), f"FIGO type {tid}: management_options must be an object")
        for key in REQUIRED_MGMT_KEYS:
            _require(
                _nonempty_list(mgmt.get(key)),
                f"FIGO type {tid}: management_options.{key} must be a non-empty list",
            )

        if tid in REQUIRED_FIGO_TYPES:
            seen.add(tid)
        if entry.get("category") == "hybrid":
            has_hybrid = True

    missing = REQUIRED_FIGO_TYPES - seen
    _require(not missing, f"missing FIGO types: {sorted(missing)}")
    _require(has_hybrid, "missing the hybrid (transmural) entry")


def _validate_palm_group(items: Any, codes: set[str], group: str) -> None:
    _require(_nonempty_list(items), f"palm_coein.{group} must be a non-empty list")
    seen: set[str] = set()
    for entry in items:
        _require(isinstance(entry, dict), f"palm_coein.{group}: each entry must be an object")
        for field in REQUIRED_PALM_STRING_FIELDS:
            _require(
                _nonempty_str(entry.get(field)),
                f"palm_coein.{group}: field '{field}' must be a non-empty string",
            )
        _require(
            isinstance(entry.get("image_visible"), bool),
            f"palm_coein.{group} {entry.get('code')}: image_visible must be a boolean",
        )
        seen.add(entry["code"])
    _require(seen == codes, f"palm_coein.{group} codes {sorted(seen)} must equal {sorted(codes)}")


def _validate_glossary(glossary: Any) -> None:
    _require(isinstance(glossary, dict) and glossary, "measurement_glossary must be a non-empty object")
    for field in REQUIRED_MEASUREMENT_FIELDS:
        _require(field in glossary, f"measurement_glossary missing field: {field}")
    intramural = glossary["intramural_pct"]
    _require(
        isinstance(intramural, dict) and intramural.get("proxy") is True,
        "measurement_glossary.intramural_pct must be marked proxy=true",
    )


def _validate_malignancy(rule: Any) -> None:
    _require(isinstance(rule, dict), "malignancy_exclusion_rule must be an object")
    _require(_nonempty_list(rule.get("flag_when")), "malignancy_exclusion_rule.flag_when must be a non-empty list")
    _require(_nonempty_str(rule.get("action")), "malignancy_exclusion_rule.action must be non-empty")
    _require(_nonempty_str(rule.get("citation")), "malignancy_exclusion_rule.citation must be non-empty")


def validate_rules(rules: Any) -> None:
    """Structurally validate the rules object, raising RulesError on any problem."""
    _require(isinstance(rules, dict), "top level of the rules file must be an object")
    for key in REQUIRED_TOP_LEVEL:
        _require(key in rules, f"missing top-level key: {key}")

    _validate_glossary(rules["measurement_glossary"])
    _validate_figo(rules["figo_leiomyoma_types"])

    palm = rules["palm_coein"]
    _require(
        isinstance(palm, dict) and "structural" in palm and "nonstructural" in palm,
        "palm_coein must have 'structural' and 'nonstructural'",
    )
    _validate_palm_group(palm["structural"], STRUCTURAL_CODES, "structural")
    _validate_palm_group(palm["nonstructural"], NONSTRUCTURAL_CODES, "nonstructural")

    _validate_malignancy(rules["malignancy_exclusion_rule"])


def load_and_validate(path: Path | None = None) -> dict:
    """Load the rules file and validate it, returning the parsed object."""
    rules = load_rules(path)
    validate_rules(rules)
    return rules
