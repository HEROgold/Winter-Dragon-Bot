from discord import (
    AutoModAction,
    AutoModRule,
    AutoModRuleAction,
    AutoModRuleActionType,
    app_commands,
)

from bot import WinterDragon
from bot._types.cogs import Cog, GroupCog
from bot.config import config
from database.tables import Infractions as InfractionsDb


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class Infractions(GroupCog):
    """
    Track automod interaction from discord, keep track of amount of violations
    (Infractions) Ban users when X amount have reached. (Per guild configurable)

    TODO: Add automod rules to keep track of,
    TODO: On automod trigger, add infraction (Delete old ones)
    TODO: Make rules that can trigger an infraction.
        IE: Spamming the same message in more then X amount of channels
    """


    @Cog.listener()
    async def on_automod_rule_create(self, rule: AutoModRule) -> None:
        pass


    @Cog.listener()
    async def on_automod_rule_update(self, rule: AutoModRule) -> None:
        pass


    @Cog.listener()
    async def on_automod_rule_delete(self, rule: AutoModRule) -> None:
        pass


    @staticmethod
    def get_severity(action: AutoModRuleAction) -> int:
        # sourcery skip: assign-if-exp, reintroduce-else
        if action.type == AutoModRuleActionType.block_message:
            return 3
        if action.type == AutoModRuleActionType.timeout:
            return 2
        if action.type == AutoModRuleActionType.send_alert_message:
            return 1
        return 0


    @Cog.listener()
    async def on_automod_execution(self, execution: AutoModAction) -> None:
        action = execution.action
        duration = action.duration
        user = self.bot.get_user(execution.user_id)

        if user is None:
            self.logger.warning(f"User not found for {execution}")
            return

        severity = self.get_severity(action)
        self.logger.debug(f"{action.type=} {duration=} {user=}")
        InfractionsDb.add_infraction_count(user.id, severity)


async def setup(bot: WinterDragon) -> None:
    return
    await bot.add_cog(Infractions(bot))
