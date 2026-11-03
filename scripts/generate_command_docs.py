# ruff: noqa: INP001 - a standalone repo script, not part of any package
"""Generate a documentation page for each command group the bot's cogs define, in docs/commands/.

The options, permissions and where a command works come from the cogs' command metadata, so a changed option
shows up on the page at the next run. What the metadata can't say (what the feature is for, setup, and an example of
the bot's reply) is written by hand in ``docs/commands/examples.toml``. ``--check`` fails when a page is stale, or
when a command or group has no entry there, or an entry names nothing the bot has.

Usage (from the repo root):

    uv run python scripts/generate_command_docs.py           # regenerate docs/commands/
    uv run python scripts/generate_command_docs.py --check   # verify it's up to date (pre-commit)
"""

lazy import argparse
lazy import sys
lazy import tomllib
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from wd_bot.cogs import GroupCog
    from wd_bot.commands import Command


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "commands"
EXAMPLES = OUTPUT_DIR / "examples.toml"

HEADER = "<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->\n"

OPTION_TYPES = {
    "STRING": "text",
    "INTEGER": "whole number",
    "BOOLEAN": "yes or no",
    "USER": "member",
    "CHANNEL": "channel",
    "ROLE": "role",
    "MENTIONABLE": "member or role",
    "NUMBER": "number",
}
REPLY_KINDS = {
    "embed": "an embed",
    "text": "a message",
    "image": "an image",
    "card": "a card with buttons",
}


@dataclass(frozen=True)
class Problem:
    """Something wrong with ``examples.toml`` or a generated page."""

    message: str


def groups() -> list[type[GroupCog]]:
    """Return every command group the app's cogs define, by name."""
    from wd_bot.cogs import GroupCog  # noqa: PLC0415

    from winter_dragon import cogs  # noqa: PLC0415

    cogs.import_cogs()
    pending, found = list(GroupCog.__subclasses__()), list[type[GroupCog]]()
    while pending:
        cog = pending.pop()
        pending.extend(cog.__subclasses__())
        if cog.__module__.startswith(f"{cogs.__name__}."):
            found.append(cog)
    return sorted(found, key=lambda group: group.group_definition.name)


def permission_names(value: object) -> str:
    """Return the names of the permission flags in ``value``, as words."""
    from wd_discord.permissions import Permissions  # noqa: PLC0415

    flags = Permissions(int(value))  # pyrefly: ignore[bad-argument-type]
    names = [
        flag.name.replace("_", " ").title().replace("Guild", "Server")
        for flag in Permissions
        if flag.name and flag in flags and flag.value
    ]
    return ", ".join(names)


def who_can_run(group: type[GroupCog], command: Command, custom: str | None) -> str:
    """Say who may run ``command``: ``custom`` when written by hand, else what its permissions and contexts say."""
    if custom:
        return custom
    required = command.requires or group.group_definition.default_member_permissions or command.default_member_permissions
    where = "in a server" if group.guild_only() or command.guild_only else "in a server or in DMs"
    if required:
        return f"Members with {permission_names(required)}, {where}."
    return f"Anyone {where}." if where == "in a server" else f"Anyone, {where}."


def option_row(option: object) -> str:
    """Return the table row for one command option."""
    name = f"`{option.name}`"  # pyrefly: ignore[missing-attribute]
    kind = OPTION_TYPES.get(option.type.name, option.type.name.lower())  # pyrefly: ignore[missing-attribute]
    required = "yes" if option.required else "no"  # pyrefly: ignore[missing-attribute]
    limits = []
    min_length, max_length = getattr(option, "min_length", None), getattr(option, "max_length", None)
    min_value, max_value = getattr(option, "min_value", None), getattr(option, "max_value", None)
    if min_length is not None or max_length is not None:
        limits.append(
            f"{min_length} to {max_length} characters"
            if min_length and max_length
            else f"up to {max_length} characters"
            if max_length
            else f"at least {min_length} characters",
        )
    if min_value is not None or max_value is not None:
        limits.append(
            f"{min_value} to {max_value}"
            if min_value is not None and max_value is not None
            else (f"at least {min_value}" if min_value is not None else f"at most {max_value}"),
        )
    description = (option.description or "").rstrip(".")  # pyrefly: ignore[missing-attribute]
    if limits:
        description = f"{description} ({', '.join(limits)})" if description else ", ".join(limits)
    return f"| {name} | {kind} | {required} | {description} |"


def command_section(group: type[GroupCog], command: Command, entry: dict[str, object]) -> list[str]:
    """Return the page lines for ``command``: what it does, its options, who can run it and an example reply."""
    path = f"/{group.group_definition.name} {command.name}"
    lines = [f"## {path} {{#{command.name}}}", "", f"{command.description}.", ""]
    if about := entry.get("about"):
        lines += [str(about).strip(), ""]
    options = list(command.options())
    if options:
        lines += ["| Option | Type | Required | What it is |", "| --- | --- | --- | --- |", *map(option_row, options), ""]
    else:
        lines += ["It takes no options.", ""]
    lines += [f"**Who can run it:** {who_can_run(group, command, entry.get('who'))}", ""]  # pyrefly: ignore[bad-argument-type]
    usage = entry.get("usage")
    reply = str(entry.get("reply", "")).strip()
    kind = REPLY_KINDS[str(entry.get("kind", "text"))]
    private = "only you see it" if entry.get("private") else "everyone in the channel sees it"
    lines += ['!!! example "Example"', f"    You type `{usage}`." if usage else "    You type the command.", ""]
    lines += [f"    The bot answers with {kind}; {private}:", ""]
    lines += [f"    > {row}" if row else "    >" for row in reply.splitlines()]
    lines.append("")
    return lines


def group_page(group: type[GroupCog], entry: dict[str, object]) -> str:
    """Return the markdown page of ``group``: what it is for, its setup and every command in it."""
    definition = group.group_definition
    commands = sorted(group.commands(), key=lambda command: command.name)
    lines = [HEADER, f"# /{definition.name}", "", f"{definition.description}.", ""]
    if about := entry.get("about"):
        lines += [str(about).strip(), ""]
    if setup := entry.get("setup"):
        lines += ["## Setup", "", str(setup).strip(), ""]
    lines += ["## Commands", ""]
    lines += [f"- [`/{definition.name} {command.name}`](#{command.name}): {command.description}" for command in commands]
    lines.append("")
    commands_entries = entry.get("commands", {})
    for command in commands:
        lines += command_section(group, command, commands_entries.get(command.name, {}))  # pyrefly: ignore[missing-attribute]
    return "\n".join(lines).rstrip() + "\n"


def index_page(pages: list[type[GroupCog]]) -> str:
    """Return the index page linking every group page."""
    lines = [
        HEADER,
        "# Commands",
        "",
        "What the bot does in a server, one page per command group. Each page lists the",
        "options of every command, who can run it, and an example of the bot's reply.",
        "",
    ]
    lines += [
        f"- [`/{group.group_definition.name}`]({group.group_definition.name}.md): {group.group_definition.description}"
        for group in pages
    ]
    return "\n".join(lines) + "\n"


def entries() -> dict[str, dict[str, object]]:
    """Read the hand-written entries, by group name."""
    return tomllib.loads(EXAMPLES.read_text(encoding="utf-8"))


def coverage(pages: list[type[GroupCog]], written: dict[str, dict[str, object]]) -> list[Problem]:
    """Return what is missing from, or unknown to, the hand-written entries."""
    problems = []
    names = {group.group_definition.name: group for group in pages}
    problems.extend(
        Problem(f"examples.toml has [{name}], but the bot has no /{name} group.") for name in written.keys() - names.keys()
    )
    for name, group in names.items():
        entry = written.get(name)
        if entry is None:
            problems.append(Problem(f"examples.toml has no [{name}] entry."))
            continue
        if not entry.get("about"):
            problems.append(Problem(f"[{name}] has no `about`."))
        commands = entry.get("commands", {})
        known = {command.name for command in group.commands()}
        problems.extend(Problem(f"[{name}.commands.{missing}] has no matching command.") for missing in commands.keys() - known)
        problems.extend(
            Problem(f"[{name}.commands.{command}] has no `reply`.")
            for command in sorted(known)
            if not commands.get(command, {}).get("reply")
        )
    return problems


def expected() -> dict[Path, str]:
    """Return every generated page by path."""
    pages = groups()
    written = entries()
    files = {
        OUTPUT_DIR / f"{group.group_definition.name}.md": group_page(group, written.get(group.group_definition.name, {}))
        for group in pages
    }
    files[OUTPUT_DIR / "index.md"] = index_page(pages)
    return files


def main() -> int:
    """Regenerate the pages, or with ``--check`` verify them; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when a page is stale or an entry is missing",
    )
    args = parser.parse_args()
    problems = coverage(groups(), entries())
    for problem in problems:
        sys.stderr.write(f"{problem.message}\n")
    if problems:
        return 1
    files = expected()
    if args.check:
        stale = [path for path, text in files.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        stale += [path for path in OUTPUT_DIR.glob("*.md") if path not in files]
        for path in stale:
            sys.stderr.write(f"{path.relative_to(ROOT)} is out of date; run: uv run python scripts/generate_command_docs.py\n")
        return 1 if stale else 0
    for path in OUTPUT_DIR.glob("*.md"):
        if path not in files:
            path.unlink()
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
