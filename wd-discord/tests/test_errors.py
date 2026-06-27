"""Unit tests: Discord error parsing (API -> object) and the activity/platform enums."""
from __future__ import annotations

from wd_discord import Activity, ApiResponseError
from wd_discord.errors import Platform


def test_parse_simple_error() -> None:
    # Failures like 401 return only code + message, no per-field error tree.
    error = ApiResponseError.model_validate({"code": 0, "message": "401: Unauthorized"})
    assert error.code == 0
    assert error.message == "401: Unauthorized"
    assert error.errors is None


def test_parse_error_with_field_tree() -> None:
    payload = {
        "code": 50035,
        "message": "Invalid Form Body",
        "errors": {
            "activities": {
                "0": {
                    "platform": {
                        "_errors": [
                            {"code": "BASE_TYPE_CHOICES", "message": "Value must be one of the choices."},
                        ],
                    },
                },
            },
        },
    }
    error = ApiResponseError.model_validate(payload)
    assert error.code == 50035
    assert error.errors is not None


def test_activity_enum_values() -> None:
    assert Activity.PLAYING == 0
    assert Activity.STREAMING == 1
    assert Activity.LISTENING == 2
    assert Activity.WATCHING == 3
    assert Activity.CUSTOM == 4
    assert Activity.COMPETING == 5


def test_platform_enum_values() -> None:
    assert Platform.DESKTOP == "desktop"
    assert Platform.ANDROID == "android"
    assert Platform.IOS == "ios"
