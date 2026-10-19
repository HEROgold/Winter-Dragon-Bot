# ruff: noqa: INP001 - a standalone repo script, not part of any package
"""Generate the agent-facing API reference in docs/reference/ from the workspace source.

One markdown page per package (plus one per first-level subpackage), listing only the public surface
of each module: classes (bases, fields, members), functions and type aliases, each with the first
paragraph of its docstring. Imports, ``_private`` names, function bodies and ``if TYPE_CHECKING:``
blocks are left out on purpose, so a page reads in one pass instead of opening the source files.

Source is parsed with :mod:`ast` and never imported, so the generator works even when a package
fails to import. Pages carry file paths and symbol names but no line numbers; they only change
when the public API does.

Usage (from the repo root):

    uv run python scripts/generate_api_reference.py           # regenerate docs/reference/
    uv run python scripts/generate_api_reference.py --check   # verify it's up to date (pre-commit)
"""

from __future__ import annotations

lazy import argparse
lazy import ast
lazy import copy
lazy import sys
lazy import textwrap
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import override


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "reference"
WRAP = 120
DOC_LIMIT = 200

HIDDEN_DECORATORS = frozenset({"override", "typing.override", "abstractmethod", "final"})
SKIP_DECORATORS = frozenset({"overload", "typing.overload"})
PROPERTY_DECORATORS = frozenset({"property", "cached_property", "functools.cached_property"})

HEADER = """\
<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->
"""


@dataclass(frozen=True)
class Package:
    """A workspace package whose public API gets reference pages."""

    distribution: str
    source: Path

    @property
    def import_name(self) -> str:
        """The top-level import name, e.g. ``wd_discord``."""
        return self.source.name


def discover_packages() -> list[Package]:
    """Find every ``wd-*`` member plus the root ``winter_dragon`` package."""
    packages = [
        Package(member.name, source)
        for member in sorted(ROOT.glob("wd-*"))
        for source in sorted((member / "src").glob("wd_*"))
        if (source / "__init__.py").is_file()
    ]
    packages.append(Package("winter-dragon", ROOT / "src" / "winter_dragon"))
    return packages


def is_public(name: str) -> bool:
    """Tell whether a name belongs in the reference."""
    return not name.startswith("_")


def module_files(package: Package) -> list[Path]:
    """List the public modules of a package; a ``.pyi`` is used only when it has no ``.py`` sibling."""
    files: list[Path] = []
    for path in sorted(package.source.rglob("*.py*")):
        if path.suffix not in {".py", ".pyi"} or "__pycache__" in path.parts or path.stem == "__main__":
            continue
        if path.suffix == ".pyi" and path.with_suffix(".py").exists():
            continue
        parts = path.relative_to(package.source).with_suffix("").parts
        if path.stem != "__init__" and not all(is_public(part) for part in parts):
            continue
        files.append(path)
    return files


def dotted_name(package: Package, path: Path) -> str:
    """Turn ``wd_discord/entities/user.py`` into ``wd_discord.entities.user``."""
    parts = path.relative_to(package.source).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join((package.import_name, *parts))


def summary(node: ast.AST) -> str:
    """Return the first paragraph of a docstring, collapsed onto one line and capped."""
    if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    doc = ast.get_docstring(node)
    if not doc:
        return ""
    first = " ".join(doc.strip().split("\n\n")[0].split())
    return first if len(first) <= DOC_LIMIT else first[: DOC_LIMIT - 1].rstrip() + "…"


class _StripAnnotated(ast.NodeTransformer):
    """Reduce ``Annotated[T, meta...]`` to ``T``; the metadata is noise in a signature."""

    @override
    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        self.generic_visit(node)
        name = ast.unparse(node.value)
        if name in {"Annotated", "typing.Annotated"} and isinstance(node.slice, ast.Tuple) and node.slice.elts:
            return node.slice.elts[0]
        return node


def render_type(node: ast.expr | None) -> str:
    """Unparse an annotation, unquoting string annotations and stripping ``Annotated``."""
    if node is None:
        return ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            node = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return node.value
    return ast.unparse(_StripAnnotated().visit(copy.deepcopy(node)))


def render_type_params(params: list[ast.type_param]) -> str:
    """Render PEP 695 type parameters, ``[T, **P]``, or nothing."""
    return f"[{', '.join(ast.unparse(param) for param in params)}]" if params else ""


def decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    """Name each decorator without its call arguments: ``@Cog.command(name=...)`` -> ``Cog.command``."""
    return [ast.unparse(dec.func if isinstance(dec, ast.Call) else dec) for dec in node.decorator_list]


def render_arguments(args: ast.arguments, *, drop_first: bool) -> str:
    """Render a parameter list, dropping ``self``/``cls`` and stripping annotation metadata."""
    args = copy.deepcopy(args)
    if drop_first:
        if args.posonlyargs:
            args.posonlyargs.pop(0)
        elif args.args:
            args.args.pop(0)
    for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg):
        if arg is not None and arg.annotation is not None:
            arg.annotation = ast.parse(render_type(arg.annotation), mode="eval").body
    return ast.unparse(args)


def render_function(node: ast.FunctionDef | ast.AsyncFunctionDef, *, method: bool) -> list[str]:
    """Render the bullet for a function or method; nothing for overloads and property setters."""
    decorators = decorator_names(node)
    if any(dec in SKIP_DECORATORS or dec.endswith((".setter", ".deleter")) for dec in decorators):
        return []
    prefix = "".join(f"@{dec} " for dec in decorators if dec not in HIDDEN_DECORATORS)
    prefix += "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    returns = f" -> {render_type(node.returns)}" if node.returns is not None else ""
    if PROPERTY_DECORATORS.intersection(decorators):
        signature = f"{node.name}{returns}"
    else:
        arguments = render_arguments(node.args, drop_first=method and "staticmethod" not in decorators)
        signature = f"{node.name}{render_type_params(node.type_params)}({arguments}){returns}"
    doc = summary(node)
    return [f"- `{prefix}{signature}`" + (f" — {doc}" if doc else "")]


def wrapped(label: str, items: list[str]) -> list[str]:
    """Render a bullet listing many short items, wrapped to a readable width; nothing when empty."""
    if not items:
        return []
    text = f"- {label}: " + ", ".join(items)
    return textwrap.wrap(text, WRAP, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)


def public_targets(targets: list[ast.expr]) -> list[str]:
    """Return the public plain names an assignment binds."""
    return [target.id for target in targets if isinstance(target, ast.Name) and is_public(target.id)]


def render_class(node: ast.ClassDef) -> list[str]:
    """Render the heading, docstring and members of a public class."""
    bases = [ast.unparse(base) for base in node.bases] + [ast.unparse(kw) for kw in node.keywords]
    decorators = "".join(f"@{dec} " for dec in decorator_names(node) if dec not in HIDDEN_DECORATORS)
    signature = f"{decorators}class {node.name}{render_type_params(node.type_params)}"
    lines = [f"### `{signature}" + (f"({', '.join(bases)})" if bases else "") + "`"]
    if doc := summary(node):
        lines.append(doc)

    fields: list[str] = []
    attributes: list[str] = []
    nested: list[str] = []
    members: list[str] = []
    for item in node.body:
        match item:
            case ast.AnnAssign(target=ast.Name(id=name), annotation=annotation) if is_public(name):
                fields.append(f"{name}: {render_type(annotation)}")
            case ast.Assign(targets=targets):
                attributes += public_targets(targets)
            case ast.ClassDef() if is_public(item.name):
                nested.append(item.name)
            case ast.FunctionDef() | ast.AsyncFunctionDef() if is_public(item.name) or item.name == "__call__":
                members += render_function(item, method=True)
            case _:
                pass

    body = [*wrapped("fields", fields), *wrapped("attributes", attributes), *wrapped("nested classes", nested), *members]
    return [*lines, "", *body] if body else lines


def render_module(package: Package, path: Path, *, docstring: bool = True) -> list[str]:
    """Render the section for one module, or nothing when it has no public surface."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    exports: list[str] = []
    names: list[str] = []
    listed: list[str] = []
    classes: list[str] = []
    for node in tree.body:
        match node:
            case ast.Assign(targets=[ast.Name(id="__all__")], value=ast.List() | ast.Tuple() as value):
                exports = [elt.value for elt in value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
            case ast.Assign(targets=targets):
                names += public_targets(targets)
            case ast.AnnAssign(target=ast.Name(id=name), annotation=annotation) if is_public(name):
                names.append(f"{name}: {render_type(annotation)}")
            case ast.TypeAlias(name=ast.Name(id=name)) if is_public(name):
                listed.append(f"- `type {name}{render_type_params(node.type_params)} = {render_type(node.value)}`")
            case ast.FunctionDef() | ast.AsyncFunctionDef() if is_public(node.name):
                listed += render_function(node, method=False)
            case ast.ClassDef() if is_public(node.name):
                classes += ["", *render_class(node)]
            case _:
                pass

    listed = [*wrapped("exports", exports), *wrapped("module names", names), *listed]
    if not (listed or classes):
        return []
    lines = [f"## `{dotted_name(package, path)}` — `{path.relative_to(ROOT).as_posix()}`"]
    if docstring and (doc := summary(tree)):
        lines.append(doc)
    return [*lines, *(["", *listed] if listed else []), *classes]


@dataclass(frozen=True)
class Page:
    """One reference page: a package's top-level modules, or one of its first-level subpackages."""

    package: Package
    directory: Path

    @property
    def import_name(self) -> str:
        """Dotted import path of the page's package or subpackage."""
        return ".".join((self.package.import_name, *self.directory.relative_to(self.package.source).parts))

    @property
    def path(self) -> Path:
        """Where the page is written: ``wd-discord.md``, ``wd-discord.entities.md``, ..."""
        parts = self.directory.relative_to(self.package.source).parts
        return OUTPUT_DIR / f"{'.'.join((self.package.distribution, *parts))}.md"

    @property
    def summary(self) -> str:
        """Docstring summary of the ``__init__``; empty for a namespace package."""
        init = self.directory / "__init__.py"
        return summary(ast.parse(init.read_text(encoding="utf-8"))) if init.is_file() else ""

    def modules(self, files: list[Path]) -> list[Path]:
        """Pick the package's modules that belong on this page."""
        if self.directory == self.package.source:
            return [path for path in files if path.parent == self.directory]
        return [path for path in files if self.directory in path.parents]


def package_pages(package: Package) -> list[Page]:
    """List the package's own page, then one per public first-level subpackage."""
    subpackages = {path.relative_to(package.source).parts[0] for path in module_files(package) if path.parent != package.source}
    return [Page(package, package.source), *(Page(package, package.source / name) for name in sorted(subpackages))]


def render_page(page: Page, files: list[Path]) -> str:
    """Render one reference page."""
    lines = [HEADER, f"# `{page.import_name}` ({page.package.distribution})"]
    if page.summary:
        lines.append(page.summary)
    lines += ["", "Public names only — open the file when you need a body. Index: [API reference](index.md)."]
    for path in page.modules(files):
        # The page's own __init__ docstring already heads the page.
        if section := render_module(page.package, path, docstring=path != page.directory / "__init__.py"):
            lines += ["", *section]
    return "\n".join(lines) + "\n"


def render_index(pages: list[Page]) -> str:
    """Render the index page: one row per reference page."""
    lines = [
        HEADER,
        "# API reference",
        "",
        "Generated from source. Each page lists the public classes, functions and type aliases of one package or",
        "first-level subpackage, with the file each lives in. Read the page before opening source files.",
        "",
        "| Page | Summary |",
        "|---|---|",
    ]
    lines += [f"| [`{page.import_name}`]({page.path.name}) | {page.summary} |" for page in pages]
    return "\n".join(lines) + "\n"


def build() -> dict[Path, str]:
    """Render every reference page, keyed by output path."""
    pages: dict[Path, str] = {}
    all_pages: list[Page] = []
    for package in discover_packages():
        files = module_files(package)
        for page in package_pages(package):
            all_pages.append(page)
            pages[page.path] = render_page(page, files)
    pages[OUTPUT_DIR / "index.md"] = render_index(all_pages)
    return pages


def main() -> int:
    """Write the pages, or with ``--check`` report stale ones and exit 1."""
    parser = argparse.ArgumentParser(description="Generate docs/reference/ from the workspace source.")
    parser.add_argument("--check", action="store_true", help="fail if docs/reference/ is out of date")
    options = parser.parse_args()

    pages = build()
    existing = set(OUTPUT_DIR.glob("*.md"))
    if options.check:
        stale = [p for p, text in pages.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        stale += sorted(existing - pages.keys())
        for path in stale:
            print(f"stale: {path.relative_to(ROOT).as_posix()}")
        if stale:
            print("run: uv run python scripts/generate_api_reference.py")
        return 1 if stale else 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in existing - pages.keys():
        path.unlink()
    for path, text in pages.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(pages)} pages to {OUTPUT_DIR.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
