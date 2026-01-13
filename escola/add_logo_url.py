import sqlite3

conn = sqlite3.connect('escola.db')
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE dados_escola ADD COLUMN logo_url TEXT;")
    conn.commit()
    print("Coluna logo_url adicionada com sucesso!")
except Exception as e:
    print("Erro ou a coluna já existe:", e)
finally:
    conn.close()