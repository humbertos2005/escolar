BEGIN TRANSACTION;

-- Adiciona colunas usadas pelo formulário/handler FMD.
-- Atenção: se alguma coluna já existir, este script falhará com sqlite3.OperationalError.
ALTER TABLE ficha_medida_disciplinar ADD COLUMN data_falta TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN falta_disciplinar_ids TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN tipo_falta_list TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN relato TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN medida_aplicada TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN medida_aplicada_outra TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN comportamento_id INTEGER;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN pontuacao_id INTEGER;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN comparecimento INTEGER DEFAULT 1;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN prazo_comparecimento TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN atenuantes_id INTEGER;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN agravantes_id INTEGER;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN gestor_id INTEGER;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN created_at TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN updated_at TEXT;
ALTER TABLE ficha_medida_disciplinar ADD COLUMN baixa INTEGER DEFAULT 0;

COMMIT;