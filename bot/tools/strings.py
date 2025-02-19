from typing import Any


def codeblock(language: str, text: Any) -> str:  # noqa: ANN401
    return f"```{language}\n{text}\n```"
