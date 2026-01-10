import sqlite3

conn = sqlite3.connect('escola.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS recuperacao_senha_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        token TEXT NOT NULL UNIQUE,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        expiracao DATETIME,
        usado INTEGER DEFAULT 0,
        data_uso DATETIME,
        FOREIGN KEY(user_id) REFERENCES usuarios(id)
    );
''')

conn.commit()
print("Tabela recuperacao_senha_tokens criada!")
conn.close()