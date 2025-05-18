from discord import (
    AutoModAction,
    AutoModRule,
    AutoModRuleAction,
    AutoModRuleActionType,
    app_commands,
)
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.bot.settings import Settings
from winter_dragon.database.tables import Infractions as InfractionsDb


_rule_severities = {
    AutoModRuleActionType.block_message: 3,
    AutoModRuleActionType.timeout: 2,
    AutoModRuleActionType.send_alert_message: 1,
    AutoModRuleActionType.block_member_interactions: 0,
}

@app_commands.guilds(Settings.support_guild_id)
class Infractions(GroupCog):
    """Track automod interaction from discord, keep track of amount of violations
    (Infractions) Ban users when X amount have reached. (Per guild configurable).

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
        """Get the severity of the action."""
        return _rule_severities.get(action.type, 0)


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
    """Entrypoint for adding cogs."""
    return
    await bot.add_cog(Infractions(bot))
