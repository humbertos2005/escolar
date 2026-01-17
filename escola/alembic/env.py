from logging.config import fileConfig
import os
from dotenv import load_dotenv

from sqlalchemy import pool, create_engine
from alembic import context

# Carrega variáveis de ambiente
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Importa o objeto Base das models
from models_sqlalchemy import Base

# Instância da configuração do Alembic
config = context.config

# Configuração de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata das models para autogenerate
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Executa as migrations em modo 'offline'."""
    url = os.getenv("SQLALCHEMY_DATABASE_URI")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Executa as migrations em modo 'online'."""
    url = os.getenv("SQLALCHEMY_DATABASE_URI")
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
