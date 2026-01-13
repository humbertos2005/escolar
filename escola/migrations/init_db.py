import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # USUARIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            email TEXT,
            nivel INTEGER,
            cargo TEXT,
            data_criacao TEXT
        );
    ''')

    # ALUNOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            nascimento DATE,
            turma TEXT
            -- acrescente outros campos conforme sua lógica, ex: responsavel, cpf, etc
        );
    ''')

    # TELEFONES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telefones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            numero TEXT
        );
    ''')

    # RFO_SEQUENCIA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rfo_sequencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT
        );
    ''')

    # FMD_SEQUENCIA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fmd_sequencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT
        );
    ''')

    # TIPOS_OCORRENCIA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_ocorrencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT
        );
    ''')

    # FALTAS_DISCIPLINARES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faltas_disciplinares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            descricao TEXT
        );
    ''')

    # ELOGIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elogios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            tipo TEXT,
            descricao TEXT,
            data TEXT
        );
    ''')

    # OCORRENCIAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            tipo_id INTEGER,
            data TEXT,
            descricao TEXT
            -- Adicione novas colunas conforme seu banco: circunstâncias, atenuantes, agravantes, etc
        );
    ''')

    # FICHA_MEDIDA_DISCIPLINAR
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ficha_medida_disciplinar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            medida TEXT,
            data TEXT
            -- acrescente campos para: data_falta, falta_disciplinar_ids, relato, comparecimento, etc
        );
    ''')

    # COMPORTAMENTOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comportamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT
        );
    ''')

    # CIRCUNSTANCIAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS circunstancias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT
        );
    ''')

    # OCORRENCIAS_ALUNOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            ocorrencia_id INTEGER
        );
    ''')

    # PONTUACAO_BIMESTRAL
    cursor.execute('''
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
    ''')

    # PONTUACAO_HISTORICO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pontuacao_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            ano INTEGER,
            bimestre INTEGER,
            ocorrencia_id INTEGER,
            fmd_id INTEGER,
            tipo_evento TEXT,
            valor_delta REAL NOT NULL,
            observacao TEXT,
            criado_em DATETIME DEFAULT (datetime('now'))
        );
    ''')

    # TABELA_DISCIPLINAR_CONFIG
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tabela_disciplinar_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT UNIQUE NOT NULL,
            valor REAL NOT NULL,
            descricao TEXT,
            atualizado_em DATETIME DEFAULT (datetime('now'))
        );
    ''')

    # BIMESTRES
    cursor.execute('''
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
    ''')

    # CABEÇALHOS
    cursor.execute('''
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
    ''')

    # DADOS_ESCOLA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dados_escola (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cabecalho_id INTEGER,
            escola TEXT,
            rua TEXT,
            numero TEXT,
            complemento TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            cnpj TEXT,
            diretor_nome TEXT,
            diretor_cpf TEXT,
            created_at TEXT,
            email_remetente TEXT,
            senha_email_app TEXT,
            telefone TEXT,
            dominio_sistema TEXT,
            nome_sistema TEXT
        );
    ''')

    # PRONTUARIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            descricao TEXT,
            data TEXT
        );
    ''')

    # OCORRENCIAS_FALTAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_faltas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER,
            falta_id INTEGER
        );
    ''')

    # OCORRENCIAS_REMOVIDAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_removidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER,
            motivo TEXT,
            data_remocao TEXT
        );
    ''')

    # PRONTUARIOS_HISTORY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuarios_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prontuario_id INTEGER,
            descricao TEXT,
            data TEXT
        );
    ''')

    # TACS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tacs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            data TEXT,
            baixa INTEGER DEFAULT 0
        );
    ''')

    # TAC_OBRIGACOES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tac_obrigacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tac_id INTEGER,
            obrigacao TEXT
        );
    ''')

    # TAC_PARTICIPANTES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tac_participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tac_id INTEGER,
            nome TEXT
        );
    ''')

    # ATAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            data TEXT
        );
    ''')

    # PRONTUARIO_RFO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuario_rfo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prontuario_id INTEGER,
            rfo TEXT
        );
    ''')

    # RECUPERACAO_SENHA_TOKENS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recuperacao_senha_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            token TEXT,
            data_criacao TEXT
        );
    ''')

    conn.commit()
    conn.close()
    print("Banco inicializado com sucesso!")

# Para rodar manualmente: python migrations/init_db.py
if __name__ == "__main__":
    init_db("escola.db")