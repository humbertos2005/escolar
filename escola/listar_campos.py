import os
from sqlalchemy import create_engine, inspect

# Caminho do banco pelo ambiente ou padrão
db_path = os.environ.get("DATABASE_FILE", "escola.db")
engine = create_engine(f"sqlite:///{db_path}")
inspector = inspect(engine)

tabela = "recuperacao_senha_tokens"

print(f"Campos da tabela '{tabela}':")
for coluna in inspector.get_columns(tabela):
    print("-", coluna["name"])
