"""CLI validator for the rules file; exits non-zero and prints why if malformed.

    python -m app.rules.validate
"""

from __future__ import annotations

import sys

from .loader import RULES_PATH, RulesError, load_rules, validate_rules


def main() -> None:
    try:
        rules = load_rules()
        validate_rules(rules)
    except RulesError as exc:
        print(f"INVALID: {exc}")
        sys.exit(1)

    figo = [t["type"] for t in rules["figo_leiomyoma_types"]]
    palm = [e["code"] for e in rules["palm_coein"]["structural"]]
    coein = [e["code"] for e in rules["palm_coein"]["nonstructural"]]
    print(f"OK: {RULES_PATH.name} is valid")
    print(f"  FIGO entries: {figo}")
    print(f"  PALM: {palm}  COEIN: {coein}")


if __name__ == "__main__":
    main()
