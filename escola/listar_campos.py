import sqlite3

conn = sqlite3.connect('escola.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(dados_escola);")
colunas = cursor.fetchall()

print("Campos da tabela 'dados_escola':")
for coluna in colunas:
    print("-", coluna[1])

conn.close()