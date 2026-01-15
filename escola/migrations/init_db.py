import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')
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
            turma TEXT,
            responsavel TEXT,
            cpf TEXT,
            usuario_cadastro_id INTEGER,
            email TEXT,
            telefone TEXT,
            data_matricula TEXT,
            FOREIGN KEY (usuario_cadastro_id) REFERENCES usuarios(id)
        );
    ''')

    # TELEFONES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telefones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            numero TEXT,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id) ON DELETE CASCADE
        );
    ''')

    # RFO_SEQUENCIA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rfo_sequencia (
            ano TEXT PRIMARY KEY,
            numero INTEGER NOT NULL
        );
    ''')

    # FMD_SEQUENCIA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fmd_sequencia (
            ano TEXT PRIMARY KEY,
            numero INTEGER NOT NULL
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
            natureza TEXT,
            descricao TEXT,
            data_criacao TEXT
        );
    ''')

    # ELOGIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elogios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            tipo TEXT,
            descricao TEXT,
            data_criacao TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE
        );
    ''')

    # OCORRENCIAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            tipo_ocorrencia_id INTEGER,
            data_ocorrencia TEXT,
            observador_id INTEGER,
            relato_observador TEXT,
            advertencia_oral TEXT,
            material_recolhido TEXT,
            data_registro TEXT,
            hora_ocorrencia TEXT,
            local_ocorrencia TEXT,
            infracao_id INTEGER,
            descricao_detalhada TEXT,
            status TEXT,
            data_tratamento TEXT,
            tipo_falta TEXT,
            medida_aplicada TEXT,
            observacao_tratamento TEXT,
            reincidencia INTEGER,
            responsavel_registro_id INTEGER,
            observador_nome TEXT,
            relato_estudante TEXT,
            despacho_gestor TEXT,
            data_despacho TEXT,
            falta_disciplinar_id INTEGER,
            tipo_ocorrencia_text TEXT,
            subtipo_elogio TEXT,
            tratamento_tipo TEXT,
            observador_advertencia_oral TEXT,
            pontos_aplicados INTEGER,
            falta_ids_csv TEXT,
            circunstancias_atenuantes TEXT,
            circunstancias_agravantes TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
            FOREIGN KEY (tipo_ocorrencia_id) REFERENCES tipos_ocorrencia(id),
            FOREIGN KEY (falta_disciplinar_id) REFERENCES faltas_disciplinares(id),
            FOREIGN KEY (responsavel_registro_id) REFERENCES usuarios(id),
            FOREIGN KEY (observador_id) REFERENCES usuarios(id)
        );
    ''')

    # FICHA_MEDIDA_DISCIPLINAR
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ficha_medida_disciplinar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fmd_id TEXT,
            aluno_id INTEGER,
            rfo_id TEXT,
            data_fmd TEXT,
            tipo_falta TEXT,
            medida_aplicada TEXT,
            descricao_falta TEXT,
            observacoes TEXT,
            responsavel_id INTEGER,
            data_registro TEXT,
            status TEXT,
            data_falta TEXT,
            falta_disciplinar_ids TEXT,
            tipo_falta_list TEXT,
            relato TEXT,
            medida_aplicada_outra TEXT,
            comportamento_id INTEGER,
            pontuacao_id INTEGER,
            comparecimento TEXT,
            prazo_comparecimento TEXT,
            atenuantes_id TEXT,
            agravantes_id TEXT,
            gestor_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            baixa INTEGER,
            relato_faltas TEXT,
            itens_faltas_ids TEXT,
            comparecimento_responsavel TEXT,
            atenuantes TEXT,
            agravantes TEXT,
            pontos_aplicados INTEGER,
            email_enviado_data TEXT,
            email_enviado_para TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (comportamento_id) REFERENCES comportamentos(id),
            FOREIGN KEY (pontuacao_id) REFERENCES pontuacao_bimestral(id),
            FOREIGN KEY (gestor_id) REFERENCES usuarios(id)
        );
    ''')

    # COMPORTAMENTOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comportamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            pontuacao INTEGER,
            data_criacao TEXT
        );
    ''')

    # CIRCUNSTANCIAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS circunstancias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            descricao TEXT,
            data_criacao TEXT
        );
    ''')

    # OCORRENCIAS_ALUNOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            ocorrencia_id INTEGER,
            criado_em TEXT,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id) ON DELETE CASCADE
        );
    ''')

    # PONTUACAO_BIMESTRAL
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pontuacao_bimestral (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            ano TEXT NOT NULL,
            bimestre INTEGER NOT NULL,
            pontuacao_inicial REAL NOT NULL DEFAULT 8.0,
            pontuacao_atual REAL NOT NULL DEFAULT 8.0,
            atualizado_em TEXT,
            UNIQUE(aluno_id, ano, bimestre),
            FOREIGN KEY(aluno_id) REFERENCES alunos(id) ON DELETE CASCADE
        );
    ''')

    # PONTUACAO_HISTORICO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pontuacao_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            ano TEXT,
            bimestre INTEGER,
            ocorrencia_id INTEGER,
            fmd_id INTEGER,
            tipo_evento TEXT,
            valor_delta REAL NOT NULL,
            observacao TEXT,
            criado_em TEXT,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id),
            FOREIGN KEY(fmd_id) REFERENCES ficha_medida_disciplinar(id)
        );
    ''')

    # TABELA_DISCIPLINAR_CONFIG
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tabela_disciplinar_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT UNIQUE NOT NULL,
            valor REAL NOT NULL,
            descricao TEXT,
            atualizado_em TEXT
        );
    ''')

    # BIMESTRES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bimestres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano TEXT NOT NULL,
            numero INTEGER NOT NULL,
            inicio TEXT,
            fim TEXT,
            responsavel_id INTEGER,
            criado_em TEXT,
            UNIQUE(ano, numero),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
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
            nome_sistema TEXT,
            FOREIGN KEY(cabecalho_id) REFERENCES cabecalhos(id)
        );
    ''')

    # PRONTUARIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            registros_fatos TEXT,
            circunstancias_atenuantes TEXT,
            circunstancias_agravantes TEXT,
            created_at TEXT,
            numero TEXT,
            deleted INTEGER,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id) ON DELETE CASCADE
        );
    ''')

    # OCORRENCIAS_FALTAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_faltas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER,
            falta_id INTEGER,
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id) ON DELETE CASCADE,
            FOREIGN KEY(falta_id) REFERENCES faltas_disciplinares(id) ON DELETE CASCADE
        );
    ''')

    # OCORRENCIAS_REMOVIDAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocorrencias_removidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            motivo TEXT,
            removed_at TEXT,
            FOREIGN KEY(original_id) REFERENCES ocorrencias(id)
        );
    ''')

    # PRONTUARIOS_HISTORY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuarios_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prontuario_id INTEGER,
            descricao TEXT,
            data TEXT,
            FOREIGN KEY(prontuario_id) REFERENCES prontuarios(id) ON DELETE CASCADE
        );
    ''')

    # TACS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tacs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT,
            aluno_id INTEGER,
            cabecalho_id INTEGER,
            escola_text TEXT,
            serie TEXT,
            turma TEXT,
            responsavel TEXT, 
            diretor_nome TEXT,
            fato TEXT,
            prazo TEXT,
            created_at TEXT,
            updated_at TEXT,
            deleted INTEGER,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id),
            FOREIGN KEY(cabecalho_id) REFERENCES cabecalhos(id)
        );
    ''')

    # TAC_OBRIGACOES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tac_obrigacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tac_id INTEGER,
            descricao TEXT,
            ordem INTEGER,
            FOREIGN KEY(tac_id) REFERENCES tacs(id) ON DELETE CASCADE
        );
    ''')

    # TAC_PARTICIPANTES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tac_participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tac_id INTEGER,
            nome TEXT,
            cargo TEXT,
            ordem INTEGER,
            FOREIGN KEY(tac_id) REFERENCES tacs(id) ON DELETE CASCADE
        );
    ''')

    # ATAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            aluno_nome TEXT,
            serie_turma TEXT,
            numero TEXT,
            ano TEXT,
            conteudo TEXT,
            created_at TEXT,
            updated_at TEXT,
            created_by TEXT,
            participants_json TEXT,
            FOREIGN KEY(aluno_id) REFERENCES alunos(id)
        );
    ''')

    # PRONTUARIO_RFO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuario_rfo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocorrencia_id INTEGER,
            prontuario_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(prontuario_id) REFERENCES prontuarios(id),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id)
        );
    ''')

    # RECUPERACAO_SENHA_TOKENS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recuperacao_senha_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT,
            token TEXT,
            data_criacao TEXT,
            expiracao TEXT,
            usado INTEGER,
            data_uso TEXT,
            FOREIGN KEY(user_id) REFERENCES usuarios(id)
        );
    ''')

    conn.commit()
    conn.close()
    print("Banco inicializado com sucesso!")

import os
if __name__ == "__main__":
    db_path = os.environ.get("DATABASE_FILE", "escola.db")
    init_db(db_path)