"""Alembic environment: compares the database with every table the app's cogs and the archive define."""

from alembic import context
from sqlmodel import SQLModel

import archive.models  # noqa: F401 - registers the archive's tables
from winter_dragon.cogs import import_cogs
from winter_dragon.migrations import include_object, render_item


import_cogs()

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=SQLModel.metadata,
    include_object=include_object,
    render_item=render_item,
    compare_type=True,
)
with context.begin_transaction():
    context.run_migrations()
