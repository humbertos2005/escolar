from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, 
    jsonify, g, current_app, Response, abort
)
from database import get_db  # USAR SEMPRE O NOVO
from models_sqlalchemy import (
    Ocorrencia, FichaMedidaDisciplinar, Aluno, TipoOcorrencia, Usuario, 
    PontuacaoBimestral, PontuacaoHistorico, Comportamento, FaltaDisciplinar,
    OcorrenciaFalta, OcorrenciaAluno, TabelaDisciplinarConfig, Bimestre,
    Cabecalho, DadosEscola, 
    # Inclua outras conforme necessário para as rotas!
)

from services.escolar_helper import get_tipos_ocorrencia, get_proximo_fmd_id, get_faltas_disciplinares
from services.escolar_helper import compute_pontuacao_corrente, _infer_comportamento_por_faixa
# ...
from .utils import (
    login_required,
    admin_required,
    admin_secundario_required,
    INFRACAO_MAP,
    TIPO_OCORRENCIA_MAP,
    TIPO_FALTA_MAP,
    MEDIDAS_MAP,
    get_proximo_rfo_id  # Adicione esta linha
)

from datetime import datetime, date
import re
import os
import pdfkit
import shutil
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from blueprints.prontuario_utils import create_or_append_prontuario_por_rfo

disciplinar_bp = Blueprint('disciplinar_bp', __name__, url_prefix='/disciplinar')

# Este bloco não é necessário em projetos 100% SQLAlchemy com migrations ORM/Alembic!
# Removido _ensure_disciplinar_schema.

def _create_fmd_for_aluno(db, aluno_id, medida_aplicada, descricao, data_fmd=None):
    from datetime import date
    if data_fmd is None:
        data_fmd = date.today().isoformat()
    try:
        # Verifica se a tabela existe usando SQLAlchemy
        if not db.bind.has_table("ficha_medida_disciplinar"):
            return False

        seq, ano = _next_fmd_sequence(db)
        fmd_id = f"FMD-{seq}/{ano}"

        fmd_kwargs = dict(
            fmd_id=fmd_id,
            aluno_id=aluno_id,
            data_fmd=data_fmd,
            medida_aplicada=medida_aplicada
        )
        if descricao is not None:
            fmd_kwargs['descricao_falta'] = descricao
        if 'status' in FichaMedidaDisciplinar.__table__.columns:
            fmd_kwargs['status'] = 'ATIVA'

        fmd = FichaMedidaDisciplinar(**fmd_kwargs)
        db.add(fmd)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

def _get_table_columns(db, model):
    """Retorna lista de nomes de colunas para a tabela (SQLAlchemy)"""
    return [col.name for col in model.__table__.columns]

def _find_first_column(db, model, candidates):
    cols = _get_table_columns(db, model)
    for c in candidates:
        if c in cols:
            return c
    return None

@disciplinar_bp.route('/api/check_reincidencia', methods=['GET'])
@login_required
def api_check_reincidencia():
    """
    Parâmetros:
      - aluno_id (int) REQUIRED
      - falta_id (int) OR descricao (string) REQUIRED (pelo menos um)
    Retorna JSON: { exists: bool, count: int, last: { id, tipo, created_at } or null }
    """
    db = get_db()
    aluno_id = request.args.get('aluno_id', type=int)
    falta_id = request.args.get('falta_id', type=int)
    descricao = request.args.get('descricao', type=str)
    
    if not aluno_id:
        return jsonify(error='Parâmetro aluno_id é obrigatório'), 400

    query = db.query(Ocorrencia).filter(Ocorrencia.aluno_id == aluno_id)
    if falta_id is not None:
        if hasattr(Ocorrencia, 'falta_disciplinar_id'):
            query = query.filter(Ocorrencia.falta_disciplinar_id == falta_id)
        elif hasattr(Ocorrencia, 'falta_id'):
            query = query.filter(Ocorrencia.falta_id == falta_id)
        elif hasattr(Ocorrencia, 'item_id'):
            query = query.filter(Ocorrencia.item_id == falta_id)
        else:
            return jsonify(error='falta_id fornecido, mas coluna correspondente não encontrada'), 400
    elif descricao:
        descricao_filters = []
        descricao_fields = [
            'descricao',
            'descricao_falta',
            'item_descricao',
            'falta_descricao',
            'descricao_ocorrencia',
            'relato_observador',
            'relato_faltas',
            'obs'
        ]
        found = False
        for field in descricao_fields:
            if hasattr(Ocorrencia, field):
                descricao_filters.append(getattr(Ocorrencia, field).ilike(f"%{descricao}%"))
                descricao_filters.append(getattr(Ocorrencia, field) == descricao)
                found = True
        if not found:
            return jsonify(error='Descrição fornecida, mas não foi encontrada coluna de descrição na tabela ocorrencias'), 400
        query = query.filter(or_(*descricao_filters))
    else:
        return jsonify(error='Parâmetro falta_id ou descricao é obrigatório'), 400

    print("aluno_id:", aluno_id, "falta_id:", falta_id, "descricao:", descricao)
    count = query.count()
    last = query.order_by(getattr(Ocorrencia, 'data_tratamento', None) or 
                          getattr(Ocorrencia, 'data_registro', None) or 
                          getattr(Ocorrencia, 'created_at', None) or 
                          Ocorrencia.id.desc()).first()
    
    if last:
        last_obj = {
            'id': last.id,
            'tipo': getattr(last, 'tipo_falta', None) or getattr(last, 'tipo', None) or getattr(last, 'tipo_ocorrencia', None) or getattr(last, 'falta_tipo', None) or getattr(last, 'classificacao', None),
            'created_at': getattr(last, 'data_tratamento', None) or getattr(last, 'data_registro', None) or getattr(last, 'created_at', None) or getattr(last, 'data', None)
        }
    else:
        last_obj = None

    return jsonify(exists=(count > 0), count=count, last=last_obj)

@disciplinar_bp.route('/reclassificar_ocorrencia', methods=['POST'])
@login_required
def reclassificar_ocorrencia():
    """
    Form data:
      - ocorrencia_id (int) REQUIRED
      - new_tipo (string) REQUIRED
    Atualiza a coluna tipo_falta (ou equivalente) da ocorrência indicada.
    """
    db = get_db()
    ocorrencia_id = request.form.get('ocorrencia_id', type=int) or request.form.get('ocorrencia_id')
    new_tipo = request.form.get('new_tipo', type=str) or request.form.get('new_tipo')

    try:
        ocorrencia_id = int(ocorrencia_id)
    except Exception:
        return jsonify(error='ocorrencia_id inválido'), 400

    if not new_tipo:
        return jsonify(error='new_tipo é obrigatório'), 400

    # Tenta encontrar o campo correto para o tipo
    tipo_fields = ['tipo_falta', 'tipo', 'falta_tipo', 'classificacao']
    ocorrencia = db.query(Ocorrencia).filter_by(id=ocorrencia_id).first()
    if not ocorrencia:
        return jsonify(error='Ocorrência não encontrada'), 404

    tipo_col = None
    for field in tipo_fields:
        if hasattr(ocorrencia, field):
            tipo_col = field
            break
    if not tipo_col:
        return jsonify(error='Coluna onde gravar tipo não encontrada'), 500

    try:
        setattr(ocorrencia, tipo_col, new_tipo)
        db.commit()
    except Exception:
        current_app.logger.exception('Erro ao reclassificar ocorrência')
        db.rollback()
        return jsonify(error='Erro ao atualizar ocorrência'), 500

    return jsonify(success=True)

# Helper: salva relações ocorrencia <-> faltas selecionadas
def salvar_faltas_relacionadas(db, ocorrencia_id, falta_ids_list):
    """
    Salva as relações ocorrencia <-> faltas usando SQLAlchemy.
    falta_ids_list: lista de ids (inteiros)
    Observação: não faz commit; o chamador deve commitar.
    """
    # Remove relações antigas
    db.query(OcorrenciaFalta).filter_by(ocorrencia_id=ocorrencia_id).delete()
    if not falta_ids_list:
        return
    for fid in falta_ids_list:
        try:
            rel = OcorrenciaFalta(ocorrencia_id=ocorrencia_id, falta_id=fid)
            db.add(rel)
        except Exception:
            pass

def _get_config_values(db):
    """Lê tabela_disciplinar_config e retorna dict de valores (ORM; fallback defaults se ausente)."""
    defaults = {
        'advertencia_oral': -0.1,
        'advertencia_escrita': -0.3,
        'suspensao_dia': -0.5,
        'acao_educativa_dia': -1.0,
        'elogio_individual': 0.5,
        'elogio_coletivo': 0.3
    }
    try:
        rows = db.query(TabelaDisciplinarConfig).all()
        for r in rows:
            defaults[getattr(r, 'chave')] = float(getattr(r, 'valor'))
    except Exception:
        pass
    return defaults

def _get_bimestre_for_date(db, data_str):
    """
    Determina (ano_int, bimestre_int) consultando a tabela 'bimestres' com SQLAlchemy.
    Se não encontrar ou erro, faz fallback para 4 bimestres por ano.
    """
    try:
        d = datetime.strptime(data_str[:10], '%Y-%m-%d').date()
    except Exception:
        d = date.today()
    ano = d.year
    try:
        rows = db.query(Bimestre).filter_by(ano=ano).order_by(Bimestre.numero).all()
        if rows:
            for r in rows:
                num = int(getattr(r, 'numero')) if getattr(r, 'numero') is not None else None
                inicio = getattr(r, 'inicio')
                fim = getattr(r, 'fim')
                try:
                    inicio_date = datetime.strptime(str(inicio)[:10], '%Y-%m-%d').date() if inicio else None
                except Exception:
                    inicio_date = None
                try:
                    fim_date = datetime.strptime(str(fim)[:10], '%Y-%m-%d').date() if fim else None
                except Exception:
                    fim_date = None
                if (inicio_date is None or inicio_date <= d) and (fim_date is None or fim_date >= d):
                    if num is not None:
                        return ano, num
    except Exception:
        try:
            current_app.logger.debug("Erro ao consultar tabela bimestres; usando fallback.")
        except Exception:
            pass
    b = ((d.month - 1) // 3) + 1
    return ano, b

from unidecode import unidecode
import re

def _calcular_delta_por_medida(medida_aplicada, qtd, config):
    """
    Calcula o delta (positivo/negativo) aplicável à pontuação a partir do texto da medida e quantidade.
    Aceita variações como advertencia oral, advertência oral, adv oral, advert oral, etc.
    Também faz print dos valores de depuração.
    """
    if not medida_aplicada:
        print("DEBUG - medida_aplicada vazia.")
        return 0.0

    # Remove acentos, coloca maiúsculo e remove espaços duplicados
    m = unidecode(str(medida_aplicada)).upper().replace("  ", " ").strip()
    try:
        qtd = float(qtd or 1)
    except Exception:
        qtd = 1.0

    # Print de depuração
    print("DEBUG - medida_aplicada recebida:", medida_aplicada)
    print("DEBUG - medida_aplicada formatada:", m)
    print("DEBUG - qtd usada:", qtd)

    # Formas mais comuns de cada medida
    if 'ADVERTENCIA ORAL' in m or 'ADV ORAL' in m or ('ORAL' in m and 'ADVERT' in m):
        delta = qtd * float(config.get('advertencia_oral', -0.1))
        print("DEBUG - delta calculado para ADVERTÊNCIA ORAL:", delta)
        return delta
    if 'ADVERTENCIA ESCRITA' in m or 'ADV ESCRITA' in m or ('ESCRITA' in m and 'ADVERT' in m):
        delta = qtd * float(config.get('advertencia_escrita', -0.3))
        print("DEBUG - delta calculado para ADVERTÊNCIA ESCRITA:", delta)
        return delta
    if 'SUSPENS' in m or 'SUSPENSAO' in m:
        nums = re.findall(r'(\d+)', m)
        dias = int(nums[0]) if nums else int(qtd)
        delta = dias * float(config.get('suspensao_dia', -0.5))
        print("DEBUG - delta calculado para SUSPENSÃO:", delta)
        return delta
    if 'ACAO EDUCATIVA' in m or 'ACAO EDUCATIVA' in m or 'EDUCATIVA' in m:
        nums = re.findall(r'(\d+)', m)
        dias = int(nums[0]) if nums else int(qtd)
        delta = dias * float(config.get('acao_educativa_dia', -1.0))
        print("DEBUG - delta calculado para AÇÃO EDUCATIVA:", delta)
        return delta
    if 'ELOGIO' in m and 'INDIVIDU' in m:
        delta = qtd * float(config.get('elogio_individual', 0.5))
        print("DEBUG - delta calculado para ELOGIO INDIVIDUAL:", delta)
        return delta
    if 'ELOGIO' in m and 'COLET' in m:
        delta = qtd * float(config.get('elogio_coletivo', 0.3))
        print("DEBUG - delta calculado para ELOGIO COLETIVO:", delta)
        return delta

    print("DEBUG - Nenhum caso identificado. Retornando delta 0.0")
    return 0.0

def _next_fmd_sequence(db):
    """
    Retorna (seq_int, ano_int) com o próximo número sequencial para o ano corrente.
    Mantém/atualiza Tabela FMDSequencia (model) (ano PRIMARY KEY, seq INTEGER).
    Se a tabela não existir, tenta computar a partir dos fmd_id existentes.
    """

    ano = str(datetime.now().year)  # Garante que o tipo bate (string)
    from models_sqlalchemy import FMDSequencia, FichaMedidaDisciplinar

    try:
        row = db.query(FMDSequencia).filter_by(ano=ano).first()
        if row and row.seq is not None:
            seq = int(row.seq) + 1
            row.seq = seq
            db.commit()
            return seq, int(ano)
        elif row is not None:
            # Caso raro: row existe mas não tem seq
            row.seq = 1
            db.commit()
            return 1, int(ano)
    except Exception as e:
        db.rollback()  # Garante rollback do erro!
        print("Erro ao buscar/incrementar FMDSequencia:", e)

    # Se não existe para o ano, pega maior seq dos FMDs existentes para o ano
    maxseq = 0
    try:
        fmds = db.query(FichaMedidaDisciplinar).filter(FichaMedidaDisciplinar.fmd_id.like(f"FMD-%/{ano}")).all()
        for f in fmds:
            fid = f.fmd_id or ''
            m = re.match(r'^FMD-(\d{1,})/' + str(ano) + r'$', fid)
            if m:
                n = int(m.group(1))
                if n > maxseq:
                    maxseq = n
    except Exception as e:
        print("Erro ao buscar maxseq de FMDs:", e)
        maxseq = 0

    seq = maxseq + 1

    # Insere novo registro APENAS SE não existe para este ano!
    try:
        existing = db.query(FMDSequencia).filter_by(ano=ano).first()
        if not existing:
            fmd_seq = FMDSequencia(ano=ano, seq=seq, numero=seq)
            db.add(fmd_seq)
            db.commit()
    except Exception as e:
        db.rollback()
        print("Erro ao inserir nova FMDSequencia:", e)
    return seq, int(ano)

def _apply_delta_pontuacao(db, aluno_id, data_tratamento_str, delta, ocorrencia_id=None, tipo_evento=None, data_despacho=None):
    """
    Aplica delta na pontuacao_bimestral do aluno (cria linha se inexistente).
    Garante limites mínimos/máximos (0.0 .. 10.0).
    Registra no pontuacao_historico usando DD/MM/AAAA (sem horas).
    """
    if not aluno_id:
        return

    from datetime import datetime
    ano, bimestre = _get_bimestre_for_date(db, data_tratamento_str)
    from models_sqlalchemy import PontuacaoBimestral, PontuacaoHistorico

    # Formata a data para DD/MM/AAAA
    criado_em = None
    if data_despacho:
        # Se vier YYYY-MM-DD, converte para DD/MM/AAAA
        if '-' in data_despacho and len(data_despacho) >= 10:
            criado_em = datetime.strptime(data_despacho[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        elif '/' in data_despacho and len(data_despacho) >= 10:
            criado_em = data_despacho[:10]
        else:
            criado_em = datetime.now().strftime('%d/%m/%Y')
    else:
        criado_em = datetime.now().strftime('%d/%m/%Y')

    try:
        row = db.query(PontuacaoBimestral).filter_by(aluno_id=aluno_id, ano=ano, bimestre=bimestre).first()
        if row:
            atual = float(row.pontuacao_atual)
            novo = max(0.0, min(10.0, atual + float(delta)))
            row.pontuacao_atual = novo
            row.atualizado_em = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            inicial = 8.0
            novo = max(0.0, min(10.0, inicial + float(delta)))
            row = PontuacaoBimestral(
                aluno_id=aluno_id,
                ano=ano,
                bimestre=bimestre,
                pontuacao_inicial=inicial,
                pontuacao_atual=novo,
                atualizado_em=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            db.add(row)

        hist = PontuacaoHistorico(
            aluno_id=aluno_id,
            ano=ano,
            bimestre=bimestre,
            ocorrencia_id=ocorrencia_id,
            tipo_evento=tipo_evento,
            valor_delta=float(delta),
            criado_em=criado_em
        )
        db.add(hist)
        db.commit()
    except Exception:
        current_app.logger.exception('Erro ao aplicar delta pontuacao (possível tabela ausente).')
        db.rollback()

@disciplinar_bp.route('/buscar_alunos_json')
@login_required
def buscar_alunos_json():
    """Rota AJAX para Autocomplete de alunos."""
    termo_busca = request.args.get('q', '').strip()
    db = get_db()
    resultados = []

    if not termo_busca:
        return jsonify([])

    matricula_part = None
    if ' - ' in termo_busca:
        matricula_part = termo_busca.split(' - ', 1)[0].strip()

    try:
        if termo_busca.isdigit() or (matricula_part and matricula_part.isdigit()):
            num = matricula_part if matricula_part and matricula_part.isdigit() else termo_busca
            alunos = db.query(Aluno).filter(
                (Aluno.id == int(num)) |
                (Aluno.matricula.ilike(f"%{num}%")) |
                (Aluno.nome.ilike(f"%{num}%"))
            ).order_by(Aluno.nome).limit(20).all()
        else:
            if len(termo_busca) < 3:
                return jsonify([])
            q_like = f'%{termo_busca}%'
            alunos = db.query(Aluno).filter(
                (Aluno.matricula.ilike(q_like)) |
                (Aluno.nome.ilike(q_like))
            ).order_by(Aluno.nome).limit(20).all()

        for aluno in alunos:
            resultados.append({
                'id': aluno.id,
                'value': f"{aluno.matricula} - {aluno.nome}",
                'matricula': aluno.matricula,
                'nome': aluno.nome,
                'data': {
                    'serie': getattr(aluno, "serie", ""),
                    'turma': getattr(aluno, "turma", "")
                }
            })
    except Exception:
        return jsonify([])

    return jsonify(resultados)

@disciplinar_bp.route('/registrar_rfo', methods=['GET', 'POST'])
@login_required
def registrar_rfo():
    db = get_db()
    from .utils import get_proximo_rfo_id
    rfo_id_gerado = get_proximo_rfo_id()
    tipos_ocorrencia = get_tipos_ocorrencia()

    if request.method == 'POST':
        

        aluno_ids = request.form.getlist('aluno_id')
        if not aluno_ids or all(not a for a in aluno_ids):
            raw = request.form.get('aluno_ids') or request.form.get('aluno_id') or ''
            aluno_ids = [s.strip() for s in raw.split(',') if s.strip()]

        tipo_ocorrencia_id_raw = request.form.get('tipo_ocorrencia_id')
        try:
            tipo_ocorrencia_id = int(tipo_ocorrencia_id_raw)
        except Exception:
            tipo_obj = db.query(TipoOcorrencia).filter_by(nome=tipo_ocorrencia_id_raw).first()
            tipo_ocorrencia_id = tipo_obj.id if tipo_obj else None

        data_ocorrencia = request.form.get('data_ocorrencia')
        observador_id = request.form.get('observador_id')
        error = None
        if not observador_id:
            error = 'Sessão do usuário expirada. Faça login novamente.'
        relato_observador = request.form.get('relato_observador', '').strip()
        tipo_rfo = request.form.get('tipo_rfo', '').strip()
        subtipo_elogio = request.form.get('subtipo_elogio', '').strip()
        material_recolhido = request.form.get('material_recolhido', '').strip()
        advertencia_oral = request.form.get('advertencia_oral', '').strip()

        if error is None:
            if not aluno_ids or len([a for a in aluno_ids if a]) == 0 or not tipo_ocorrencia_id or not data_ocorrencia or not observador_id or not relato_observador:
                error = 'Por favor, preencha todos os campos obrigatórios.'
            elif tipo_rfo != 'Elogio' and advertencia_oral not in ['sim', 'nao']:
                error = 'Selecione se a ocorrência deve ser considerada como Advertência Oral.'

        if error:
            aluno_ids_req = request.form.getlist('aluno_id')
            alunos_nome_map = {}
            if aluno_ids_req:
                alunos_objs = db.query(Aluno).filter(Aluno.id.in_(aluno_ids_req)).all()
                for aluno in alunos_objs:
                    alunos_nome_map[str(aluno.id)] = f"{aluno.matricula} - {aluno.nome}"

            flash(error, 'danger')
            return render_template(
                'disciplinar/registrar_rfo.html',
                rfo_id_gerado=rfo_id_gerado,
                tipos_ocorrencia=tipos_ocorrencia,
                request_form=request.form,
                g=g,
                alunos_nome_map=alunos_nome_map
            )

        if tipo_rfo == 'Elogio':
            advertencia_oral = 'nao'
        else:
            advertencia_oral = advertencia_oral or 'nao'

        try:
            rfo_id_final = get_proximo_rfo_id(incrementar=True)
            valid_aluno_ids = [a for a in aluno_ids if a]

            if not valid_aluno_ids:
                aluno_ids_req = request.form.getlist('aluno_id')
                alunos_nome_map = {}
                if aluno_ids_req:
                    alunos_objs = db.query(Aluno).filter(Aluno.id.in_(aluno_ids_req)).all()
                    for aluno in alunos_objs:
                        alunos_nome_map[str(aluno.id)] = f"{aluno.matricula} - {aluno.nome}"
                flash('Nenhum aluno válido selecionado.', 'danger')
                return render_template('disciplinar/registrar_rfo.html',
                                    rfo_id_gerado=rfo_id_gerado,
                                    tipos_ocorrencia=tipos_ocorrencia,
                                    request_form=request.form,
                                    g=g,
                                    alunos_nome_map=alunos_nome_map)

            primeiro_aluno = valid_aluno_ids[0] if valid_aluno_ids else None

            ocorrencia = Ocorrencia(
                rfo_id=rfo_id_final,
                aluno_id=primeiro_aluno,
                tipo_ocorrencia_id=tipo_ocorrencia_id,
                data_ocorrencia=data_ocorrencia,
                observador_id=observador_id,
                relato_observador=relato_observador,
                advertencia_oral=advertencia_oral,
                material_recolhido=material_recolhido,
                tratamento_tipo=tipo_rfo,
                tipo_rfo=tipo_rfo,                  # <--- LINHA NOVA, ESSENCIAL!
                subtipo_elogio=subtipo_elogio,
                responsavel_registro_id=session.get('user_id'),
                status='AGUARDANDO TRATAMENTO'
            )
            db.add(ocorrencia)
            db.commit()

            ocorrencia_id = ocorrencia.id

            for aid in valid_aluno_ids:
                try:
                    oa = OcorrenciaAluno(ocorrencia_id=ocorrencia_id, aluno_id=aid)
                    db.add(oa)
                except Exception:
                    try:
                        oa = OcorrenciaAluno(ocorrencia_id=ocorrencia_id, aluno_id=str(aid))
                        db.add(oa)
                    except Exception:
                        pass
            db.commit()

            flash(f'RFO {rfo_id_final} registrado com sucesso!', 'success')
            return redirect(url_for('disciplinar_bp.listar_rfo'))

        except Exception as e:
            db.rollback()
            current_app.logger.exception("Erro ao registrar RFO")
            aluno_ids_req = request.form.getlist('aluno_id')
            alunos_nome_map = {}
            if aluno_ids_req:
                alunos_objs = db.query(Aluno).filter(Aluno.id.in_(aluno_ids_req)).all()
                for aluno in alunos_objs:
                    alunos_nome_map[str(aluno.id)] = f"{aluno.matricula} - {aluno.nome}"
            flash(f'Erro ao registrar RFO: {e}', 'danger')
            return render_template(
                'disciplinar/registrar_rfo.html',
                rfo_id_gerado=rfo_id_gerado,
                tipos_ocorrencia=tipos_ocorrencia,
                request_form=request.form,
                g=g,
                alunos_nome_map=alunos_nome_map
            )

    return render_template('disciplinar/registrar_rfo.html',
                       rfo_id_gerado=rfo_id_gerado,
                       tipos_ocorrencia=tipos_ocorrencia,
                       g=g,
                       alunos_nome_map={})

@disciplinar_bp.route('/listar_rfo')
@admin_secundario_required
def listar_rfo():
    db = get_db()
    from sqlalchemy.orm import joinedload, aliased
    from sqlalchemy import func, cast, String

    Aluno1 = aliased(Aluno)
    Aluno2 = aliased(Aluno)

    # Consulta principal com JOINs para obter informações relevantes e agrupamentos
    ocorrencias = (
        db.query(
            Ocorrencia.id,
            Ocorrencia.rfo_id,
            Ocorrencia.data_ocorrencia,
            Ocorrencia.tipo_ocorrencia_id,
            Ocorrencia.status,
            Ocorrencia.relato_observador,
            Ocorrencia.advertencia_oral,
            Ocorrencia.material_recolhido,
            func.string_agg(Aluno2.nome, '; ').label('alunos'),
            func.coalesce(Aluno1.matricula, Aluno2.matricula).label('matricula'),
            func.coalesce(Aluno1.nome, Aluno2.nome).label('nome_aluno'),
            func.coalesce(
                func.string_agg(
                    cast(Aluno2.serie, String) + " - " + cast(Aluno2.turma, String),
                    '; '
                ),
                cast(Aluno1.serie, String) + " - " + cast(Aluno1.turma, String)
            ).label('series_turmas'),
            Usuario.username.label('responsavel_registro_username'),
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
        )
        .join(OcorrenciaAluno, OcorrenciaAluno.ocorrencia_id == Ocorrencia.id, isouter=True)
        .join(Aluno2, Aluno2.id == OcorrenciaAluno.aluno_id, isouter=True)
        .join(Aluno1, Aluno1.id == Ocorrencia.aluno_id, isouter=True)
        .join(Usuario, Usuario.id == Ocorrencia.responsavel_registro_id, isouter=True)
        .join(TipoOcorrencia, TipoOcorrencia.id == Ocorrencia.tipo_ocorrencia_id, isouter=True)
        .filter(Ocorrencia.status == 'AGUARDANDO TRATAMENTO')
        .group_by(
            Ocorrencia.id,
            Ocorrencia.rfo_id,
            Ocorrencia.data_ocorrencia,
            Ocorrencia.tipo_ocorrencia_id,
            Ocorrencia.status,
            Ocorrencia.relato_observador,
            Ocorrencia.advertencia_oral,
            Ocorrencia.material_recolhido,
            Aluno1.matricula,
            Aluno2.matricula,
            Aluno1.nome,
            Aluno2.nome,
            Aluno1.serie,
            Aluno1.turma,
            Usuario.username,
            TipoOcorrencia.nome
        )
        .order_by(Ocorrencia.data_registro.desc())
        .all()
    )

    rfos_list = [dict(rfo._asdict()) for rfo in ocorrencias]
    return render_template('disciplinar/listar_rfo.html', rfos=rfos_list)


@disciplinar_bp.route('/visualizar_rfo/<int:ocorrencia_id>')
@admin_secundario_required
def visualizar_rfo(ocorrencia_id):
    db = get_db()
    from sqlalchemy import func, cast, String

    rfo = (
        db.query(
            Ocorrencia,
            func.string_agg(Aluno.nome.cast(String), '; ').label('alunos'),
            func.string_agg(
                (Aluno.serie.cast(String) + " - " + Aluno.turma.cast(String)),
                '; '
            ).label('series_turmas'),
            Aluno.matricula.label('matricula'),
            Aluno.nome.label('nome_aluno'),
            Aluno.serie.label('serie'),
            Aluno.turma.label('turma'),
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
            Usuario.username.label('responsavel_registro_username'),
            Ocorrencia.tipo_rfo.label('tipo_rfo'),
            Ocorrencia.subtipo_elogio.label('subtipo_elogio'),
        )
        .select_from(Ocorrencia)
        .outerjoin(OcorrenciaAluno, OcorrenciaAluno.ocorrencia_id == Ocorrencia.id)
        .outerjoin(Aluno, Aluno.id == OcorrenciaAluno.aluno_id)
        .outerjoin(TipoOcorrencia, TipoOcorrencia.id == Ocorrencia.tipo_ocorrencia_id)
        .outerjoin(Usuario, Usuario.id == Ocorrencia.responsavel_registro_id)
        .filter(Ocorrencia.id == ocorrencia_id)
        .group_by(Ocorrencia.id, Aluno.matricula, Aluno.nome, Aluno.serie, Aluno.turma, TipoOcorrencia.nome, Usuario.username)
        .first()
    )

    if not rfo:
        flash('RFO não encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    # rfo é uma namedtuple (ou Row); transformar em dict mutável para manipulação
    rfo_dict = dict(rfo._asdict() if hasattr(rfo, "_asdict") else rfo)

    # Obter lista de alunos da ocorrência, incluindo o ID
    alunos_rows = (
        db.query(
            Aluno.id,
            Aluno.matricula,
            Aluno.nome,
            Aluno.serie,
            Aluno.turma
        )
        .join(OcorrenciaAluno, OcorrenciaAluno.aluno_id == Aluno.id)
        .filter(OcorrenciaAluno.ocorrencia_id == ocorrencia_id)
        .order_by(OcorrenciaAluno.id)
        .all()
    )
    alunos_list = []
    series_list = []
    names_list = []
    for ar in alunos_rows:
        # ar = (id, matricula, nome, serie, turma)
        aluno_id = ar[0]
        matricula = ar[1]
        nome = ar[2]
        serie = ar[3]
        turma = ar[4]
        alunos_list.append({
            'id': aluno_id,
            'nome': nome or '',
            'matricula': matricula or '',
            'serie': serie or '',
            'turma': turma or ''
        })
        # Para os nomes/séries/turmas
        s = (serie or '')
        t = (turma or '')
        if s or t:
            series_list.append(f"{s} - {t}".strip(' - '))
        names_list.append(nome or '')

    rfo_dict['alunos_list'] = alunos_list

    if series_list:
        rfo_dict['series_turmas'] = '; '.join(series_list)
    else:
        rfo_dict['series_turmas'] = rfo_dict.get('series_turmas') or ((rfo_dict.get('serie') and rfo_dict.get('turma')) and f"{rfo_dict.get('serie')} - {rfo_dict.get('turma')}" or '')

    if any(names_list):
        rfo_dict['alunos'] = '; '.join([n for n in names_list if n])
    else:
        rfo_dict['alunos'] = rfo_dict.get('alunos') or rfo_dict.get('nome_aluno') or ''

    tratamento = rfo_dict.get('tratamento_tipo') or rfo_dict.get('tipo_ocorrencia_text') or rfo_dict.get('tipo_ocorrencia_nome') or ''
    associado = (rfo_dict.get('advertencia_oral') or rfo_dict.get('subtipo_elogio') or '')
    if isinstance(associado, bool):
        associado = 'Sim' if associado else 'Não'
    material_info = rfo_dict.get('material_recolhido') or ''
    if (not material_info) and tratamento:
        material_info = tratamento
        if associado:
            material_info = f"{tratamento} — {associado}"
    rfo_dict['material_recolhido_info'] = material_info

    from datetime import datetime
    from models_sqlalchemy import PontuacaoHistorico
    from sqlalchemy import func

    data_do_documento = rfo.Ocorrencia.data_registro
    if isinstance(data_do_documento, str):
        data_do_documento = datetime.strptime(data_do_documento[:10], '%Y-%m-%d')

    aluno_id = rfo.Ocorrencia.aluno_id

    pontuacao_historica = (
        db.query(func.sum(PontuacaoHistorico.valor_delta))
        .filter(PontuacaoHistorico.aluno_id == aluno_id)
        .filter(PontuacaoHistorico.criado_em <= data_do_documento.strftime('%d/%m/%Y'))
        .scalar()
    )

    if pontuacao_historica is None:
        pontuacao_historica = 8.0

    return render_template(
        'disciplinar/visualizar_rfo.html', 
        rfo=rfo, 
        pontuacao_historica=pontuacao_historica
    )

@disciplinar_bp.route('/imprimir_rfo/<int:ocorrencia_id>')
@admin_secundario_required
def imprimir_rfo(ocorrencia_id):
    db = get_db()

    rfo = (
        db.query(
            Ocorrencia,
            Aluno.matricula,
            Aluno.nome.label('nome_aluno'),
            Aluno.serie,
            Aluno.turma,
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
            Usuario.username.label('responsavel_registro_username')
        )
        .join(Aluno, Ocorrencia.aluno_id == Aluno.id)
        .join(TipoOcorrencia, Ocorrencia.tipo_ocorrencia_id == TipoOcorrencia.id)
        .outerjoin(Usuario, Ocorrencia.responsavel_registro_id == Usuario.id)
        .filter(Ocorrencia.id == ocorrencia_id)
        .first()
    )

    if not rfo:
        flash('RFO não encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    return render_template('formularios/rfo_impressao.html', rfo=dict(rfo._asdict() if hasattr(rfo, "_asdict") else rfo))

@disciplinar_bp.route('/export_prontuario/<int:ocorrencia_id>')
@admin_secundario_required
def export_prontuario_pdf(ocorrencia_id):
    db = get_db()
    from sqlalchemy import func, cast, String

    rfo = (
        db.query(
            Ocorrencia,
            func.string_agg(cast(Aluno.nome, String), '; ').label('alunos'),
            func.string_agg(cast(Aluno.serie, String) + " - " + cast(Aluno.turma, String), '; ').label('series_turmas'),
            Aluno.matricula.label('matricula'),
            Aluno.nome.label('nome_aluno'),
            Aluno.serie.label('serie'),
            Aluno.turma.label('turma'),
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
            Usuario.username.label('responsavel_registro_username'),
        )
        .select_from(Ocorrencia)
        .outerjoin(OcorrenciaAluno, OcorrenciaAluno.ocorrencia_id == Ocorrencia.id)
        .outerjoin(Aluno, Aluno.id == OcorrenciaAluno.aluno_id)
        .outerjoin(TipoOcorrencia, TipoOcorrencia.id == Ocorrencia.tipo_ocorrencia_id)
        .outerjoin(Usuario, Usuario.id == Ocorrencia.responsavel_registro_id)
        .filter(Ocorrencia.id == ocorrencia_id)
        .group_by(Ocorrencia.id, Aluno.matricula, Aluno.nome, Aluno.serie, Aluno.turma, TipoOcorrencia.nome, Usuario.username)
        .first()
    )

    if not rfo:
        flash('RFO não encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    rfo_dict = dict(rfo._asdict() if hasattr(rfo, "_asdict") else rfo)

    html = render_template('disciplinar/prontuario_pdf.html', rfo=rfo_dict)

    wk_path = shutil.which('wkhtmltopdf')
    if not wk_path:
        wk_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

    if not os.path.isfile(wk_path):
        abort(500, description=f"wkhtmltopdf não encontrado em: {wk_path}")

    config = pdfkit.configuration(wkhtmltopdf=wk_path)
    options = {
        'page-size': 'A4',
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
        'print-media-type': None,
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm',
    }

    pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)
    if not pdf_bytes:
        abort(500, description="Falha ao gerar o PDF.")

    nome_aluno = rfo_dict.get('nome_aluno') or 'aluno'
    safe_name = secure_filename(f"prontuario_{nome_aluno}.pdf")

    headers = {
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'attachment; filename="{safe_name}"'
    }
    return Response(pdf_bytes, headers=headers)

@disciplinar_bp.route('/gerar_ficha_medida/<int:ocorrencia_id>')
@admin_secundario_required
def gerar_ficha_medida(ocorrencia_id):
    flash('Funcionalidade de Ficha de Medida Disciplinar em desenvolvimento.', 'info')
    return redirect(url_for('disciplinar_bp.listar_rfo'))

@disciplinar_bp.route('/ocorrencias')
@login_required
def listar_ocorrencias():
    db = get_db()

    ocorrencias = (
        db.query(
            Ocorrencia.id,
            Ocorrencia.rfo_id,
            Ocorrencia.data_ocorrencia,
            Ocorrencia.status,
            Ocorrencia.data_tratamento,
            Ocorrencia.tipo_falta,
            Ocorrencia.medida_aplicada,
            Ocorrencia.relato_observador,
            Ocorrencia.aluno_id,
            Aluno.matricula,
            Aluno.nome.label('nome_aluno'),
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
            Ocorrencia.relato_estudante,
            Ocorrencia.despacho_gestor,
            Ocorrencia.data_despacho,
            Ocorrencia.reincidencia
        )
        .join(Aluno, Ocorrencia.aluno_id == Aluno.id)
        .join(TipoOcorrencia, Ocorrencia.tipo_ocorrencia_id == TipoOcorrencia.id)
        .filter(Ocorrencia.status == 'TRATADO')
        .order_by(Ocorrencia.data_tratamento.desc())
        .all()
    )

    ocorrencias_list = [dict(o._asdict() if hasattr(o, "_asdict") else o) for o in ocorrencias]
    return render_template('listar_ocorrencias.html', ocorrencias=ocorrencias_list)

@disciplinar_bp.route('/tratar_rfo/<int:ocorrencia_id>', methods=['GET', 'POST'])
@admin_secundario_required
def tratar_rfo(ocorrencia_id):
    db = get_db()

    ocorrencia = (
        db.query(
            Ocorrencia,
            Aluno.matricula,
            Aluno.nome.label('nome_aluno'),
            Aluno.serie,
            Aluno.turma,
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
            Usuario.username.label('responsavel_registro_username')
        )
        .join(Aluno, Ocorrencia.aluno_id == Aluno.id)
        .join(TipoOcorrencia, Ocorrencia.tipo_ocorrencia_id == TipoOcorrencia.id)
        .outerjoin(Usuario, Ocorrencia.responsavel_registro_id == Usuario.id)
        .filter(Ocorrencia.id == ocorrencia_id)
        .filter(Ocorrencia.status == 'AGUARDANDO TRATAMENTO')
        .first()
    )

    if not ocorrencia:
        flash('RFO não encontrado ou já tratado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    ocorrencia_dict = dict(ocorrencia._asdict() if hasattr(ocorrencia, "_asdict") else ocorrencia)

    alunos_rows = (
        db.query(
            Aluno.id, Aluno.matricula, Aluno.nome, Aluno.serie, Aluno.turma
        )
        .join(OcorrenciaAluno, OcorrenciaAluno.aluno_id == Aluno.id)
        .filter(OcorrenciaAluno.ocorrencia_id == ocorrencia_id)
        .order_by(OcorrenciaAluno.id)
        .all()
    )

    alunos_list = []
    series_list = []
    nomes_list = []
    for ar in alunos_rows:
        # Adicionando o ID!
        aluno_id = getattr(ar, 'id', None)
        if aluno_id is None:
            aluno_id = getattr(ar, 'aluno_id', None)
        if aluno_id is None:
            aluno_id = ''
        nome = getattr(ar, 'nome', None)
        matricula = getattr(ar, 'matricula', None)
        serie = getattr(ar, 'serie', None)
        turma = getattr(ar, 'turma', None)
        alunos_list.append({
            'id': aluno_id,               # <-- ESSENCIAL!
            'nome': nome or '',
            'matricula': matricula or '',
            'serie': serie or '',
            'turma': turma or ''
        })
        s = (serie or '')
        t = (turma or '')
        if s or t:
            series_list.append(f"{s} - {t}".strip(' - '))
        nomes_list.append(nome or '')

    ocorrencia_dict['alunos_list'] = alunos_list
    ocorrencia_dict['alunos'] = '; '.join([n for n in nomes_list if n]) if any(nomes_list) else ocorrencia_dict.get('alunos') or ocorrencia_dict.get('nome_aluno') or ''
    if series_list:
        ocorrencia_dict['series_turmas'] = '; '.join(series_list)
    else:
        ocorrencia_dict['series_turmas'] = ocorrencia_dict.get('series_turmas') or ((ocorrencia_dict.get('serie') and ocorrencia_dict.get('turma')) and f"{ocorrencia_dict.get('serie')} - {ocorrencia_dict.get('turma')}" or '')

    tipos_falta = TIPO_FALTA_MAP
    medidas_map = MEDIDAS_MAP

    if request.method == 'POST':
        oc_obj = db.query(Ocorrencia).filter_by(id=ocorrencia_id).first()
        tipos_raw = request.form.get('tipo_falta_list', '').strip()
        if tipos_raw:
            tipos_list = [t.strip() for t in tipos_raw.split(',') if t.strip()]
        else:
            tipos_list = request.form.getlist('tipo_falta[]') or request.form.getlist('tipo_falta') or []
            tipos_list = [t.strip() for t in tipos_list if t.strip()]
        tipos_csv = ','.join(tipos_list)

        falta_ids_csv = request.form.get('falta_disciplinar_ids', '').strip()
        falta_ids_list = [fid.strip() for fid in falta_ids_csv.split(',') if fid.strip()]

        medida_aplicada = request.form.get('medida_aplicada', '').strip()
        if medida_aplicada == 'Nenhuma':
            medida_aplicada = None
        reincidencia = request.form.get('reincidencia')
        try:
            reincidencia = int(reincidencia) if reincidencia is not None and reincidencia != '' else None
        except Exception:
            reincidencia = None

        relato_estudante = request.form.get('relato_estudante', '').strip()
        despacho_gestor = request.form.get('despacho_gestor', '').strip()
        data_despacho = request.form.get('data_despacho', '').strip()
        comparecimento_responsavel = request.form.get('comparecimento_responsavel', '0')

        circ_at = request.form.get('circunstancias_atenuantes', '').strip() or 'Não há'
        circ_ag = request.form.get('circunstancias_agravantes', '').strip() or 'Não há'

        tratamento_classificacao = request.form.get('tratamento_classificacao', '').strip() or ''
        tipo_rfo_post = request.form.get('tipo_rfo', '').strip() or ''
        oc_tipo = ocorrencia_dict.get('tipo_rfo') or ocorrencia_dict.get('tipo_ocorrencia_nome') or ''

        is_elogio_form = request.form.get('is_elogio')
        is_elogio_from_form = str(is_elogio_form).strip().lower() in ('1', 'true', 'on')

        is_elogio = False
        for v in (tratamento_classificacao, medida_aplicada or '', tipo_rfo_post, oc_tipo):
            try:
                if v and 'elogio' in v.lower():
                    is_elogio = True
                    break
            except Exception:
                pass

        if not is_elogio and is_elogio_from_form:
            is_elogio = True

        if is_elogio:
            tipos_csv = ''
            falta_ids_list = []
            falta_ids_csv = ''
            if not medida_aplicada:
                medida_aplicada = (tratamento_classificacao or tipo_rfo_post or oc_tipo or '').strip()
        error = None
        if not is_elogio:
            if not tipos_csv:
                error = 'Tipo de falta é obrigatório.'
            elif not falta_ids_list:
                error = 'A descrição da falta é obrigat??ria.'
            elif not medida_aplicada and not (tratamento_classificacao == 'Admoestação'):
                error = 'A medida aplicada é obrigatória.'

        if error is None:
            if not is_elogio:   # <- só exige reincidência se NÃO for elogio
                if reincidencia not in [0, 1]:
                    error = 'Reincidência deve ser "Sim" ou "Não".'
            if not despacho_gestor:
                error = 'O despacho do gestor é obrigatório.'
            elif not data_despacho:
                error = 'A data do despacho é obrigatória.'

        if error is not None:
            flash(error, 'danger')
        else:
            try:
                primeiro_falta_id = None
                try:
                    if falta_ids_list:
                        primeiro_falta_id = int(falta_ids_list[0])
                except Exception:
                    primeiro_falta_id = None

                data_trat = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Atualiza a ocorrência
                oc_obj = db.query(Ocorrencia).filter_by(id=ocorrencia_id).one_or_none()
                oc_obj.status = 'TRATADO'
                oc_obj.data_tratamento = data_trat
                oc_obj.tipo_falta = tipos_csv
                oc_obj.falta_disciplinar_id = primeiro_falta_id
                oc_obj.medida_aplicada = medida_aplicada
                oc_obj.reincidencia = reincidencia
                oc_obj.relato_estudante = relato_estudante
                oc_obj.despacho_gestor = despacho_gestor
                oc_obj.data_despacho = data_despacho
                oc_obj.comparecimento_responsavel = comparecimento_responsavel
                if hasattr(oc_obj, 'circunstancias_atenuantes'):
                    oc_obj.circunstancias_atenuantes = circ_at
                if hasattr(oc_obj, 'circunstancias_agravantes'):
                    oc_obj.circunstancias_agravantes = circ_ag

                falta_ids_ints = []
                for fid in falta_ids_list:
                    try:
                        falta_ids_ints.append(int(fid))
                    except Exception:
                        pass

                salvar_faltas_relacionadas(db, ocorrencia_id, falta_ids_ints)

                # --- INTEGRAÇÃO: calcular delta e aplicar pontuação ---
                try:
                    if medida_aplicada:
                        try:
                            config = _get_config_values(db)
                            qtd_form = request.form.get('sim_qtd') or request.form.get('dias') or request.form.get('quantidade') or 1
                            delta = _calcular_delta_por_medida(medida_aplicada, qtd_form, config)
                            _apply_delta_pontuacao(db, oc_obj.aluno_id, data_trat, delta, ocorrencia_id, medida_aplicada, data_despacho)
                        except Exception:
                            current_app.logger.exception("Erro ao aplicar delta de pontuação")
                    else:
                        current_app.logger.warning(
                            "Tratamento salvo sem aplicar pontuação: ocorrencia_id=%s, medida_aplicada ausente (possível elogio sem medida)",
                            ocorrencia_id
                        )

                    try:
                        rfo_id = getattr(oc_obj, 'rfo_id', None)
                        aluno_id_local = getattr(oc_obj, 'aluno_id', None)
                        responsavel_id = getattr(oc_obj, 'responsavel_registro_id', None) or getattr(oc_obj, 'observador_id', None)
                        responsavel_id = int(responsavel_id) if responsavel_id is not None else 0
                        tipo_falta_val = tipos_csv
                        falta_ids_val = falta_ids_csv
                        tipo_falta_list_val = tipos_csv

                        from models_sqlalchemy import FichaMedidaDisciplinar
                        if rfo_id:
                            existing = db.query(FichaMedidaDisciplinar).filter_by(rfo_id=rfo_id).first()
                            if existing:
                                existing.pontos_aplicados = float(delta) if 'delta' in locals() else 0.0
                            else:
                                seq, seq_ano = _next_fmd_sequence(db)
                                fmd_id = f"FMD-{seq:04d}/{seq_ano}"
                                data_fmd = datetime.now().strftime('%Y-%m-%d')

                                # ADICIONE OS PRINTS AQUI:
                                print("DEBUG - CAMPOS POSTADOS:", dict(request.form))  # Vai mostrar tudo do formulário enviado
                                print("DEBUG - medida_aplicada recebida no POST:", request.form.get("medida_aplicada"))
                                print("DEBUG - medida_aplicada utilizada na FMD:", medida_aplicada)

                                fmd_obj = FichaMedidaDisciplinar(
                                    fmd_id=fmd_id,
                                    aluno_id=aluno_id_local,
                                    rfo_id=rfo_id,
                                    data_fmd=data_fmd,
                                    tipo_falta=tipo_falta_val,
                                    medida_aplicada=medida_aplicada,
                                    descricao_falta='',
                                    observacoes='',
                                    responsavel_id=responsavel_id,
                                    data_registro=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    falta_disciplinar_ids=falta_ids_val,
                                    tipo_falta_list=tipo_falta_list_val,
                                    pontos_aplicados=float(delta) if 'delta' in locals() else 0.0
                                )
                                db.add(fmd_obj)
                        if ocorrencia_id:
                            oc_obj.pontos_aplicados = float(delta) if 'delta' in locals() else 0.0
                    except Exception:
                        current_app.logger.exception('Erro ao gravar pontos_aplicados em ficha_medida_disciplinar/ocorrencias')

                except Exception:
                    current_app.logger.exception('Erro ao aplicar atualização de pontuacao')

                try:
                    from flask import session as flask_session
                    ok, msg = create_or_append_prontuario_por_rfo(db, ocorrencia_id, flask_session.get('username'))
                    if not ok:
                        current_app.logger.debug('create_or_append_prontuario_por_rfo: ' + str(msg))
                except Exception:
                    current_app.logger.exception('Erro ao integrar RFO ao prontuário (tarefa auxiliar)')

                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    flash(f'Erro ao tratar RFO: {e}', 'danger')
                    return redirect(url_for('disciplinar_bp.listar_rfo'))

                rfo_id_str = ocorrencia_dict.get("rfo_id") or getattr(oc_obj, "rfo_id", None) or getattr(oc_obj, "id", None)
                flash(f'RFO {rfo_id_str} tratado com sucesso.', 'success')
                return redirect(url_for('disciplinar_bp.listar_rfo'))
            except Exception as e:
                db.rollback()
                current_app.logger.exception('Erro no tratamento do RFO')
                flash(f'Erro ao tratar RFO: {e}', 'danger')

    tipo = ocorrencia_dict.get('trata_se') or ocorrencia_dict.get('tipo_rfo') or ocorrencia_dict.get('tipo') or ocorrencia_dict.get('trata_tipo') or ''
    associado = (ocorrencia_dict.get('advertencia_oral')
                 or ocorrencia_dict.get('tipo_elogio')
                 or ocorrencia_dict.get('subtipo')
                 or ocorrencia_dict.get('considerar_advertencia_oral')
                 or '')
    if isinstance(associado, bool):
        associado = 'Sim' if associado else 'Não'
    material_info = tipo
    if associado:
        material_info = f"{tipo} — {associado}"
    ocorrencia_dict['material_recolhido_info'] = material_info

    # Acrescente isto antes do render_template:
    if 'Ocorrencia' in ocorrencia_dict and ocorrencia_dict['Ocorrencia']:
        oc = ocorrencia_dict['Ocorrencia']
        # Extrai os campos desejados do objeto SQLAlchemy para o dict principal:
        for field in ['rfo_id', 'status', 'data_ocorrencia', 'relato_observador']:
            ocorrencia_dict[field] = getattr(oc, field, None)

    from flask import g, session
    g.nivel = session.get('nivel')
    # Sincronize campos vitais do objeto Ocorrencia principal para o dict
    if 'Ocorrencia' in ocorrencia_dict and ocorrencia_dict['Ocorrencia']:
        oc = ocorrencia_dict['Ocorrencia']
        fields_to_copy = [
            'rfo_id', 'status', 'data_ocorrencia', 'relato_observador', 
            'tipo_rfo', 'subtipo_elogio', 'advertencia_oral'
        ]
        for field in fields_to_copy:
            ocorrencia_dict[field] = getattr(oc, field, None)
    return render_template('disciplinar/tratar_rfo.html',
                           ocorrencia=ocorrencia_dict,
                           tipos_falta=tipos_falta,
                           medidas_map=medidas_map,
                           request_form=request.form if request.method == 'POST' else None)

@disciplinar_bp.route('/editar_ocorrencia/<int:ocorrencia_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_ocorrencia(ocorrencia_id):
    db = get_db()
    ocorrencia = (
        db.query(
            Ocorrencia,
            Aluno.matricula,
            Aluno.nome.label('nome_aluno'),
            TipoOcorrencia.nome.label('tipo_ocorrencia_nome'),
        )
        .join(Aluno, Ocorrencia.aluno_id == Aluno.id)
        .join(TipoOcorrencia, Ocorrencia.tipo_ocorrencia_id == TipoOcorrencia.id)
        .filter(Ocorrencia.id == ocorrencia_id)
        .filter(Ocorrencia.status == 'TRATADO')
        .first()
    )

    if not ocorrencia:
        flash('Ocorrência não encontrada ou ainda não foi tratada.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_ocorrencias'))

    ocorrencia_dict = dict(ocorrencia._asdict() if hasattr(ocorrencia, "_asdict") else ocorrencia)

    if request.method == 'POST':
        tipo_falta = request.form.get('tipo_falta', '').strip()
        medida_aplicada = request.form.get('medida_aplicada', '').strip()
        relato_observador = request.form.get('relato_observador', '').strip()
        advertencia_oral = request.form.get('advertencia_oral', '').strip()
        error = None

        if not tipo_falta:
            error = 'Tipo de falta é obrigatório.'
        elif not medida_aplicada:
            error = 'A medida aplicada é obrigatória.'
        elif not advertencia_oral or advertencia_oral not in ['sim', 'nao']:
            error = 'Selecione se a ocorrência deve ser considerada como Advertência Oral.'

        if error is not None:
            flash(error, 'danger')
        else:
            try:
                oc_obj = db.query(Ocorrencia).filter_by(id=ocorrencia_id).first()
                oc_obj.tipo_falta = tipo_falta
                oc_obj.medida_aplicada = medida_aplicada
                oc_obj.relato_observador = relato_observador
                oc_obj.advertencia_oral = advertencia_oral
                db.commit()
                flash(f'Ocorrência {ocorrencia_dict["rfo_id"]} editada com sucesso.', 'success')
                return redirect(url_for('disciplinar_bp.listar_ocorrencias'))
            except Exception as e:
                db.rollback()
                flash(f'Erro ao editar ocorrência: {e}', 'danger')

    tipos_ocorrencia_db = get_tipos_ocorrencia()
    return render_template(
        'disciplinar/adicionar_ocorrencia.html',
        ocorrencia=ocorrencia_dict,
        tipos_ocorrencia=tipos_ocorrencia_db,
        tipos_falta=TIPO_FALTA_MAP,
        medidas_map=MEDIDAS_MAP,
        request_form=request.form
    )

@disciplinar_bp.route('/excluir_ocorrencia/<int:ocorrencia_id>', methods=['POST'])
@admin_required
def excluir_ocorrencia(ocorrencia_id):
    db = get_db()

    try:
        ocorrencia = db.query(Ocorrencia).filter_by(id=ocorrencia_id).first()

        if not ocorrencia:
            flash('Ocorrência/RFO não encontrado.', 'danger')
            return redirect(url_for('disciplinar_bp.listar_ocorrencias'))

        rfo_id_nome = getattr(ocorrencia, 'rfo_id', '')

        db.delete(ocorrencia)
        db.commit()

        flash(f'Oorrência/RFO {rfo_id_nome} excluído com sucesso.', 'success')

    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir ocorrência/RFO: {e}', 'danger')

    return redirect(url_for('disciplinar_bp.listar_ocorrencias'))

@disciplinar_bp.route('/registrar_fmd', methods=['GET', 'POST'])
@admin_secundario_required
def registrar_fmd():
    db = get_db()
    fmd_id_gerado = get_proximo_fmd_id()
    faltas = get_faltas_disciplinares()

    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id')
        data_fmd = request.form.get('data_fmd')
        tipos_raw = request.form.get('tipo_falta_list', '').strip()
        if tipos_raw:
            tipos_list = [t.strip() for t in tipos_raw.split(',') if t.strip()]
        else:
            tipos_list = request.form.getlist('tipo_falta[]') or []
            tipos_list = [t.strip() for t in tipos_list if t.strip()]
        tipo_falta_csv = ','.join(tipos_list)

        medida_aplicada = request.form.get('medida_aplicada', '').strip()
        descricao_falta = request.form.get('descricao_falta', '').strip() if request.form.get('descricao_falta') else ''
        relato_faltas = request.form.get('relato_faltas', '').strip()

        falta_ids_csv = request.form.get('falta_disciplinar_ids', '').strip()
        falta_ids_list = [fid.strip() for fid in falta_ids_csv.split(',') if fid.strip()]

        comportamento_id = request.form.get('comportamento_id') or None
        pontuacao_id = request.form.get('pontuacao_id') or None

        comparecimento = request.form.get('comparecimento')
        try:
            comparecimento_val = 1 if str(comparecimento) in ['1', 'true', 'True', 'on', 'sim', '1'] else 0
        except Exception:
            comparecimento_val = 0

        prazo_comparecimento = request.form.get('prazo_comparecimento', '').strip()
        atenuantes = request.form.get('circunstancias_atenuantes', '').strip() or 'Não há'
        agravantes = request.form.get('circunstancias_agravantes', '').strip() or 'Não há'
        gestor_id = request.form.get('gestor_id') or session.get('user_id')

        error = None
        if not aluno_id:
            error = 'Aluno é obrigatório.'
        elif not data_fmd:
            error = 'Data é obrigatória.'
        elif not tipo_falta_csv:
            error = 'Tipo de falta é obrigatório.'
        elif not medida_aplicada:
            error = 'Medida aplicada é obrigatória.'

        if error:
            flash(error, 'danger')
        else:
            try:
                fmd_id_final = get_proximo_fmd_id(incrementar=True)
                nova_fmd = FichaMedidaDisciplinar(
                    fmd_id=fmd_id_final,
                    aluno_id=int(aluno_id) if aluno_id and str(aluno_id).isdigit() else None,
                    rfo_id=None,
                    data_fmd=data_fmd,
                    tipo_falta=tipo_falta_csv,
                    medida_aplicada=medida_aplicada,
                    descricao_falta=descricao_falta if descricao_falta else None,
                    observacoes=None,
                    responsavel_id=session.get('user_id'),
                    status='ATIVA',
                    data_falta=request.form.get('data_falta') or None,
                    relato_faltas=relato_faltas or None,
                    itens_faltas_ids=','.join(falta_ids_list) if falta_ids_list else None,
                    comportamento_id=int(comportamento_id) if comportamento_id and str(comportamento_id).isdigit() else None,
                    pontuacao_id=int(pontuacao_id) if pontuacao_id and str(pontuacao_id).isdigit() else None,
                    comparecimento_responsavel=comparecimento_val,
                    prazo_comparecimento=prazo_comparecimento if prazo_comparecimento else None,
                    atenuantes=atenuantes,
                    agravantes=agravantes,
                    gestor_id=int(gestor_id) if gestor_id and str(gestor_id).isdigit() else session.get('user_id')
                )
                db.add(nova_fmd)
                db.commit()
                flash(f'FMD {fmd_id_final} registrada com sucesso!', 'success')
                return redirect(url_for('visualizacoes_bp.listar_fmds'))
            except Exception as e:
                db.rollback()
                current_app.logger.exception("Erro ao registrar FMD")
                flash(f'Erro ao registrar FMD: {e}', 'danger')

    return render_template('disciplinar/registrar_fmd.html',
                           fmd_id_gerado=fmd_id_gerado,
                           faltas=faltas,
                           medidas_map=MEDIDAS_MAP,
                           g=g)

@disciplinar_bp.route('/editar_fmd/<int:fmd_id>', methods=['GET', 'POST'])
def editar_fmd(fmd_id):
    db = get_db()
    fmd = (
        db.query(FichaMedidaDisciplinar, Aluno.matricula, Aluno.nome.label('nome_aluno'), Aluno.serie, Aluno.turma)
        .join(Aluno, FichaMedidaDisciplinar.aluno_id == Aluno.id)
        .filter(FichaMedidaDisciplinar.id == fmd_id)
        .first()
    )

    if not fmd:
        flash('FMD não encontrada.', 'danger')
        return redirect(url_for('visualizacoes_bp.listar_fmds'))

    faltas = get_faltas_disciplinares()

    # fmd pode ser Row, namedtuple ou objeto; padroniza para dict para o template
    fmd_dict = dict(fmd._asdict() if hasattr(fmd, "_asdict") else fmd)

    if request.method == 'POST':
        data_fmd = request.form.get('data_fmd')
        tipo_falta = request.form.get('tipo_falta', '').strip()
        medida_aplicada = request.form.get('medida_aplicada', '').strip()
        descricao_falta = request.form.get('descricao_falta', '').strip()
        observacoes = request.form.get('observacoes', '').strip()
        status = request.form.get('status')

        error = None
        if not data_fmd:
            error = 'Data da FMD é obrigatória.'
        elif not tipo_falta:
            error = 'Tipo de falta é obrigatório.'
        elif not medida_aplicada:
            error = 'Medida aplicada é obrigatória.'
        elif not status:
            error = 'Status é obrigatório.'

        if error is None:
            try:
                fmd_obj = db.query(FichaMedidaDisciplinar).filter_by(id=fmd_id).first()
                fmd_obj.data_fmd = data_fmd
                fmd_obj.tipo_falta = tipo_falta
                fmd_obj.medida_aplicada = medida_aplicada
                fmd_obj.descricao_falta = descricao_falta
                fmd_obj.observacoes = observacoes
                fmd_obj.status = status
                db.commit()
                flash(f'FMD {fmd_dict["fmd_id"]} atualizada com sucesso!', 'success')
                return redirect(url_for('visualizacoes_bp.listar_fmds'))
            except Exception as e:
                db.rollback()
                flash(f'Erro ao atualizar FMD: {e}', 'danger')
        else:
            flash(error, 'danger')

    return render_template('disciplinar/editar_fmd.html',
                         fmd=fmd_dict,
                         faltas=faltas,
                         medidas_map=MEDIDAS_MAP)

@disciplinar_bp.route('/excluir_fmd/<int:fmd_id>', methods=['POST'])
@admin_required
def excluir_fmd(fmd_id):
    db = get_db()

    try:
        fmd = db.query(FichaMedidaDisciplinar).filter_by(id=fmd_id).first()

        if not fmd:
            flash('FMD não encontrada.', 'danger')
            return redirect(url_for('visualizacoes_bp.listar_fmds'))

        fmd_id_nome = getattr(fmd, 'fmd_id', '')

        db.delete(fmd)
        db.commit()

        flash(f'FMD {fmd_id_nome} excluída com sucesso.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir FMD: {e}', 'danger')

    return redirect(url_for('visualizacoes_bp.listar_fmds'))

@disciplinar_bp.route('/api/faltas_busca')
def api_faltas_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    db = get_db()
    ids_only = re.fullmatch(r'[\d\s,]+', q)
    try:
        if ids_only:
            ids = [int(x) for x in re.split(r'[\s,]+', q) if x.strip().isdigit()]
            ids = sorted(set(ids))
            if not ids:
                return jsonify([])
            faltas = db.query(FaltaDisciplinar).filter(FaltaDisciplinar.id.in_(ids)).order_by(FaltaDisciplinar.descricao).limit(50).all()
        else:
            q_like = f'%{q}%'
            faltas = db.query(FaltaDisciplinar).filter(FaltaDisciplinar.descricao.ilike(q_like)).order_by(FaltaDisciplinar.descricao).limit(50).all()
        result = []
        seen = set()
        for r in faltas:
            rid = int(r.id)
            if rid in seen:
                continue
            seen.add(rid)
            result.append({'id': rid, 'descricao': r.descricao})
        return jsonify(result)
    except Exception:
        return jsonify([])

@disciplinar_bp.route('/api/comportamentos_busca')
def api_comportamentos_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        comportamentos = (
            db.query(Comportamento)
            .filter(Comportamento.nome.ilike(q_like))
            .order_by(Comportamento.nome)
            .limit(50)
            .all()
        )
    except Exception:
        return jsonify([])
    result = [{'id': r.id, 'nome': r.nome} for r in comportamentos]
    return jsonify(result)

@disciplinar_bp.route('/api/pontuacoes_busca')
def api_pontuacoes_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        pontuacoes = (
            db.query(Pontuacao)
            .filter(Pontuacao.descricao.ilike(q_like))
            .order_by(Pontuacao.descricao)
            .limit(50)
            .all()
        )
    except Exception:
        return jsonify([])
    result = [{'id': r.id, 'descricao': r.descricao} for r in pontuacoes]
    return jsonify(result)

@disciplinar_bp.route('/api/usuarios_busca')
def api_usuarios_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        usuarios = (
            db.query(Usuario)
            .filter((Usuario.username.ilike(q_like)) | (Usuario.full_name.ilike(q_like)))
            .order_by(Usuario.username)
            .limit(50)
            .all()
        )
    except Exception:
        return jsonify([])
    result = [{'id': r.id, 'username': r.username, 'full_name': r.full_name or ''} for r in usuarios]
    return jsonify(result)

from flask import render_template

@disciplinar_bp.route('/fmd_teste_novo')
def fmd_teste_novo():
    # Simulação de dados
    aluno = {
        'nome': 'FULANO DE TAL',
        'serie': '7º',
        'turma': 'B'
    }
    fmd = {
        'fmd_id': 'FMD-0001/2026',
        'pontos_aplicados': -2.0,
        'comportamento': 'Descumprimento das normas',
        'medida_aplicada': 'Advertência Escrita',
        'agravantes': 'Reincidência',
        'atenuantes': 'Arrependimento',
        'comparecimento_responsavel': True,
        'prazo_comparecimento': '10/01/2026',
        'itens_especificacao': 'Artigo 10, inciso II',
    }
    rfo = {
        'data_ocorrencia': '05/01/2026',
        'relato_observador': 'Falta de respeito ao professor.',
    }
    escola = {
        'logotipo_url': '/static/img/logo.png',  # Ajuste para o logo real!
        'nome': 'ESCOLA MODELO',
        'secretaria': 'Secretaria Municipal de Educação',
        'coordenacao': 'Coordenação Pedagógica',
        'estado': 'Estado do Exemplo',
    }
    usuario = {
        'nome': 'MÁRIO RESPONSÁVEL',
        'cargo': 'Gestor Escolar'
    }
    envio = {
        'data_hora': '05/01/2026 14:08',
        'email_destinatario': 'responsavel@email.com'
    }
    return render_template(
        'disciplinar/fmd_novo.html',
        aluno=aluno,
        fmd=fmd,
        rfo=rfo,
        escola=escola,
        usuario=usuario,
        envio=envio
    )

from flask import render_template, g
from flask import request
import sqlite3

def montar_contexto_fmd(db, fmd_id, usuario_sessao_override=None):
    fmd = db.query(FichaMedidaDisciplinar).filter_by(fmd_id=fmd_id).first()
    aluno = db.query(Aluno).filter_by(id=fmd.aluno_id).first() if fmd else None
    cabecalho = db.query(Cabecalho).first() or {}
    escola = {
        'estado': getattr(cabecalho, 'estado', ''),
        'secretaria': getattr(cabecalho, 'secretaria', ''),
        'coordenacao': getattr(cabecalho, 'coordenacao', ''),
        'nome': getattr(cabecalho, 'escola', ''),
        'logotipo_url': '/static/uploads/cabecalhos/' + cabecalho.logo_escola if hasattr(cabecalho, 'logo_escola') and cabecalho.logo_escola else ''
    }
    rfo = db.query(Ocorrencia).filter_by(rfo_id=fmd.rfo_id).first() if fmd else None
    rfo_dict = rfo.__dict__.copy() if rfo else {}
    rfo_dict.pop('_sa_instance_state', None)
    item_descricoes_faltas = []
    ids_faltas = []
    # Busca faltas diretamente da FMD se houver (mais confiável após tratamento)
    if hasattr(fmd, 'falta_disciplinar_ids') and fmd.falta_disciplinar_ids:
        ids_faltas = [id.strip() for id in str(fmd.falta_disciplinar_ids).split(',') if id.strip()]
    # Se não houver na FMD, tenta pegar da RFO vinculada
    elif hasattr(rfo, 'falta_disciplinar_id') and rfo.falta_disciplinar_id:
        ids_faltas.append(str(rfo.falta_disciplinar_id))
    elif hasattr(rfo, 'falta_ids_csv') and rfo.falta_ids_csv:
        ids_faltas = [id.strip() for id in str(rfo.falta_ids_csv).split(',') if id.strip()]

    for falta_id in ids_faltas:
        res = db.query(FaltaDisciplinar).filter_by(id=falta_id).first()
        if res:
            item_descricoes_faltas.append(f"{res.id} - {res.descricao}")
    if item_descricoes_faltas:
        item_descricao_falta = "<br>".join(item_descricoes_faltas)
    else:
        item_descricao_falta = "-"

    itens_especificacao = (
        rfo_dict.get('item_descricao') or
        rfo_dict.get('descricao_item') or
        rfo_dict.get('descricao') or
        rfo_dict.get('falta_descricao') or
        item_descricao_falta or
        '-'
    )
    atenuantes = getattr(fmd, 'atenuantes', '') or rfo_dict.get('circunstancias_atenuantes', '')
    agravantes = getattr(fmd, 'agravantes', '') or rfo_dict.get('circunstancias_agravantes', '')
    envio = {
        'data_hora': getattr(fmd, 'email_enviado_data', None),
        'email_destinatario': getattr(fmd, 'email_enviado_para', None),
    }
    comportamento = "-"
    pontuacao = "-"
    if aluno and hasattr(aluno, 'id'):
        # Pega a data da FMD para usar na busca histórica:
        data_fmd = getattr(fmd, 'data_fmd', None)
        if data_fmd:
            try:
                from services.escolar_helper import compute_pontuacao_em_data
                res = compute_pontuacao_em_data(aluno.id, data_fmd)
                pontuacao = res.get('pontuacao')
                comportamento = res.get('comportamento')
            except Exception:
                pass
    if usuario_sessao_override is not None:
        usuario_sessao = usuario_sessao_override
    else:
        user_id = session.get('user_id')
        usuario_sessao = db.query(Usuario).filter(Usuario.id == user_id).first() if user_id else None
    nome_usuario = getattr(usuario_sessao, 'username', '-') if usuario_sessao else '-'
    cargo_usuario = getattr(usuario_sessao, 'cargo', '-') if usuario_sessao else '-'
    contexto = {
        'escola': escola,
        'aluno': aluno.__dict__.copy() if aluno else {},
        'fmd': dict(fmd._asdict()) if hasattr(fmd, "_asdict") else fmd,
        'rfo': rfo_dict,
        'nome_usuario': nome_usuario,
        'cargo_usuario': cargo_usuario,
        'envio': envio,
        'atenuantes': atenuantes,
        'agravantes': agravantes,
        'comportamento': comportamento,
        'pontuacao': pontuacao,
        'itens_especificacao': itens_especificacao,
        'responsavel': {'nome': aluno.nome if aluno else '-'},
    }
    return contexto

@disciplinar_bp.route('/fmd_novo_real/<path:fmd_id>')
def fmd_novo_real(fmd_id):
    db = get_db()

    # ==== 1. PEGA O USUÁRIO LOGADO NA SESSÃO ====
    user_id = session.get('user_id')
    usuario_sessao = db.query(Usuario).filter(Usuario.id == user_id).first() if user_id else None
    if not usuario_sessao or str(getattr(usuario_sessao, "nivel", None)) not in ['1', '2']:
        return "Você não tem permissão para acessar este documento.", 403

    # ==== 2. Busca a FMD ====
    fmd = db.query(FichaMedidaDisciplinar).filter_by(fmd_id=fmd_id).first()
    if not fmd:
        return 'FMD não encontrada', 404

    # ==== 3. Busca o aluno relacionado ====
    aluno = db.query(Aluno).filter_by(id=fmd.aluno_id).first() or {}

    # REMOVIDO: from models import get_aluno_estado_atual

    comportamento = "-"
    pontuacao = "-"

    if aluno and hasattr(aluno, 'id'):
        p_corrente = compute_pontuacao_corrente(aluno.id)
        if p_corrente is not None:
            # p_corrente pode ser um dict, então busque o campo correto:
            valor_pontuacao = p_corrente if isinstance(p_corrente, (int, float)) else p_corrente.get('pontuacao') or p_corrente.get('pontuacao_atual') or 8.0
            pontuacao = round(float(valor_pontuacao), 2)
            comportamento = _infer_comportamento_por_faixa(valor_pontuacao) or "-"

    # ==== 4. Busca ocorrência relacionada (RFO) ====
    try:
        rfo = db.query(Ocorrencia).filter_by(rfo_id=fmd.rfo_id).first()
    except Exception:
        db.rollback()
        rfo = None
    if not rfo:
        rfo = {}
    item_descricoes_faltas = []

    ids_faltas = []
    if hasattr(rfo, 'falta_disciplinar_id') and rfo.falta_disciplinar_id:
        ids_faltas.append(str(rfo.falta_disciplinar_id))
    elif hasattr(rfo, 'falta_ids_csv') and rfo.falta_ids_csv:
        ids_faltas = [id.strip() for id in str(rfo.falta_ids_csv).split(',') if id.strip()]

    for falta_id in ids_faltas:
        res = db.query(FaltaDisciplinar).filter_by(id=falta_id).first()
        if res:
            item_descricoes_faltas.append(f"{res.id} - {res.descricao}")

    if item_descricoes_faltas:
        item_descricao_falta = "<br>".join(item_descricoes_faltas)
    else:
        item_descricao_falta = "-"

    if rfo:
        # Corrigido para extrair o dicionário do objeto SQLAlchemy
        rfo_dict = rfo.__dict__.copy() if rfo else {}
        # Remove _sa_instance_state, que não é serializável nem útil para templates/views:
        rfo_dict.pop('_sa_instance_state', None)
    else:
        rfo_dict = {}

    itens_especificacao = (
        rfo_dict.get('item_descricao') or
        rfo_dict.get('descricao_item') or
        rfo_dict.get('descricao') or
        rfo_dict.get('falta_descricao') or
        '-'
    )

    # ==== 5. Cabeçalho institucional ====
    cabecalho = db.query(Cabecalho).first() or {}

    escola = {
        'estado': getattr(cabecalho, 'estado', ''),
        'secretaria': getattr(cabecalho, 'secretaria', ''),
        'coordenacao': getattr(cabecalho, 'coordenacao', ''),
        'nome': getattr(cabecalho, 'escola', ''),
        'logotipo_url': '/static/uploads/cabecalhos/' + cabecalho.logo_escola if hasattr(cabecalho, 'logo_escola') and cabecalho.logo_escola else ''
    }

    envio = {
        'data_hora': getattr(fmd, 'email_enviado_data', None),
        'email_destinatario': getattr(fmd, 'email_enviado_para', None),
    }

    # ==== 6. Busca gestor/responsável para carimbo/assinatura ====
    usuario_id_registro = getattr(fmd, 'gestor_id', None) or getattr(fmd, 'responsavel_id', None)
    usuario_registro = db.query(Usuario).filter_by(id=usuario_id_registro).first() or {}

    atenuantes = getattr(fmd, 'atenuantes', '') or rfo_dict.get('circunstancias_atenuantes', '')
    agravantes = getattr(fmd, 'agravantes', '') or rfo_dict.get('circunstancias_agravantes', '')

    nome_usuario = getattr(usuario_sessao, 'username', '-') if usuario_sessao else '-'
    cargo_usuario = getattr(usuario_sessao, 'cargo', '-') if usuario_sessao else '-'

    contexto = montar_contexto_fmd(db, fmd_id, usuario_sessao)

    if request.args.get('salvar_pdf') == '1':
        import pdfkit, os
        from urllib.parse import quote

        logo_relativo = contexto.get('escola', {}).get('logotipo_url', '')
        if logo_relativo:
            logo_relativo = logo_relativo.lstrip("/")
            caminho_absoluto = os.path.join(
                r"C:\Users\Usuário\Documents\GitHub\escolar\escola", logo_relativo
            )
            contexto['logo_pdfkit_path'] = "file:///" + quote(caminho_absoluto.replace("\\", "/"))
        else:
            contexto['logo_pdfkit_path'] = ""

        html = render_template('disciplinar/fmd_novo_pdf.html', **contexto)
        temp_dir = 'tmp'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        safe_fmd_id = str(fmd_id).replace('/', '_')
        pdf_path = os.path.join(temp_dir, f"{safe_fmd_id}.pdf")
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Arquivos de Programas\wkhtmltopdf\bin\wkhtmltopdf.exe')
        options = {'encoding': 'UTF-8', 'enable-local-file-access': None}
        pdfkit.from_string(html, pdf_path, configuration=config, options=options)

    return render_template('disciplinar/fmd_novo.html', **contexto)

@disciplinar_bp.route('/enviar_email_fmd/<path:fmd_id>', methods=['POST'])
def enviar_email_fmd(fmd_id):
    from flask import redirect, url_for, flash
    import datetime
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import os
    from email.mime.application import MIMEApplication

    db = get_db()
    user_id = session.get('user_id')
    usuario_obj = db.query(Usuario).filter(Usuario.id == user_id).first() if user_id else None
    nome_usuario = getattr(usuario_obj, 'username', 'Usuário do sistema')
    cargo_usuario = getattr(usuario_obj, 'cargo', '')

    # Busca os dados da FMD
    fmd = db.query(FichaMedidaDisciplinar).filter_by(fmd_id=fmd_id).first()
    if not fmd:
        flash('FMD não encontrada!', 'alert-danger')
        return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

    # Busca o aluno e seu e-mail
    aluno = db.query(Aluno).filter_by(id=fmd.aluno_id).first()
    email_destinatario = getattr(aluno, 'email', None) if aluno else None

    if not email_destinatario:
        flash('Não existe e-mail cadastrado para este aluno.', 'alert-danger')
        return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

    # Busca o e-mail e a senha de app da escola
    dados_escola = db.query(DadosEscola).first()
    email_remetente = getattr(dados_escola, 'email_remetente', None)
    senha_email_app = getattr(dados_escola, 'senha_email_app', None)
    telefone_escola = getattr(dados_escola, 'telefone', '')

    if not email_remetente or not senha_email_app:
        flash('Não há e-mail institucional e/ou senha de aplicativo cadastrados para a escola.', 'danger')
        return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

    assunto = "Ficha de Medida Disciplinar"

    def get_fmd_field(row, key):
        try:
            return getattr(row, key, '')
        except Exception:
            return ''
        
    def safe_value(val):
        return val if val not in (None, '', 'None') else '—'

    corpo_html = f"""
    <html>
    <body>
        <p>Prezado responsável,<br>
        Segue a Ficha de Medida Disciplinar referente ao(a) aluno(a): <b>{getattr(aluno, 'nome', '')}</b>.
        <br><br>
        Tipo de falta: <b>{safe_value(get_fmd_field(fmd,'tipo_falta'))}</b><br>
        Medida aplicada: <b>{safe_value(get_fmd_field(fmd,'medida_aplicada'))}</b><br>
        {"Descrição: <b>{}</b><br>".format(safe_value(get_fmd_field(fmd,'descricao_detalhada'))) if get_fmd_field(fmd,'descricao_detalhada') else ""}
        <br>
        <i>Favor entrar em contato com a escola caso necessário. Telefone: <b>{telefone_escola}</b></i>
        </p>
        <br><br>
        Atenciosamente,<br>
        <b>{nome_usuario}</b><br>
        {cargo_usuario}<br>
        {getattr(dados_escola, 'nome', '')}
    </body>
    </html>
    """

    try:
        temp_dir = "tmp"
        safe_fmd_id = str(fmd_id).replace('/', '_')
        pdf_path = os.path.join(temp_dir, f"{safe_fmd_id}.pdf")
        if not os.path.exists(pdf_path):
            flash('O PDF da FMD não foi gerado corretamente. Por favor, gere novamente a FMD antes de enviar por e-mail.', 'danger')
            return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = email_destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html'))

        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_email_app)
        server.sendmail(email_remetente, email_destinatario, msg.as_string())
        server.quit()

        data_envio = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        fmd.email_enviado_data = data_envio
        fmd.email_enviado_para = email_destinatario
        db.commit()
        flash("FMD enviada por e-mail com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao enviar o e-mail: {e}", "danger")

    return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))
