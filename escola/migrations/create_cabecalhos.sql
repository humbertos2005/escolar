-- Substituir/rodar este arquivo SQL no seu mecanismo de migração ou executar manualmente no DB (ex.: sqlite)
CREATE TABLE IF NOT EXISTS cabecalhos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estado TEXT,
    secretaria TEXT,
    coordenacao TEXT,
    escola TEXT,
    logo_estado TEXT,
    logo_escola TEXT,
    logo_prefeitura TEXT,
    descricao TEXT,
    created_at TEXT
);