# ruff: noqa: INP001 - a standalone repo script, not part of any package
"""Check that relative links in the agent guidance and docs point at files that exist.

Covers CLAUDE.md, the READMEs, the project skills and docs/. Skills and CLAUDE.md must not
use ``#L<n>`` line anchors: they go stale on every edit above the target, so name the symbol instead
(``client.py `returns_known_exception```) and let a Grep find it.

Usage (from the repo root):

    uv run python scripts/check_doc_links.py
"""

from __future__ import annotations

lazy import re
lazy import sys
lazy from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s]+)\)")
LINE_ANCHOR = re.compile(r"#L\d+")
CODE_SPAN = re.compile(r"`[^`]*`")


def documents() -> list[Path]:
    """List every markdown file whose links are checked."""
    return sorted(
        {
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            *ROOT.glob(".claude/skills/*/*.md"),
            *ROOT.glob("docs/**/*.md"),
            *ROOT.glob("wd-*/README.md"),
        },
    )


def problems(document: Path) -> list[str]:
    """Describe each broken link or banned line anchor in one document."""
    found: list[str] = []
    guidance = document.name == "CLAUDE.md" or ".claude" in document.parts
    in_fence = False
    for number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if in_fence:
            continue
        for target in LINK.findall(CODE_SPAN.sub("", line)):
            path, _, anchor = target.partition("#")
            where = f"{document.relative_to(ROOT).as_posix()}:{number}"
            if path and not (document.parent / path).exists():
                found.append(f"{where}: broken link -> {target}")
            if guidance and LINE_ANCHOR.fullmatch(f"#{anchor}"):
                found.append(f"{where}: line anchor -> {target} (name the symbol instead)")
    return found


def main() -> int:
    """Print every problem and exit 1 when there are any."""
    found = [problem for document in documents() for problem in problems(document)]
    for problem in found:
        print(problem)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
