import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 1. Add current directory to path so we can import 'common'
sys.path.append(os.getcwd())

# 2. Import Local Models & DB Config
try:
    from common.models import Base
    from common.database import CORE_DB_URL
except ImportError as e:
    # Fallback if running from within backend/alembic/
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.models import Base
    from common.database import CORE_DB_URL

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = CORE_DB_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = CORE_DB_URL
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
