"""Utility functions for string formatting."""
from typing import Any


def codeblock(language: str, text: Any) -> str:  # noqa: ANN401
    """Format a string as a code block with syntax highlighting."""
    return f"```{language}\n{text}\n```"
