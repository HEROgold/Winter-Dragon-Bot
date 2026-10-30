"""Unit tests: Discord error parsing (API -> object) and the activity type enum."""

lazy from wd_discord import ActivityType, ApiResponseError
lazy from wd_discord.errors import ErrorCode


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


def test_activity_type_values() -> None:
    assert ActivityType.PLAYING == 0
    assert ActivityType.STREAMING == 1
    assert ActivityType.LISTENING == 2
    assert ActivityType.WATCHING == 3
    assert ActivityType.CUSTOM == 4
    assert ActivityType.COMPETING == 5


def test_field_error_code_parses_into_error_code() -> None:
    payload = {
        "code": 50035,
        "message": "Invalid Form Body",
        "errors": {"name": {"_errors": [{"code": "BASE_TYPE_REQUIRED", "message": "Required"}]}},
    }
    error = ApiResponseError.model_validate(payload)
    assert error.errors is not None
    assert [message.code for message in error.errors] == [ErrorCode.BASE_TYPE_REQUIRED]
