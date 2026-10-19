"""Files uploaded with a message (https://docs.discord.com/developers/reference#uploading-files).

A message with files is sent as ``multipart/form-data``: the JSON body goes in the ``payload_json`` field, file
``n`` in the ``files[n]`` field, and the body's ``attachments`` array names each file by that same ``n``.
"""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
lazy import json
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from wd_core.client import JsonPayload, RequestKwargs

    from wd_discord.responses import MessageData


@dataclass(frozen=True)
class File:
    """A file to upload with a message; Discord shows it as one of the message's attachments."""

    filename: str
    data: bytes
    _: KW_ONLY
    description: str | None = None
    """Alt text for the file, up to 1024 characters."""
    content_type: str = "application/octet-stream"


def attachments_payload(files: Sequence[File]) -> Generator[dict[str, object]]:
    """Yield the partial attachment object for each file, linking it to its ``files[n]`` form field by ``id``."""
    for index, file in enumerate(files):
        attachment: dict[str, object] = {"id": index, "filename": file.filename}
        if file.description is not None:
            attachment["description"] = file.description
        yield attachment


def request_body(payload: JsonPayload | MessageData, files: Sequence[File] = ()) -> RequestKwargs:
    """Return the request kwargs sending ``payload``: as JSON, or as ``multipart/form-data`` when there are ``files``."""
    if not files:
        return {"json": payload}
    return {
        "data": {"payload_json": json.dumps(payload)},
        "files": [(f"files[{index}]", (file.filename, file.data, file.content_type)) for index, file in enumerate(files)],
    }
