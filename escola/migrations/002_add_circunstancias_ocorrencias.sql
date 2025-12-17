-- Migration: adiciona colunas circunstancias_atenuantes e circunstancias_agravantes à tabela ocorrencias
-- Execute no seu banco (SQLite) ou use o script Python sugerido abaixo.

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;
-- Em SQLite ALTER TABLE ADD COLUMN é suportado; em outros SGBDs, adapte conforme necessidade.
ALTER TABLE ocorrencias ADD COLUMN circunstancias_atenuantes TEXT;
ALTER TABLE ocorrencias ADD COLUMN circunstancias_agravantes TEXT;
COMMIT;

-- Após criar as colunas, rode (opcional) para popular valores existentes:
-- UPDATE ocorrencias SET circunstancias_atenuantes = 'Não há' WHERE circunstancias_atenuantes IS NULL;
-- UPDATE ocorrencias SET circunstancias_agravantes = 'Não há' WHERE circunstancias_agravantes IS NULL;