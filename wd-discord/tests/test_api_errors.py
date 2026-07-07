"""Unit tests: Discord API error-response parsing."""
from __future__ import annotations

from wd_discord.errors.api import ApiErrorTree, ApiResponseError
from wd_errors import ErrorNode


def test_simple_error_has_no_error_tree() -> None:
    """A 401-style failure carries only ``code`` and ``message``."""
    error = ApiResponseError.model_validate({"code": 0, "message": "401: Unauthorized"})
    assert error.code == 0
    assert error.message == "401: Unauthorized"
    assert error.errors is None


def test_error_tree_parses_leaf_node() -> None:
    """An ``_errors`` leaf parses into an ErrorNode carrying the messages."""
    payload = {
        "code": 50035,
        "message": "Invalid Form Body",
        "errors": {
            "name": {
                "_errors": [
                    {"code": "BASE_TYPE_REQUIRED", "message": "This field is required"},
                ],
            },
        },
    }
    error = ApiResponseError.model_validate(payload)
    assert error.errors is not None

    root = error.errors.root
    assert isinstance(root, dict)
    field_tree = root["name"]
    assert isinstance(field_tree, ApiErrorTree)
    node = field_tree.root
    assert isinstance(node, ErrorNode)
    assert node.errors_list[0].code == "BASE_TYPE_REQUIRED"
    assert node.errors_list[0].message == "This field is required"


def test_error_tree_parses_nested_dict() -> None:
    """Nested field dicts exercise the recursive ApiErrorTree (model_rebuild)."""
    payload = {
        "code": 50035,
        "message": "Invalid Form Body",
        "errors": {
            "options": {
                "0": {
                    "name": {
                        "_errors": [
                            {"code": "BASE_TYPE_REQUIRED", "message": "Required"},
                        ],
                    },
                },
            },
        },
    }
    error = ApiResponseError.model_validate(payload)
    assert error.errors is not None

    tree: ApiErrorTree = error.errors
    for key in ("options", "0", "name"):
        root = tree.root
        assert isinstance(root, dict)
        tree = root[key]

    leaf = tree.root
    assert isinstance(leaf, ErrorNode)
    assert leaf.errors_list[0].code == "BASE_TYPE_REQUIRED"
