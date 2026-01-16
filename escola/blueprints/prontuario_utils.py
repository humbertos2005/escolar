from datetime import datetime
from flask import session, current_app

def create_or_append_prontuario_por_rfo(db, ocorrencia_id, usuario=None):
    """
    Integra um RFO (ocorrencia_id) ao prontuário do aluno.
    - cria a tabela prontuario_rfo se não existir;
    - evita duplicação consultando prontuario_rfo;
    - cria ou atualiza prontuário acrescentando o registro formatado;
    - copia série/turma (e outros campos básicos) do aluno para o prontuário;
    - registra vínculo prontuario_rfo.
    Retorna (True, message) ou (False, message).
    """
    usuario = usuario or (session.get('username') if session else 'system')

    try:
        db.execute('''
            CREATE TABLE IF NOT EXISTS prontuario_rfo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ocorrencia_id INTEGER UNIQUE,
                prontuario_id INTEGER,
                created_at TEXT
            );
        ''')
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False, 'Falha ao garantir tabela prontuario_rfo'

    existing_link = db.execute('SELECT id, prontuario_id FROM prontuario_rfo WHERE ocorrencia_id = ?', (ocorrencia_id,)).fetchone()
    if existing_link:
        return False, 'RFO já integrado ao prontuário (vínculo existente)'

    r = db.execute('''
        SELECT o.*, a.id AS aluno_id, a.matricula AS aluno_matricula,
               a.nome AS aluno_nome, a.serie AS aluno_serie, a.turma AS aluno_turma,
               a.turno AS aluno_turno, a.telefone AS aluno_telefone, a.photo AS aluno_photo
        FROM ocorrencias o
        LEFT JOIN alunos a ON o.aluno_id = a.id
        WHERE o.id = ?
    ''', (ocorrencia_id,)).fetchone()

    if not r:
        return False, 'Ocorrência/RFO não encontrada'

    rdict = dict(r)
    rfo_numero = rdict.get('rfo_id') or rdict.get('rfo') or rdict.get('codigo') or f"RFO-{rdict.get('id','')}"
    data_oc = rdict.get('data_ocorrencia') or rdict.get('data') or rdict.get('created_at') or ''
    relato = rdict.get('relato_observador') or rdict.get('relato') or rdict.get('descricao') or ''
    tipo = rdict.get('tipo_ocorrencia_nome') or rdict.get('tipo') or ''
    item_desc = rdict.get('item_descricao') or rdict.get('descricao_item') or ''
    reinc = 'Sim' if rdict.get('reincidencia') else 'Não'
    medida_aplicada = rdict.get('medida_aplicada') or rdict.get('medida') or ''
    despacho = rdict.get('despacho_gestor') or rdict.get('despacho') or ''
    data_despacho = rdict.get('data_despacho') or rdict.get('data_tratamento') or ''

    registro_line = (f"RFO: {rfo_numero} | Data do RFO: {data_oc} | Relato: {relato} | "
                     f"Tipo: {tipo} | Item/Descrição: {item_desc} | É reincidência? {reinc} | "
                     f"Medida Aplicada: {medida_aplicada} | Despacho do Gestor: {despacho} | "
                     f"Data do Despacho: {data_despacho}")

    aluno_id = rdict.get('aluno_id')
    aluno_serie = rdict.get('aluno_serie') or None
    aluno_turma = rdict.get('aluno_turma') or None
    aluno_turno = rdict.get('aluno_turno') or None
    aluno_telefone = rdict.get('aluno_telefone') or None
    aluno_photo = rdict.get('aluno_photo') or None

    timestamp = datetime.utcnow().isoformat()

    existing = db.execute('SELECT * FROM prontuarios WHERE aluno_id = ? ORDER BY id DESC LIMIT 1', (aluno_id,)).fetchone()

    try:
        if existing:
            # salvar histórico se disponível
            try:
                from blueprints.formularios_prontuario import insert_prontuario_history
                insert_prontuario_history(db, existing, action='update_before_append', changed_by=usuario)
            except Exception:
                pass

            try:
                existing_rf = existing['registros_fatos'] if 'registros_fatos' in existing.keys() else (existing[10] if len(existing) > 10 else '')
            except Exception:
                existing_rf = existing[10] if existing and len(existing) > 10 else ''

            if existing_rf and registro_line:
                combined = f"{existing_rf}\n\n--- Adicionado em {timestamp} ---\n{registro_line}"
            elif registro_line:
                combined = f"--- Adicionado em {timestamp} ---\n{registro_line}"
            else:
                combined = existing_rf

            prontuario_id = existing['id'] if 'id' in existing.keys() else existing[0]

            # Atualizar prontuário: registros_fatos e também copiar serie/turma/turno/telefone se disponíveis
            db.execute('''
                UPDATE prontuarios
                SET registros_fatos = ?, deleted = 0, serie = ?, turma = ?, turno = ?, telefone1 = ?
                WHERE id = ?
            ''', (combined, aluno_serie, aluno_turma, aluno_turno, aluno_telefone, prontuario_id))
        else:
            # criar novo prontuário incluindo série/turma/turno/telefone se existirem
            db.execute('''
                INSERT INTO prontuarios (aluno_id, responsavel, email, registros_fatos, circunstancias_atenuantes, circunstancias_agravantes, created_at, deleted, serie, turma, turno, telefone1)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            ''', (int(aluno_id) if aluno_id else None, '', '', f"--- Adicionado em {timestamp} ---\n{registro_line}", '', '', timestamp, aluno_serie, aluno_turma, aluno_turno, aluno_telefone))
            prontuario_id = db.execute('SELECT last_insert_rowid() as id').fetchone()[0]

        # gravar vínculo (ocorrencia_id -> prontuario_id)
        db.execute('INSERT OR REPLACE INTO prontuario_rfo (ocorrencia_id, prontuario_id, created_at) VALUES (?, ?, ?)', (ocorrencia_id, prontuario_id, timestamp))

        return True, 'RFO integrado ao prontuário'
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        current_app.logger.exception('Erro em create_or_append_prontuario_por_rfo')
        return False, f'Erro ao integrar RFO ao prontuário: {e}'

