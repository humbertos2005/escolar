import os
from sqlalchemy import create_engine, inspect

# Caminho do banco pelo ambiente ou padrão
db_path = os.environ.get("DATABASE_FILE", "escola.db")
engine = create_engine(f"sqlite:///{db_path}")
inspector = inspect(engine)

print("Tabelas encontradas:")
for tabela in inspector.get_table_names():
    print("-", tabela)
