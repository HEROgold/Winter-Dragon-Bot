
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.associations.guild_commands import GuildCommands


model = APIModel(GuildCommands)
router = model.router
