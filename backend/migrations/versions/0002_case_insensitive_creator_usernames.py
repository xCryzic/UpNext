"""Enforce case-insensitive creator usernames."""
from alembic import op
import sqlalchemy as sa

revision = "0002_case_insensitive_creator_usernames"
down_revision = "0001_initial_upnext_schema"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicates = bind.execute(sa.text("""
        SELECT lower(username) AS normalized_username
        FROM creators
        GROUP BY lower(username)
        HAVING count(*) > 1
    """)).scalars().all()
    if duplicates:
        raise RuntimeError("Cannot enforce case-insensitive usernames until duplicate usernames are resolved.")
    existing = {index["name"] for index in sa.inspect(bind).get_indexes("creators")}
    if "uq_creators_username_lower" not in existing:
        op.create_index("uq_creators_username_lower", "creators", [sa.text("lower(username)")], unique=True)


def downgrade():
    bind = op.get_bind()
    existing = {index["name"] for index in sa.inspect(bind).get_indexes("creators")}
    if "uq_creators_username_lower" in existing:
        op.drop_index("uq_creators_username_lower", table_name="creators")
