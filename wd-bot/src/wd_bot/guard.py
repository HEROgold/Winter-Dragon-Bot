"""The one guard command, component and listener dispatch run their handler through.

A handler that refuses (raises :class:`~wd_errors.Refused`) has its refusal logged and, when someone is waiting on an
interaction, told to them privately. A handler that raises anything else has the exception logged and, for an
interaction, gets the ephemeral :func:`error_embed` reply, so an interaction never goes unanswered.
"""

lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin
lazy from wd_discord.color import Color
lazy from wd_discord.embed import Embed, EmbedFooter
lazy from wd_errors import Refused

lazy from wd_bot.checks import answer_refusal


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from wd_discord import AnyInteraction
    lazy from wd_discord.snowflake import Snowflake


COMMAND_ERROR_REPLY = "Something went wrong running this command."
"""The text of the ephemeral reply sent when a command or component handler raises."""
ERROR_COLOR = 0xFF0000
"""The color of that reply."""


def error_embed(interaction_id: Snowflake) -> Embed:
    """Return the reply to the interaction ``interaction_id`` whose handler raised.

    The exception's log line names the same interaction ID, so a user's report finds it.
    """
    return Embed(
        title="Something went wrong",
        description=COMMAND_ERROR_REPLY,
        color=Color(ERROR_COLOR),
        footer=EmbedFooter(text=f"If it keeps happening, tell the bot's owners this ID: {interaction_id}"),
    )


class DispatchGuard(LoggerMixin):
    """Runs a handler, turning a refusal or an unexpected exception into the right reply and log entry."""

    async def run(
        self,
        handler: str,
        call: Callable[[], Awaitable[object]],
        interaction: AnyInteraction | None = None,
    ) -> bool:
        """Await ``call()``, the handler described as ``handler`` (e.g. ``"command 'ping'"``).

        ``interaction`` is who to answer, if anyone: a listener has nobody waiting. Returns ``True`` when the handler
        completed or refused, ``False`` when it raised.
        """
        about = handler if interaction is None else f"{handler} (interaction {interaction.id})"
        try:
            await call()
        except Refused as refused:
            self.logger.info(t"{about} refused: {refused.message} ({refused.cause})")
            if interaction is not None:
                await answer_refusal(interaction, refused)
        except Exception:
            # herogold's Logger.exception() logs any message as a tuple's repr, so error() carries the traceback.
            self.logger.error(t"Unhandled exception in {about}", exc_info=True)  # noqa: G201
            if interaction is not None:
                await interaction.respond(embeds=[error_embed(interaction.id)], ephemeral=True)
            return False
        return True


dispatch_guard = DispatchGuard()
"""The guard every command, component and listener dispatch goes through."""
