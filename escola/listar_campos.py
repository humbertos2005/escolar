import sqlite3

import os
db_path = os.environ.get("DATABASE_FILE", "escola.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(dados_escola);")
colunas = cursor.fetchall()

print("Campos da tabela 'dados_escola':")
for coluna in colunas:
    print("-", coluna[1])

conn.close()