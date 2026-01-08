import sqlite3

# Defina o nome do arquivo do banco de dados correto:
# Tente 'escola/db.sqlite' ou 'escola/escola. db' conforme o seu caso.
banco = 'escola.db'

conn = sqlite3.connect(banco)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(ficha_medida_disciplinar);")
colunas = cursor.fetchall()

print("Colunas da tabela ficha_medida_disciplinar:")
for col in colunas:
    print(f"{col[1]} ({col[2]})")

conn.close()