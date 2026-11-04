"""Guard the strongest architectural boundary before Phase 4 adds rule logic."""

import ast
from pathlib import Path


def test_clinical_rules_does_not_import_application_or_ai() -> None:
    package = Path(__file__).parents[1] / "app" / "clinical_rules"
    forbidden_prefixes = ("app.", "ai", "celery", "sqlalchemy", "redis")

    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(name.startswith(forbidden_prefixes) for name in names), path
