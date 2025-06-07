"""Migration script to modify AutoChannels table id field to use BigInteger and make it non-nullable."""

import sqlmodel


query = """
    ALTER TABLE auto_channels
    ALTER COLUMN id SET DATA TYPE BIGINT,
    ALTER COLUMN id SET NOT NULL
"""
sqlmodel.text(query)
