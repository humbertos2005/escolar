-- Criação da tabela bimestres
CREATE TABLE IF NOT EXISTS bimestres (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ano INTEGER NOT NULL,
  numero INTEGER NOT NULL,
  inicio DATE,
  fim DATE,
  responsavel_id INTEGER,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(ano, numero)
);