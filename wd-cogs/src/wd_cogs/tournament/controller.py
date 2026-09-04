"""Tournament Cog for announcements and match status management."""

from __future__ import annotations


STATUS_SEQUENCE: tuple[MatchStatus, ...] = (
    MatchStatus.PRE,
    MatchStatus.FORMING_TEAMS,
    MatchStatus.BAN_PHASE,
    MatchStatus.SELECT_PHASE,
    MatchStatus.IN_PROGRESS,
    MatchStatus.POST,
    MatchStatus.FORFEIT,
)


class TournamentStatusView(discord.ui.View):
    """Interactive controls for a tournament status card."""

    def __init__(self, cog: Tournament, guild_id: int, *, timeout: float = 300.0) -> None:
        super().__init__(timeout=timeout)
        self.cog = cog
        self.guild_id = guild_id

    async def _ensure_manager(self, interaction: discord.Interaction) -> bool:
        user = interaction.user
        if user is None or not isinstance(user, discord.Member) or not user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server permissions to control tournament status.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Advance Phase", style=discord.ButtonStyle.primary, emoji="➡️")
    async def advance_phase(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[TournamentStatusView],
    ) -> None:
        if not await self._ensure_manager(interaction):
            return

        match = self.cog.get_match(self.guild_id)
        await self.cog.advance_match(match)

        embed = self.cog.build_status_embed(match, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Announce Status", style=discord.ButtonStyle.secondary, emoji="📣")
    async def announce_status(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[TournamentStatusView],
    ) -> None:
        if not await self._ensure_manager(interaction):
            return

        match = self.cog.get_match(self.guild_id)
        embed = self.cog.build_status_embed(match, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger, emoji="🔁")
    async def reset_status(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[TournamentStatusView],
    ) -> None:
        if not await self._ensure_manager(interaction):
            return

        match = self.cog.get_match(self.guild_id)
        await self.cog.set_match_status(match, MatchStatus.PRE)

        embed = self.cog.build_status_embed(match, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)


class Tournament(GroupCog, auto_load=True):
    """Manage tournament announcements and match state transitions."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Tournament cog."""
        super().__init__(**kwargs)

    def get_match(self, guild_id: int) -> MatchInformation:
        """Return the tracked match for a guild, creating a default record when needed."""
        return registry.get_match(guild_id)

    def build_status_embed(
        self,
        match: MatchInformation,
        guild: discord.Guild | None = None,
    ) -> discord.Embed:
        """Build a visually clear status card for a tournament match."""
        guild_name = guild.name if guild is not None else "Tournament"
        embed = discord.Embed(
            title=f"{guild_name} Tournament",
            description=self._status_description(match.status),
            color=self._status_color(match.status),
        )
        embed.add_field(name="Current Phase", value=match.status.name.replace("_", " ").title(), inline=True)
        embed.add_field(name="Teams", value=str(len(match.teams)), inline=True)
        embed.add_field(name="Controller", value=match.controller.__class__.__name__, inline=True)

        if match.teams:
            for index, team in enumerate(match.teams, start=1):
                roster = ", ".join(player.name for player in team.players) if team.players else "No players yet"
                embed.add_field(name=f"Team {index}", value=roster[:1024], inline=False)

        next_phase = self._next_status(match.status)
        embed.set_footer(text=f"Next phase: {next_phase.name.replace('_', ' ').title()}")
        return embed

    async def advance_match(self, match: MatchInformation) -> None:
        """Advance a match to the next phase, preferring the configured state machine when available."""
        next_status = self._next_status(match.status)
        await self._trigger_controller(match, self._next_event(match.status), next_status)

    async def set_match_status(self, match: MatchInformation, status: MatchStatus) -> None:
        """Set a match to a specific status."""
        await self._trigger_controller(match, self._event_for_status(status), status)

    async def _trigger_controller(
        self,
        match: MatchInformation,
        event: Events | None,
        fallback_status: MatchStatus,
    ) -> None:
        controller = match.controller
        trigger = getattr(controller, "trigger", None)

        if callable(trigger) and event is not None:
            result = trigger(event, Context())
            if inspect.isawaitable(result):
                await result

        match.status = fallback_status

    def _next_status(self, status: MatchStatus) -> MatchStatus:
        index = STATUS_SEQUENCE.index(status)
        if index >= len(STATUS_SEQUENCE) - 1:
            return STATUS_SEQUENCE[-1]
        return STATUS_SEQUENCE[index + 1]

    def _next_event(self, status: MatchStatus) -> Events | None:
        mapping: dict[MatchStatus, Events] = {
            MatchStatus.PRE: Events.FORM_TEAMS,
            MatchStatus.FORMING_TEAMS: Events.BAN,
            MatchStatus.BAN_PHASE: Events.SELECT,
            MatchStatus.SELECT_PHASE: Events.START,
            MatchStatus.IN_PROGRESS: Events.GAME_ENDED,
            MatchStatus.POST: Events.FORFEIT,
        }
        return mapping.get(status)

    def _event_for_status(self, status: MatchStatus) -> Events | None:
        reverse_mapping: dict[MatchStatus, Events] = {
            MatchStatus.PRE: Events.FORM_TEAMS,
            MatchStatus.FORMING_TEAMS: Events.FORM_TEAMS,
            MatchStatus.BAN_PHASE: Events.BAN,
            MatchStatus.SELECT_PHASE: Events.SELECT,
            MatchStatus.IN_PROGRESS: Events.START,
            MatchStatus.POST: Events.GAME_ENDED,
            MatchStatus.FORFEIT: Events.FORFEIT,
        }
        return reverse_mapping.get(status)

    def _status_description(self, status: MatchStatus) -> str:
        descriptions = {
            MatchStatus.PRE: "Ready to open registration and publish the next match card.",
            MatchStatus.FORMING_TEAMS: "Players are being grouped into teams.",
            MatchStatus.BAN_PHASE: "Teams are banning before the draft continues.",
            MatchStatus.SELECT_PHASE: "Teams are selecting their picks.",
            MatchStatus.IN_PROGRESS: "The game is live.",
            MatchStatus.POST: "The match ended and results can be summarized.",
            MatchStatus.FORFEIT: "The match ended by forfeit.",
        }
        return descriptions[status]

    def _status_color(self, status: MatchStatus) -> discord.Color:
        colors = {
            MatchStatus.PRE: discord.Color.dark_grey(),
            MatchStatus.FORMING_TEAMS: discord.Color.blurple(),
            MatchStatus.BAN_PHASE: discord.Color.gold(),
            MatchStatus.SELECT_PHASE: discord.Color.teal(),
            MatchStatus.IN_PROGRESS: discord.Color.green(),
            MatchStatus.POST: discord.Color.brand_red(),
            MatchStatus.FORFEIT: discord.Color.red(),
        }
        return colors[status]

    @app_commands.command(name="status", description="Show the current tournament status")
    @app_commands.guild_only()
    async def tournament_status(self, interaction: discord.Interaction) -> None:
        """Show the current tournament status in an ephemeral message with controls for advancing and announcing."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        match = self.get_match(guild.id)
        embed = self.build_status_embed(match, guild)
        view = TournamentStatusView(self, guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="announce", description="Announce the current tournament card in this channel")
    @app_commands.guild_only()
    async def tournament_announce(self, interaction: discord.Interaction) -> None:
        """Announce the current tournament status in the channel, without controls."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        match = self.get_match(guild.id)
        embed = self.build_status_embed(match, guild)
        view = TournamentStatusView(self, guild.id)
        await interaction.response.send_message(embed=embed, view=view)
