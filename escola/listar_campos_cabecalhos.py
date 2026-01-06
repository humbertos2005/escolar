import sqlite3

nome_tabela = 'usuarios'

conn = sqlite3.connect('escola.db')
cursor = conn.cursor()

# Ver os campos (colunas)
cursor.execute(f"PRAGMA table_info({nome_tabela});")
colunas = cursor.fetchall()
print(f"Colunas da tabela {nome_tabela}:")
for c in colunas:
    print(f"- {c[1]} ({c[2]})")

# Ver alguns dados de exemplo
cursor.execute(f"SELECT * FROM {nome_tabela} LIMIT 3;")
linhas = cursor.fetchall()
print("Exemplo de linhas:")
for l in linhas:
    print(l)

conn.close()