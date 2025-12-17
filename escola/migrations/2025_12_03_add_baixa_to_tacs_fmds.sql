-- Migration: adicionar coluna "baixa" (0/1) em tacs e fmds
BEGIN TRANSACTION;

-- tacs: já tem deleted, adicionamos baixa para arquivamento administrativo
ALTER TABLE tacs ADD COLUMN baixa INTEGER DEFAULT 0;

-- fmds: caso não tenha coluna equivalente (ajuste o nome da tabela se for diferente)
-- Substitua 'fmds' pelo nome correto da tabela das Fichas de Medida Disciplinar se for outro.
ALTER TABLE fmds ADD COLUMN baixa INTEGER DEFAULT 0;

COMMIT;