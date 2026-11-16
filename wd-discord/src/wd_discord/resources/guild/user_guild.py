"""A guild in a user's guild list (https://docs.discord.com/developers/resources/user#get-current-user-guilds)."""

from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.snowflake import Snowflake


class UserGuild(DiscordModel):
    """One guild of ``GET /users/@me/guilds``: a user's, or a bot's, with the permissions they hold there."""

    id: Snowflake
    """Guild ID."""
    name: str
    """Guild name (2-100 characters)."""
    icon: ImageHash | None = None
    """The guild's icon hash."""
    banner: ImageHash | None = None
    """The guild's banner hash."""
    owner: bool
    """Whether the user is the owner of the guild."""
    permissions: PermissionsField
    """The user's total permissions in the guild, channel overwrites excluded."""
    features: list[str]
    """Enabled guild features; kept as strings so features Discord adds later don't fail validation."""
    approximate_member_count: int | None = None
    """Approximate number of members; only sent with ``with_counts``."""
    approximate_presence_count: int | None = None
    """Approximate number of online members; only sent with ``with_counts``."""
