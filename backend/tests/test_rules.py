"""Loud test for the rules file.

The real file must validate, and known malformations must raise RulesError.
Runs standalone (python tests/test_rules.py) or under pytest.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from app.rules.loader import RulesError, load_rules, validate_rules  # noqa: E402


def _assert_raises(broken: dict, label: str) -> None:
    try:
        validate_rules(broken)
    except RulesError:
        return
    raise AssertionError(f"validator did not fail on: {label}")


def test_rules_file_valid() -> None:
    validate_rules(load_rules())


def test_missing_figo_type_raises() -> None:
    broken = copy.deepcopy(load_rules())
    broken["figo_leiomyoma_types"] = [
        t for t in broken["figo_leiomyoma_types"] if t["type"] != "2"
    ]
    _assert_raises(broken, "missing FIGO type 2")


def test_empty_required_field_raises() -> None:
    broken = copy.deepcopy(load_rules())
    broken["figo_leiomyoma_types"][0]["geometric_definition"] = ""
    _assert_raises(broken, "empty geometric_definition")


def test_missing_palm_code_raises() -> None:
    broken = copy.deepcopy(load_rules())
    broken["palm_coein"]["structural"] = [
        e for e in broken["palm_coein"]["structural"] if e["code"] != "M"
    ]
    _assert_raises(broken, "missing PALM code M")


def test_intramural_proxy_flag_required() -> None:
    broken = copy.deepcopy(load_rules())
    broken["measurement_glossary"]["intramural_pct"]["proxy"] = False
    _assert_raises(broken, "intramural_pct not marked proxy")


if __name__ == "__main__":
    test_rules_file_valid()
    test_missing_figo_type_raises()
    test_empty_required_field_raises()
    test_missing_palm_code_raises()
    test_intramural_proxy_flag_required()
    print("all rules tests passed")
