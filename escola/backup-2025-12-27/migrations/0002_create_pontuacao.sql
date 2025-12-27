-- Migration: cria tabelas para o módulo de pontuação disciplinar
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- tabela para armazenar valores/pesos das medidas (configurável via UI)
CREATE TABLE IF NOT EXISTS tabela_disciplinar_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT UNIQUE NOT NULL,
    valor REAL NOT NULL,
    descricao TEXT,
    atualizado_em DATETIME DEFAULT (datetime('now'))
);

-- Popula defaults se não existirem
INSERT OR IGNORE INTO tabela_disciplinar_config (chave, valor, descricao) VALUES
('advertencia_oral', -0.1, 'Perda por Advertência Oral (por ocorrência)'),
('advertencia_escrita', -0.3, 'Perda por Advertência Escrita (por ocorrência)'),
('suspensao_dia', -0.5, 'Perda por Suspensão de Sala (por dia)'),
('acao_educativa_dia', -1.0, 'Perda por Ação Educativa (por dia)'),
('elogio_individual', 0.5, 'Ganho por Elogio Individual (por ocorrência)'),
('elogio_coletivo', 0.3, 'Ganho por Elogio Coletivo (por ocorrência)');

-- tabela de pontuações por aluno/ano/bimestre
CREATE TABLE IF NOT EXISTS pontuacao_bimestral (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    bimestre INTEGER NOT NULL,
    pontuacao_inicial REAL NOT NULL DEFAULT 8.0,
    pontuacao_atual REAL NOT NULL DEFAULT 8.0,
    atualizado_em DATETIME DEFAULT (datetime('now')),
    UNIQUE(aluno_id, ano, bimestre)
);

-- histórico de alterações na pontuação (referência a ocorrências/FMDs)
CREATE TABLE IF NOT EXISTS pontuacao_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    ano INTEGER,
    bimestre INTEGER,
    ocorrencia_id INTEGER, -- referencia para ocorrencias.id (quando aplicável)
    fmd_id INTEGER,        -- referencia para ficha_medida_disciplinar.id (quando aplicável)
    tipo_evento TEXT,
    valor_delta REAL NOT NULL,
    observacao TEXT,
    criado_em DATETIME DEFAULT (datetime('now'))
);

COMMIT;