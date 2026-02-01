from datetime import datetime
from flask import session, current_app

def create_or_append_prontuario_por_rfo(db, ocorrencia_id, usuario=None):
    """
    Integra um RFO (ocorrencia_id) ao prontuário do aluno. Usa ORM/SQLAlchemy.
    - Evita duplicação consultando ProntuarioRFO.
    - Cria ou atualiza Prontuario, acrescentando o registro formatado.
    - Copia série/turma/turno/telefone do aluno para o prontuário.
    - Registra o vínculo ProntuarioRFO.
    Retorna (True, message) ou (False, message).
    """
    if not usuario:
        try:
            from flask import session
            usuario = session.get('username', 'system')
        except Exception:
            usuario = 'system'

    # ----- Importa os modelos necessários -----
    from models_sqlalchemy import (
        Prontuario, ProntuarioRFO, Ocorrencia, Aluno
    )
    # Checar se já existe vínculo
    existing_link = db.query(ProntuarioRFO).filter_by(ocorrencia_id=ocorrencia_id).first()
    if existing_link:
        return False, 'RFO já integrado ao prontuário (vínculo existente)'

    ocorrencia = (
        db.query(Ocorrencia)
        .filter_by(id=ocorrencia_id)
        .first()
    )

    if not ocorrencia:
        return False, 'Ocorrência/RFO não encontrada'

    aluno = db.query(Aluno).filter_by(id=ocorrencia.aluno_id).first() if ocorrencia.aluno_id else None
    if not aluno:
        return False, 'Aluno relacionado ao RFO não encontrado'

    # ----- Monta os campos-formatados -----
    rfo_numero = getattr(ocorrencia, 'rfo_id', None) or getattr(ocorrencia, 'rfo', None) or getattr(ocorrencia, 'codigo', None) or f"RFO-{getattr(ocorrencia, 'id', '')}"
    data_oc = getattr(ocorrencia, 'data_ocorrencia', None) or getattr(ocorrencia, 'data', None) or getattr(ocorrencia, 'created_at', None) or ''
    relato = getattr(ocorrencia, 'relato_observador', None) or getattr(ocorrencia, 'relato', None) or getattr(ocorrencia, 'descricao', None) or ''
    tipo = getattr(ocorrencia, 'tipo_ocorrencia_nome', None) or getattr(ocorrencia, 'tipo', None) or ''
    item_desc = getattr(ocorrencia, 'item_descricao', None) or getattr(ocorrencia, 'descricao_item', None) or ''
    reinc = 'Sim' if getattr(ocorrencia, 'reincidencia', False) else 'Não'
    medida_aplicada = (
        getattr(ocorrencia, 'medida_aplicada', None)
        or getattr(ocorrencia, 'medida', None)
        or getattr(ocorrencia, 'tipo_rfo', None)
        or getattr(ocorrencia, 'tratamento_tipo', None)
    )
    if not medida_aplicada or medida_aplicada.strip() == "":
        medida_aplicada = "Elogio"
    despacho = getattr(ocorrencia, 'despacho_gestor', None) or getattr(ocorrencia, 'despacho', None) or ''
    data_despacho = getattr(ocorrencia, 'data_despacho', None) or getattr(ocorrencia, 'data_tratamento', None) or ''

    registro_line = (
        f"RFO: {rfo_numero} | Data do RFO: {data_oc} | Relato: {relato} | "
        f"Tipo: {tipo} | Item/Descrição: {item_desc} | É reincidência? {reinc} | "
        f"Medida Aplicada: {medida_aplicada} | Despacho do Gestor: {despacho} | "
        f"Data do Despacho: {data_despacho}"
    )

    aluno_id = aluno.id
    aluno_serie = getattr(aluno, "serie", None)
    aluno_turma = getattr(aluno, "turma", None)
    aluno_turno = getattr(aluno, "turno", None)
    aluno_telefone = getattr(aluno, "telefone", None)

    timestamp = datetime.utcnow().isoformat()

    prontuario = (
        db.query(Prontuario)
        .filter_by(aluno_id=aluno_id)
        .order_by(Prontuario.id.desc())
        .first()
    )
    try:
        if prontuario:
            atenuante = getattr(ocorrencia, 'circunstancias_atenuantes', '') or getattr(ocorrencia, 'atenuantes', '') or 'Não há'
            agravante = getattr(ocorrencia, 'circunstancias_agravantes', '') or getattr(ocorrencia, 'agravantes', '') or 'Não há'

            if not atenuante or atenuante.strip() == '':
                atenuante = 'Não há'
            if not agravante or agravante.strip() == '':
                agravante = 'Não há'

            prontuario.circunstancias_atenuantes = atenuante
            prontuario.circunstancias_agravantes = agravante
            # Salvar histórico se integrador disponível
            try:
                from blueprints.formularios_prontuario import insert_prontuario_history
                insert_prontuario_history(db, prontuario, action='update_before_append', changed_by=usuario)
            except Exception:
                pass

            existing_rf = getattr(prontuario, "registros_fatos", '') or ''
            if existing_rf and registro_line:
                combined = f"{existing_rf}\n\n--- Adicionado em {timestamp} ---\n{registro_line}"
            elif registro_line:
                combined = f"--- Adicionado em {timestamp} ---\n{registro_line}"
            else:
                combined = existing_rf
            
            prontuario.registros_fatos = combined
            prontuario.deleted = 0
            prontuario.serie = aluno_serie
            prontuario.turma = aluno_turma
            prontuario.turno = aluno_turno
            prontuario.telefone1 = aluno_telefone
            db.commit()
            prontuario_id = prontuario.id
        else:
            new_prontuario = Prontuario(
                aluno_id=aluno_id,
                responsavel='',
                email='',
                registros_fatos=f"--- Adicionado em {timestamp} ---\n{registro_line}",
                circunstancias_atenuantes=getattr(ocorrencia, 'circunstancias_atenuantes', '') or getattr(ocorrencia, 'atenuantes', '') or 'Não há',
                circunstancias_agravantes=getattr(ocorrencia, 'circunstancias_agravantes', '') or getattr(ocorrencia, 'agravantes', '') or 'Não há',
                created_at=timestamp,
                deleted=0,
                serie=aluno_serie,
                turma=aluno_turma,
                turno=aluno_turno,
                telefone1=aluno_telefone
            )
            db.add(new_prontuario)
            db.commit()
            prontuario_id = new_prontuario.id

        # Vincula o RFO ao prontuário
        new_link = ProntuarioRFO(
            ocorrencia_id=ocorrencia_id,
            prontuario_id=prontuario_id,
            created_at=timestamp
        )
        db.add(new_link)
        db.commit()

        return True, 'RFO integrado ao prontuário'
    except Exception as e:
        db.rollback()
        current_app.logger.exception('Erro em create_or_append_prontuario_por_rfo')
        return False, f'Erro ao integrar RFO ao prontuário: {e}'

