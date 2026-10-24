"""Pin the database.ini and sentry.ini scopes: what a boot writes there, what resolves from them, and the check."""

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


SETTINGS = """
from wd_config import OperatorFiles
from wd_config.sentry import SentrySettings
from wd_db.settings import ApiTableSettings, DbUrl
from wd_db.constants import DATABASE_URL
result = {
    "driver": DbUrl.driver_name,
    "database": DbUrl.database,
    "username": DbUrl.username,
    "password": DbUrl.password,
    "host": DbUrl.host,
    "port": DbUrl.port,
    "url": DATABASE_URL.render_as_string(hide_password=False),
    "timeout": ApiTableSettings.request_timeout,
    "dsn": SentrySettings.dsn,
    "environment": SentrySettings.environment.value,
    "telemetry": SentrySettings.Telemetry,
    "unset": sorted(OperatorFiles.unset()),
}
"""


def test_fresh_boot_writes_database_and_sentry_ini(boot_config: BootConfig) -> None:
    """With neither file present, both are written with `!!` for the secrets, which the first-launch check lists."""
    boot = boot_config(SETTINGS)
    values = boot.values

    assert values["password"] == "!!"
    assert values["dsn"] == "!!"
    assert values["host"] == "postgres"
    assert values["port"] == 5432
    assert values["timeout"] == 10.0
    assert values["environment"] == "development"
    assert values["telemetry"] is True
    assert boot.files["database.ini"]["DbUrl"]["password"] == "!!"
    assert boot.files["database.ini"]["ApiTableSettings"]["request_timeout"] == "10.0"
    assert boot.files["sentry.ini"]["SentrySettings"]["dsn"] == "!!"
    assert "database.ini:DbUrl:password" in values["unset"]
    assert "sentry.ini:SentrySettings:dsn" in values["unset"]


def test_prewritten_values_resolve_and_build_the_url(boot_config: BootConfig) -> None:
    """Values already in database.ini and sentry.ini win; the database URL is assembled from them."""
    boot = boot_config(
        SETTINGS,
        files={
            "database.ini": (
                "[DbUrl]\ndriver_name = postgresql\ndatabase = wd\nusername = me\npassword = s3cret\n"
                "host = db.local\nport = 6543\n"
                "[ApiTableSettings]\nrequest_timeout = 2.5\n"
            ),
            "sentry.ini": (
                "[SentrySettings]\nTelemetry = False\ndsn = https://key@sentry.example/1\nenvironment = production\n"
            ),
        },
    )
    values = boot.values

    assert values["url"] == "postgresql://me:s3cret@db.local:6543/wd"
    assert values["timeout"] == 2.5
    assert values["dsn"] == "https://key@sentry.example/1"
    assert values["environment"] == "production"
    assert values["telemetry"] is False
    assert values["unset"] == []


def test_database_and_sentry_settings_stay_out_of_config_ini(boot_config: BootConfig) -> None:
    """No database or Sentry section lands in config.ini."""
    boot = boot_config(SETTINGS + "import winter_dragon.config\n")
    config = boot.files.get("config.ini", {})

    assert {"DbUrl", "ApiTableSettings", "SentrySettings"}.isdisjoint(config)


SENTRY_INIT = """
import sentry_sdk
from wd_config.sentry import SentrySettings
from {module} import Sentry
Sentry()
result = {{"dsn": SentrySettings.dsn, "resolved": SentrySettings.resolved_dsn(), "client_dsn": sentry_sdk.get_client().dsn}}
"""


def test_unset_dsn_initialises_sentry_without_a_dsn(boot_config: BootConfig) -> None:
    """The `!!` placeholder DSN counts as no DSN, so both Sentry set-ups start without one instead of failing."""
    for module in ("wd_core.sentry", "wd_discord.sentry"):
        boot = boot_config(SENTRY_INIT.format(module=module))

        assert boot.values == {"dsn": "!!", "resolved": None, "client_dsn": None}
