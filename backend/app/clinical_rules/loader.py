"""External fixture loader; rule loading intentionally stays outside the pure evaluator."""

from pathlib import Path

import yaml

from .models import RuleDefinition


def load_rules(directory: Path) -> list[RuleDefinition]:
    rules: list[RuleDefinition] = []
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path} must contain an object")
        rules.append(RuleDefinition.model_validate(raw))
    return rules
