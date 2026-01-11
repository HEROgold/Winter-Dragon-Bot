from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Session, col, select

from winter_dragon.database.channel_types import Tags
from winter_dragon.database.extension.model import DiscordID
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.guild import Guilds


class Channels(DiscordID, table=True):
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds))))
    name: str

    def link_tag(self, session: Session, tag: Tags) -> None:
        """Link this channel to a specific tag through the association table."""
        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        if session.exec(
            select(ChannelTag).where(
                ChannelTag.channel_id == self.id,
                ChannelTag.tag == tag,
            )
        ).first():
            return

        association = ChannelTag(
            channel_id=self.id,
            tag=tag,
        )
        session.add(association)
        session.commit()

    def unlink_tag(self, session: Session, tag: Tags | None = None) -> None:
        """Remove tag associations from this channel.

        If tag is None, removes all tag associations.
        Uses bulk delete for efficiency instead of fetching and deleting records individually.
        """
        from sqlalchemy import delete

        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        if tag is None:
            stmt = delete(ChannelTag).where(col(ChannelTag.channel_id) == self.id)
        else:
            stmt = delete(ChannelTag).where(
                col(ChannelTag.channel_id) == self.id,
                col(ChannelTag.tag) == tag,
            )

        session.exec(stmt)
        session.commit()

    def get_tags(self, session: Session) -> list[Tags]:
        """Get all tags associated with this channel."""
        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        associations = session.exec(select(ChannelTag).where(ChannelTag.channel_id == self.id)).all()

        return [assoc.tag for assoc in associations]

    def has_tag(self, session: Session, tag: Tags) -> bool:
        """Check if this channel has a specific tag."""
        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        return (
            session.exec(
                select(ChannelTag).where(
                    ChannelTag.channel_id == self.id,
                    ChannelTag.tag == tag,
                )
            ).first()
            is not None
        )

    def has_all_tags(self, session: Session, tags: list[Tags]) -> bool:
        """Check if this channel has all specified tags.

        Optimized to use a single database query instead of N queries.
        """
        if not tags:
            return True

        from sqlalchemy import func

        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        stmt = select(func.count()).where(
            ChannelTag.channel_id == self.id,
            col(ChannelTag.tag).in_(tags),
        )
        count = session.exec(stmt).one()
        return count == len(tags)

    @staticmethod
    def get_by_tag(session: Session, tag: Tags, guild_id: int | None = None) -> list["Channels"]:
        """Get all channels with a specific tag, optionally filtered by guild."""
        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        query = select(Channels).join(ChannelTag).where(ChannelTag.tag == tag)

        if guild_id is not None:
            query = query.where(Channels.guild_id == guild_id)

        return list(session.exec(query).all())

    @staticmethod
    def get_by_tags(
        session: Session,
        tags: list[Tags],
        guild_id: int | None = None,
        *,
        match_all: bool = False,
    ) -> list["Channels"]:
        """Get all channels with specific tags, optionally filtered by guild."""
        if not tags:
            return []

        from sqlalchemy import func

        from winter_dragon.database.tables.associations.channel_tags import ChannelTag

        stmt = select(col(ChannelTag.channel_id)).where(col(ChannelTag.tag).in_(tags))

        if guild_id is not None:
            stmt = stmt.join(Channels, col(ChannelTag.channel_id) == col(Channels.id)).where(col(Channels.guild_id) == guild_id)

        if match_all:
            stmt = stmt.group_by(col(ChannelTag.channel_id)).having(func.count(func.distinct(col(ChannelTag.tag))) == len(tags))
        else:
            stmt = stmt.distinct()

        channel_ids = list(session.exec(stmt).all())

        if not channel_ids:
            return []
        return list(session.exec(select(Channels).where(col(Channels.id).in_(channel_ids))).all())
