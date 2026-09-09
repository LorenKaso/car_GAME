import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context
from app.db.base import Base
from app.models import entities  # noqa: F401

load_dotenv()
url = os.environ.get("MIGRATION_DATABASE_URL")
if not url:
    raise RuntimeError(
        "MIGRATION_DATABASE_URL is required; migrations never use runtime credentials"
    )


def configure(connection=None):
    context.configure(
        connection=connection,
        url=url,
        target_metadata=Base.metadata,
        include_schemas=True,
        version_table_schema="game",
        literal_binds=connection is None,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    configure()
else:
    with create_engine(url, poolclass=pool.NullPool).connect() as connection:
        if not connection.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')"
        ).scalar():
            raise RuntimeError("Enable PostGIS with a DBA account before running migrations")
        connection.commit()
        configure(connection)
