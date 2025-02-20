"""Module that contains the definitions of the tables in the database."""

from sqlmodel import Field


USERS_ID = "users.id"
CHANNELS_ID = "channels.id"
GUILDS_ID = "guilds.id"
COMMANDS_ID = "commands.id"
COMMAND_GROUPS_ID = "command_groups.id"
HANGMEN_ID = "hangmen.id"
ROLES_ID = "roles.id"
POLLS_ID = "polls.id"
LOBBIES_ID = "lobbies.id"
GAMES_NAME = "games.name"
MESSAGES_ID = "messages.id"
LOBBY_STATUS = "lobby_status.status"
AUTO_INCREMENT_ID: int | None = Field(default=None, primary_key=True)
