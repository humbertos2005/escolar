import sqlite3

import os
db_path = os.environ.get("DATABASE_FILE", "escola.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tabelas = cursor.fetchall()

print("Tabelas encontradas:")
for tabela in tabelas:
    print("-", tabela[0])

conn.close()