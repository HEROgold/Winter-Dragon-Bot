"""Check that every table Class is present.

The script checks that every SQLModel table class defined in
the `__all__` list of `src/winter_dragon/database/__init__.py`.

Prints green for found, yellow for extra's, red for missing. Exits with code 1 if any are missing.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
RESET = "\x1b[0m"


def find_table_classes(py_path: Path) -> list[str]:
    """Find all class names in the given Python file that define SQLModel tables."""
    src = py_path.read_text(encoding="utf8")
    tree = ast.parse(src)
    names: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check for keyword table=True in class definition (e.g. class X(SQLModel, table=True))
            has_table_kw = False
            for kw in getattr(node, "keywords", []):
                if getattr(kw, "arg", None) == "table":
                    val = getattr(kw, "value", None)
                    # ast.Constant for Python 3.8+, ast.NameConstant for older
                    if (isinstance(val, ast.Constant) and val.value is True) or (
                        type(val).__name__ == "NameConstant" and getattr(val, "value", None) is True
                    ):
                        has_table_kw = True
                        break

            if has_table_kw:
                names.append(node.name)

    return names


def load_all_list(init_path: Path) -> list[str]:  # noqa: C901
    """Load the __all__ list from the given __init__.py file."""
    src = init_path.read_text(encoding="utf8")
    tree = ast.parse(src)

    for node in tree.body:
        # Look for assignment to __all__
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = node.value
                    if isinstance(value, (ast.List, ast.Tuple)):
                        items: list[str] = []
                        for elt in value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                items.append(elt.value)
                            elif isinstance(elt, ast.Str):  # ty:ignore[deprecated]
                                match elt.s:
                                    case str():
                                        items.append(elt.s)
                                    case bytes():
                                        items.append(elt.s.decode("utf8"))
                                    case int():
                                        items.append(str(elt.s))
                        return items
    return []


def main() -> int:
    """Entry point."""
    root = Path(__file__).parent
    tables_dir = root / "tables"
    init_file = root / "__init__.py"

    if not tables_dir.exists():
        return 2

    py_files = list(tables_dir.rglob("*.py"))

    table_classes: list[str] = []
    for p in py_files:
        table_classes.extend(find_table_classes(p))

    table_classes = sorted(set(table_classes))

    all_list = load_all_list(init_file)
    all_set = set(all_list)

    any_missing = False
    for name in table_classes:
        if name in all_set:
            print(f"{GREEN}FOUND: {name}{RESET}")  # noqa: T201
        else:
            any_missing = True
            print(f"{RED}MISSING: {name}{RESET}")  # noqa: T201

    # Also show classes that are in __all__ but not discovered (optional)
    extras = sorted([x for x in all_list if x not in table_classes])
    if extras:
        for _x in extras:
            print(f"{YELLOW}EXTRA: {_x}{RESET}")  # noqa: T201

    return 1 if any_missing else 0


if __name__ == "__main__":
    sys.exit(main())
