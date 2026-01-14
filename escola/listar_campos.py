import sqlite3

import os
db_path = os.environ.get("DATABASE_FILE", "escola.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(faltas_disciplinares);")
colunas = cursor.fetchall()

print("Campos da tabela 'faltas_disciplinares':")
for coluna in colunas:
    print("-", coluna[1])

conn.close()