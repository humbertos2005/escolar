from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, g, current_app

# ATEN��O: ajuste o caminho relativo conforme sua estrutura de pastas
from escola.services.escolar_helper import (
    get_proximo_rfo_id,
    get_tipos_ocorrencia,
    get_proximo_fmd_id,
    get_faltas_disciplinares,
    ensure_disciplinar_migrations,
    next_fmd_seq_and_year,
)

from escola.models import get_db  # mant�m apenas aquilo relacionado � sess�o do banco (ou troque para ORM futuramente)

from .utils import (
    login_required,
    admin_required,
    admin_secundario_required,
    INFRACAO_MAP,
    TIPO_OCORRENCIA_MAP,
    TIPO_FALTA_MAP,
    MEDIDAS_MAP
)
from datetime import datetime, date
import sqlite3
import re
import os
# Remover 'import models' se n�o h� mais uso direto das fun��es dela. 
# Se sobrar chamada tipo models.fun��o_que_vai_para_o_helper, corrija tamb�m!
# import models

# Adicionar (logo ap�s os imports j� existentes)
import pdfkit
import shutil
from werkzeug.utils import secure_filename
from flask import Response, abort

from escola.blueprints.prontuario_utils import create_or_append_prontuario_por_rfo

disciplinar_bp = Blueprint('disciplinar_bp', __name__, url_prefix='/disciplinar')

@disciplinar_bp.before_app_request
def _ensure_disciplinar_schema():
    # roda apenas uma vez por processo/app usando flag em current_app (idempotente)
    if getattr(current_app, "_disciplinar_migrations_done", False):
        return
    try:
        db = get_db()
        ensure_disciplinar_migrations()
        current_app._disciplinar_migrations_done = True
        current_app.logger.info("ensure_disciplinar_migrations executed")
    except Exception as e:
        current_app.logger.exception("Erro ao garantir migrations disciplinar: %s", e)

# Utilit�rio robusto para criar uma FMD m�nima para um aluno (se a tabela existir)
def _create_fmd_for_aluno(db, aluno_id, medida_aplicada, descricao, data_fmd=None):
    from datetime import date
    if data_fmd is None:
        data_fmd = date.today().isoformat()
    try:
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ficha_medida_disciplinar'").fetchone()
        if not cur:
            return False
        seq, ano = next_fmd_seq_and_year()
        fmd_id = f"FMD-{seq}/{ano}"
        try:
            db.execute("""
                INSERT INTO ficha_medida_disciplinar (fmd_id, aluno_id, data_fmd, medida_aplicada, descricao_falta, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fmd_id, aluno_id, data_fmd, medida_aplicada, descricao or '', 'ATIVA'))
        except Exception:
            db.execute("""
                INSERT INTO ficha_medida_disciplinar (fmd_id, aluno_id, data_fmd, medida_aplicada)
                VALUES (?, ?, ?, ?)
            """, (fmd_id, aluno_id, data_fmd, medida_aplicada))
        try:
            db.commit()
        except Exception:
            pass
        return True
    except Exception:
        return False

# -----------------------
# Novos helpers para detec��o de colunas e compatibilidade
# -----------------------
def _get_table_columns(db_conn, table):
    """Retorna lista de nomes de colunas para a tabela (SQLite PRAGMA ou fallback)."""
    try:
        rows = db_conn.execute(f"PRAGMA table_info({table})").fetchall()
        cols = []
        for r in rows:
            # row pode ser sqlite3.Row com index ou dict-like
            if isinstance(r, dict):
                cols.append(r.get('name'))
            else:
                # PRAGMA result: cid, name, type, notnull, dflt_value, pk
                cols.append(r[1])
        return [c for c in cols if c]
    except Exception:
        return []

def _find_first_column(db_conn, table, candidates):
    cols = _get_table_columns(db_conn, table)
    for c in candidates:
        if c in cols:
            return c
    return None

# -----------------------
# API: checa reincid�ncia
# -----------------------
@disciplinar_bp.route('/api/check_reincidencia', methods=['GET'])
@login_required
def api_check_reincidencia():
    """
    Par�metros:
      - aluno_id (int) REQUIRED
      - falta_id (int) OR descricao (string) REQUIRED (pelo menos um)
    Retorna JSON: { exists: bool, count: int, last: { id, tipo, created_at } or null }
    """
    db = get_db()
    aluno_id = request.args.get('aluno_id', type=int)
    falta_id = request.args.get('falta_id', type=int)
    descricao = request.args.get('descricao', type=str)

    if not aluno_id:
        return jsonify(error='Par�metro aluno_id � obrigat�rio'), 400

    # detectar colunas
    aluno_col = _find_first_column(db, 'ocorrencias', ['aluno_id', 'aluno', 'matricula'])
    tipo_col = _find_first_column(db, 'ocorrencias', ['tipo_falta', 'tipo', 'tipo_ocorrencia', 'falta_tipo', 'classificacao'])
    created_col = _find_first_column(db, 'ocorrencias', ['data_tratamento', 'data_registro', 'created_at', 'data'])

    item_id_col = _find_first_column(db, 'ocorrencias', ['falta_disciplinar_id', 'falta_id', 'item_id', 'item'])
    descr_cols_candidates = ['descricao', 'descricao_falta', 'item_descricao', 'falta_descricao', 'descricao_ocorrencia', 'relato_observador', 'relato_faltas', 'obs']

    descr_cols = [c for c in _get_table_columns(db, 'ocorrencias') if c in descr_cols_candidates]

    if not aluno_col:
        return jsonify(error='Coluna de identifica��o do aluno n�o encontrada na tabela ocorrencias'), 500

    where_clauses = []
    params = []
    where_clauses.append(f"{aluno_col} = ?")
    params.append(aluno_id)

    if falta_id is not None:
        if item_id_col:
            where_clauses.append(f"{item_id_col} = ?")
            params.append(falta_id)
        else:
            return jsonify(error='falta_id fornecido, mas coluna correspondente n�o encontrada'), 400
    elif descricao:
        if not descr_cols:
            return jsonify(error='Descri��o fornecida, mas n�o foi encontrada coluna de descri��o na tabela ocorrencias'), 400
        sub = []
        for c in descr_cols:
            sub.append(f"({c} = ? OR {c} LIKE ?)")
            params.extend([descricao, f"%{descricao}%"])
        where_clauses.append("(" + " OR ".join(sub) + ")")
    else:
        return jsonify(error='Par�metro falta_id ou descricao � obrigat�rio'), 400

    where_sql = " AND ".join(where_clauses)

    # contar ocorr�ncias e buscar a �ltima (por created_at ou por id descendente)
    try:
        count_row = db.execute(f"SELECT COUNT(*) as cnt FROM ocorrencias WHERE {where_sql}", params).fetchone()
        count = count_row['cnt'] if isinstance(count_row, dict) else count_row[0]
    except Exception:
        current_app.logger.exception('Erro ao contar ocorr�ncias para check_reincidencia')
        return jsonify(error='Erro ao consultar banco'), 500

    order_by = f"{created_col} DESC" if created_col else "id DESC"
    tipo_select = tipo_col if tipo_col else 'NULL as tipo'
    created_select = created_col if created_col else 'NULL as created_at'
    try:
        last_row = db.execute(f"SELECT id, {tipo_select} as tipo, {created_select} as created_at FROM ocorrencias WHERE {where_sql} ORDER BY {order_by} LIMIT 1", params).fetchone()
    except Exception:
        current_app.logger.exception('Erro ao buscar �ltima ocorr�ncia para check_reincidencia')
        last_row = None

    if last_row:
        last_obj = dict(last_row) if not isinstance(last_row, tuple) else {'id': last_row[0], 'tipo': last_row[1], 'created_at': last_row[2]}
    else:
        last_obj = None

    return jsonify(exists=(count > 0), count=count, last=last_obj)


# -----------------------
# Endpoint: reclassificar ocorr�ncia existente (atualiza tipo)
# -----------------------
@disciplinar_bp.route('/reclassificar_ocorrencia', methods=['POST'])
@login_required
def reclassificar_ocorrencia():
    """
    Form data:
      - ocorrencia_id (int) REQUIRED
      - new_tipo (string) REQUIRED
    Atualiza a coluna tipo_falta (ou equivalente) da ocorr�ncia indicada.
    """
    db = get_db()
    ocorrencia_id = request.form.get('ocorrencia_id', type=int) or request.form.get('ocorrencia_id')
    new_tipo = request.form.get('new_tipo', type=str) or request.form.get('new_tipo')

    try:
        ocorrencia_id = int(ocorrencia_id)
    except Exception:
        return jsonify(error='ocorrencia_id inv�lido'), 400

    if not new_tipo:
        return jsonify(error='new_tipo � obrigat�rio'), 400

    tipo_col = _find_first_column(db, 'ocorrencias', ['tipo_falta', 'tipo', 'falta_tipo', 'classificacao'])
    if not tipo_col:
        return jsonify(error='Coluna onde gravar tipo n�o encontrada'), 500

    try:
        db.execute(f"UPDATE ocorrencias SET {tipo_col} = ? WHERE id = ?", (new_tipo, ocorrencia_id))
        db.commit()
    except Exception:
        current_app.logger.exception('Erro ao reclassificar ocorr�ncia')
        db.rollback()
        return jsonify(error='Erro ao atualizar ocorr�ncia'), 500

    return jsonify(success=True)


# -----------------------
# Fun��es existentes do arquivo (mantive integra��es; apenas acrescentei compatibilidade abaixo)
# -----------------------

# Helper: salva rela��es ocorrencia <-> faltas selecionadas
def salvar_faltas_relacionadas(db_conn, ocorrencia_id, falta_ids_list):
    """
    Garante a exist�ncia da tabela relacional e salva as rela��es ocorrencia <-> faltas.
    falta_ids_list: lista de ids (inteiros)
    Observa��o: n�o faz commit; o chamador deve commitar.
    """
    try:
        db_conn.execute('''
            CREATE TABLE IF NOT EXISTS ocorrencias_faltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ocorrencia_id INTEGER NOT NULL,
                falta_id INTEGER NOT NULL,
                FOREIGN KEY (ocorrencia_id) REFERENCES ocorrencias(id) ON DELETE CASCADE,
                FOREIGN KEY (falta_id) REFERENCES faltas_disciplinares(id)
            );
        ''')
    except Exception:
        # Se falhar, segue em frente (poss�vel em ambientes restritos)
        pass

    try:
        db_conn.execute('DELETE FROM ocorrencias_faltas WHERE ocorrencia_id = ?', (ocorrencia_id,))
    except Exception:
        pass

    if not falta_ids_list:
        return

    for fid in falta_ids_list:
        try:
            db_conn.execute('INSERT INTO ocorrencias_faltas (ocorrencia_id, falta_id) VALUES (?, ?)', (ocorrencia_id, fid))
        except Exception:
            # ignora ids inv�lidos
            pass

# -----------------------
# Helpers novos para pontua��o (mantive inalterados)
# -----------------------
def _get_config_values(db_conn):
    """L� tabela_disciplinar_config e retorna dict de valores (fallback defaults se ausente)."""
    defaults = {
        'advertencia_oral': -0.1,
        'advertencia_escrita': -0.3,
        'suspensao_dia': -0.5,
        'acao_educativa_dia': -1.0,
        'elogio_individual': 0.5,
        'elogio_coletivo': 0.3
    }
    try:
        rows = db_conn.execute('SELECT chave, valor FROM tabela_disciplinar_config').fetchall()
        for r in rows:
            defaults[r['chave']] = float(r['valor'])
    except Exception:
        # tabela pode n�o existir ainda
        pass
    return defaults

def _get_bimestre_for_date(db_conn, data_str):
    """
    Determina (ano_int, bimestre_int) consultando a tabela 'bimestres'.
    Usa as colunas (ano, numero, inicio, fim). Para o ano da data, procura
    uma linha cujo intervalo inicio..fim contenha a data e retorna (ano, numero).
    Se n�o encontrar ou ocorrer erro, faz fallback para 4 bimestres por ano
    (cada 3 meses) para manter compatibilidade.
    """
    try:
        d = datetime.strptime(data_str[:10], '%Y-%m-%d').date()
    except Exception:
        d = date.today()
    ano = d.year
    try:
        rows = db_conn.execute(
            "SELECT numero, inicio, fim FROM bimestres WHERE ano = ? ORDER BY numero",
            (ano,)
        ).fetchall()
        if rows:
            for r in rows:
                try:
                    num = int(r['numero']) if r['numero'] is not None else None
                except Exception:
                    num = None
                inicio = r.get('inicio') if isinstance(r, dict) else r['inicio']
                fim = r.get('fim') if isinstance(r, dict) else r['fim']
                try:
                    inicio_date = datetime.strptime(inicio[:10], '%Y-%m-%d').date() if inicio else None
                except Exception:
                    inicio_date = None
                try:
                    fim_date = datetime.strptime(fim[:10], '%Y-%m-%d').date() if fim else None
                except Exception:
                    fim_date = None
                # Se inicio/fim n�o definidos, consideramos compat�vel (aberto)
                if (inicio_date is None or inicio_date <= d) and (fim_date is None or fim_date >= d):
                    if num is not None:
                        return ano, num
    except Exception:
        try:
            from flask import current_app
            current_app.logger.debug("Erro ao consultar tabela bimestres; usando fallback.")
        except Exception:
            pass
    # fallback: 4 bimestres por ano (cada 3 meses)
    b = ((d.month - 1) // 3) + 1
    return ano, b

def _calcular_delta_por_medida(medida_aplicada, qtd, config):
    """
    Calcula o delta (positivo/negativo) aplic�vel � pontua��o a partir do texto da medida e quantidade.
    qtd: n�mero (ex.: dias ou ocorr�ncias)
    config: dict com valores
    """
    if not medida_aplicada:
        return 0.0
    m = medida_aplicada.strip().upper()
    try:
        qtd = float(qtd or 1)
    except Exception:
        qtd = 1.0
    # compara��es simples � adapt�veis conforme nomes exatos em MEDIDAS_MAP
    if 'ORAL' in m and 'ADVERT' in m:
        return qtd * float(config.get('advertencia_oral', -0.1))
    if 'ESCRIT' in m and 'ADVERT' in m:
        return qtd * float(config.get('advertencia_escrita', -0.3))
    if 'SUSPENS' in m:
        # tentar extrair dias num�ricos do texto
        nums = re.findall(r'(\d+)', m)
        dias = int(nums[0]) if nums else int(qtd)
        return dias * float(config.get('suspensao_dia', -0.5))
    if 'ACAO' in m or 'A��O' in m or 'EDUCATIVA' in m:
        nums = re.findall(r'(\d+)', m)
        dias = int(nums[0]) if nums else int(qtd)
        return dias * float(config.get('acao_educativa_dia', -1.0))
    if 'ELOGIO' in m and 'INDIVIDU' in m:
        return qtd * float(config.get('elogio_individual', 0.5))
    if 'ELOGIO' in m and 'COLET' in m:
        return qtd * float(config.get('elogio_coletivo', 0.3))
    # fallback
    return 0.0

def _next_fmd_sequence(db_conn):
    """
    Retorna (seq_int, ano_int) com o pr�ximo n�mero sequencial para o ano corrente.
    Mant�m/atualiza tabela fmd_sequencia (ano INTEGER PRIMARY KEY, seq INTEGER).
    Se a tabela n�o existir, a fun��o tenta computar a sequ�ncia a partir dos fmd_id existentes.
    """
    ano = datetime.now().year
    try:
        row = db_conn.execute('SELECT seq FROM fmd_sequencia WHERE ano = ?', (ano,)).fetchone()
        if row and row['seq'] is not None:
            seq = int(row['seq']) + 1
            db_conn.execute('UPDATE fmd_sequencia SET seq = ? WHERE ano = ?', (seq, ano))
            return seq, ano
    except Exception:
        # continua para tentativa de calcular a partir dos fmd_id existentes
        pass

    # calcula o maior seq j� presente no formato FMD-NNNN/YYYY (caso haja fmd_id j� no novo formato)
    maxseq = 0
    try:
        rows = db_conn.execute("SELECT fmd_id FROM ficha_medida_disciplinar WHERE fmd_id LIKE ?", (f"FMD-%/{ano}",)).fetchall()
        for r in rows:
            fid = r['fmd_id'] or ''
            m = re.match(r'^FMD-(\d{1,})/' + str(ano) + r'$', fid)
            if m:
                try:
                    n = int(m.group(1))
                    if n > maxseq:
                        maxseq = n
                except Exception:
                    pass
    except Exception:
        maxseq = 0

    seq = maxseq + 1
    try:
        db_conn.execute('INSERT INTO fmd_sequencia (ano, seq) VALUES (?, ?)', (ano, seq))
    except Exception:
        # se insert falhar, ainda assim retornamos seq calculado
        pass
    return seq, ano

def _apply_delta_pontuacao(db_conn, aluno_id, data_tratamento_str, delta, ocorrencia_id=None, tipo_evento=None):
    """
    Aplica delta na pontuacao_bimestral do aluno (cria linha se inexistente).
    Garante limites m�nimos/ m�ximos (0.0 .. 10.0).
    Registra no pontuacao_historico.
    """
    if not aluno_id:
        return
    ano, bimestre = _get_bimestre_for_date(db_conn, data_tratamento_str)
    try:
        row = db_conn.execute('SELECT id, pontuacao_inicial, pontuacao_atual FROM pontuacao_bimestral WHERE aluno_id = ? AND ano = ? AND bimestre = ?', (aluno_id, ano, bimestre)).fetchone()
        if row:
            atual = float(row['pontuacao_atual'])
            novo = max(0.0, min(10.0, atual + float(delta)))
            db_conn.execute('UPDATE pontuacao_bimestral SET pontuacao_atual = ?, atualizado_em = ? WHERE id = ?', (novo, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), row['id']))
        else:
            inicial = 8.0
            novo = max(0.0, min(10.0, inicial + float(delta)))
            db_conn.execute('INSERT INTO pontuacao_bimestral (aluno_id, ano, bimestre, pontuacao_inicial, pontuacao_atual, atualizado_em) VALUES (?, ?, ?, ?, ?, ?)', (aluno_id, ano, bimestre, inicial, novo, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        # historico
        db_conn.execute('INSERT INTO pontuacao_historico (aluno_id, ano, bimestre, ocorrencia_id, tipo_evento, valor_delta, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)', (
            aluno_id, ano, bimestre, ocorrencia_id, tipo_evento, float(delta), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    except Exception:
        # se tabela nao existe, ignora (migration pendente)
        current_app.logger.exception('Erro ao aplicar delta pontuacao (poss�vel tabela ausente).')


# -----------------------
# Rotas existentes (mantive as defini��es originais)
# -----------------------

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
            rows = db.execute('''
                SELECT id, matricula, nome, serie, turma
                FROM alunos
                WHERE id = ? OR matricula LIKE ? OR nome LIKE ?
                ORDER BY nome
                LIMIT 20
            ''', (int(num), f'%{num}%', f'%{num}%')).fetchall()
        else:
            if len(termo_busca) < 3:
                return jsonify([])
            q_like = f'%{termo_busca}%'
            rows = db.execute('''
                SELECT id, matricula, nome, serie, turma
                FROM alunos
                WHERE matricula LIKE ? OR nome LIKE ?
                ORDER BY nome
                LIMIT 20
            ''', (q_like, q_like)).fetchall()

        for aluno in rows:
            resultados.append({
                'id': aluno['id'],
                'value': f"{aluno['matricula']} - {aluno['nome']}",
                'matricula': aluno['matricula'],
                'nome': aluno['nome'],
                'data': {'serie': aluno.get('serie') if isinstance(aluno, dict) else aluno['serie'],
                         'turma': aluno.get('turma') if isinstance(aluno, dict) else aluno['turma']}
            })
    except sqlite3.Error:
        return jsonify([])

    return jsonify(resultados)


@disciplinar_bp.route('/registrar_rfo', methods=['GET', 'POST'])
@login_required
def registrar_rfo():
    db = get_db()
    cursor = db.cursor()
    rfo_id_gerado = get_proximo_rfo_id()
    tipos_ocorrencia = get_tipos_ocorrencia()

    if request.method == 'POST':
        # aceitar m�ltiplos alunos: getlist ou CSV/single
        aluno_ids = request.form.getlist('aluno_id')
        if not aluno_ids or all(not a for a in aluno_ids):
            raw = request.form.get('aluno_ids') or request.form.get('aluno_id') or ''
            aluno_ids = [s.strip() for s in raw.split(',') if s.strip()]

        # leitura do formul�rio (capturar tipo de RFO e subtipo de elogio)
        # leitura do formul�rio (capturar tipo de RFO e subtipo de elogio)
        tipo_ocorrencia_id = request.form.get('tipo_ocorrencia_id')
        data_ocorrencia = request.form.get('data_ocorrencia')
        observador_id = request.form.get('observador_id')
        relato_observador = request.form.get('relato_observador', '').strip()

        # tipo_rfo � o radio (Falta Disciplinar / Elogio)
        tipo_rfo = request.form.get('tipo_rfo', '').strip()
        subtipo_elogio = request.form.get('subtipo_elogio', '').strip()

        # material_recolhido e advertencia_oral v�m do formul�rio
        material_recolhido = request.form.get('material_recolhido', '').strip()
        advertencia_oral = request.form.get('advertencia_oral', '').strip()

        # valida��es m�nimas:
        # - campos obrigat�rios b�sicos (tipo_ocorrencia_id, data, observador, relato)
        # - advertencia_oral s� � obrigat�rio quando n�o for Elogio
        error = None
        if not aluno_ids or not all([tipo_ocorrencia_id, data_ocorrencia, observador_id, relato_observador]):
            error = 'Por favor, preencha todos os campos obrigat�rios.'
        elif tipo_rfo != 'Elogio' and advertencia_oral not in ['sim', 'nao']:
            error = 'Selecione se a ocorr�ncia deve ser considerada como Advert�ncia Oral.'

        if error:
            flash(error, 'danger')
            return render_template('disciplinar/registrar_rfo.html',
                                   rfo_id_gerado=rfo_id_gerado,
                                   tipos_ocorrencia=tipos_ocorrencia,
                                   request_form=request.form,
                                   g=g)

        # garantir valor coerente de advertencia_oral
        if tipo_rfo == 'Elogio':
            advertencia_oral = 'nao'
        else:
            advertencia_oral = advertencia_oral or 'nao'

        # gerar RFO final e persistir
        try:
            rfo_id_final = get_proximo_rfo_id(incrementar=True)

            # Compatibilidade: garantir que valid_aluno_ids esteja definido (padr�o para aluno_ids)
            try:
                valid_aluno_ids  # apenas testa exist�ncia
            except NameError:
                try:
                    valid_aluno_ids = aluno_ids
                except NameError:
                    valid_aluno_ids = []
            
            if not valid_aluno_ids:
                flash('Nenhum aluno v�lido selecionado.', 'danger')
                return render_template('disciplinar/registrar_rfo.html',
                                       rfo_id_gerado=rfo_id_gerado,
                                       tipos_ocorrencia=tipos_ocorrencia,
                                       request_form=request.form,
                                       g=g)
            
            primeiro_aluno = valid_aluno_ids[0]

            # Inserir ocorr�ncia principal, gravando tamb�m tratamento_tipo e subtipo_elogio
            cursor.execute("""
                INSERT INTO ocorrencias (
                    rfo_id, aluno_id, tipo_ocorrencia_id, data_ocorrencia,
                    observador_id, relato_observador, advertencia_oral, material_recolhido,
                    tratamento_tipo, subtipo_elogio,
                    responsavel_registro_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AGUARDANDO TRATAMENTO')
            """, (
                rfo_id_final, primeiro_aluno, tipo_ocorrencia_id, data_ocorrencia,
                observador_id, relato_observador, advertencia_oral, material_recolhido,
                tipo_rfo, subtipo_elogio,
                session.get('user_id')
            ))
            db.commit()
            ocorrencia_id = cursor.lastrowid

            # vincular todos os alunos em ocorrencias_alunos (mant�m comportamento anterior)
            for aid in valid_aluno_ids:
                try:
                    cursor.execute("INSERT INTO ocorrencias_alunos (ocorrencia_id, aluno_id) VALUES (?, ?)",
                                   (ocorrencia_id, aid))
                except Exception:
                    try:
                        cursor.execute("INSERT INTO ocorrencias_alunos (ocorrencia_id, aluno_id) VALUES (?, ?)",
                                       (ocorrencia_id, str(aid)))
                    except Exception:
                        # ignora caso n�o seja poss�vel vincular um aluno
                        pass
            db.commit()

            # sucesso: informar e redirecionar
            flash(f'RFO {rfo_id_final} registrado com sucesso!', 'success')
            return redirect(url_for('disciplinar_bp.listar_rfo'))

        except sqlite3.IntegrityError as e:
            db.rollback()
            flash(f'Erro de integridade ao registrar RFO: {e}', 'danger')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'Erro ao registrar RFO: {e}', 'danger')
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Erro ao registrar RFO")
            flash(f'Erro ao registrar RFO: {e}', 'danger')
            flash(f'RFO {rfo_id_final} registrado com sucesso!', 'success')
            return redirect(url_for('disciplinar_bp.listar_rfo'))

        except Exception as e:
            db.rollback()
            current_app.logger.exception("Erro ao registrar RFO")
            flash(f'Erro ao registrar RFO: {e}', 'danger')

        except sqlite3.IntegrityError as e:
            flash(f'Erro de integridade ao registrar RFO: {e}', 'danger')
            db.rollback()
        except sqlite3.Error as e:
            flash(f'Erro ao registrar RFO: {e}', 'danger')
            db.rollback()
        except Exception as e:
            flash(f'Ocorreu um erro inesperado: {e}', 'danger')
            db.rollback()

    return render_template('disciplinar/registrar_rfo.html',
                           rfo_id_gerado=rfo_id_gerado,
                           tipos_ocorrencia=tipos_ocorrencia,
                           g=g)

@disciplinar_bp.route('/listar_rfo')
@admin_secundario_required
def listar_rfo():
    db = get_db()

    rfos = db.execute('''
        SELECT
            o.id, o.rfo_id, o.data_ocorrencia, o.tipo_ocorrencia_id, o.status,
            o.relato_observador, o.advertencia_oral, o.material_recolhido,
            GROUP_CONCAT(oa_alunos.nome, '; ') AS alunos,
            COALESCE(main_aluno.matricula, oa_alunos.matricula) AS matricula,
            COALESCE(main_aluno.nome, oa_alunos.nome) AS nome_aluno,
            COALESCE(
                GROUP_CONCAT(oa_alunos.serie || ' - ' || oa_alunos.turma, '; '),
                main_aluno.serie || ' - ' || main_aluno.turma
            ) AS series_turmas,
            u.username AS responsavel_registro_username,
            tipo_oc.nome AS tipo_ocorrencia_nome
        FROM ocorrencias o
        LEFT JOIN ocorrencias_alunos oa ON oa.ocorrencia_id = o.id
        LEFT JOIN alunos oa_alunos ON oa_alunos.id = oa.aluno_id
        LEFT JOIN alunos main_aluno ON main_aluno.id = o.aluno_id
        LEFT JOIN usuarios u ON o.responsavel_registro_id = u.id
        LEFT JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        WHERE o.status = 'AGUARDANDO TRATAMENTO'
        GROUP BY o.id
        ORDER BY o.data_registro DESC
    ''').fetchall()

    rfos_list = [dict(rfo) for rfo in rfos]
    return render_template('disciplinar/listar_rfo.html', rfos=rfos_list)


@disciplinar_bp.route('/visualizar_rfo/<int:ocorrencia_id>')
@admin_secundario_required
def visualizar_rfo(ocorrencia_id):
    db = get_db()

    rfo = db.execute('''
        SELECT
            o.*,
            GROUP_CONCAT(a.nome, '; ') AS alunos,
            GROUP_CONCAT(a.serie || ' - ' || a.turma, '; ') AS series_turmas,
            a.matricula, a.nome AS nome_aluno, a.serie, a.turma,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            u.username AS responsavel_registro_username
        FROM ocorrencias o
        LEFT JOIN ocorrencias_alunos oa ON oa.ocorrencia_id = o.id
        LEFT JOIN alunos a ON a.id = oa.aluno_id
        LEFT JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        LEFT JOIN usuarios u ON o.responsavel_registro_id = u.id
        WHERE o.id = ?
        GROUP BY o.id
    ''', (ocorrencia_id,)).fetchone()

    if rfo is None:
        flash('RFO n�o encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    # transformar em dict mut�vel
    rfo_dict = dict(rfo)

    # Refor�ar montagem expl�cita de s�ries/turmas lendo ocorrencias_alunos para garantir exibi��o correta
    alunos_rows = db.execute('''
        SELECT al.matricula, al.nome, al.serie, al.turma
        FROM ocorrencias_alunos oa
        LEFT JOIN alunos al ON al.id = oa.aluno_id
        WHERE oa.ocorrencia_id = ?
        ORDER BY oa.id
    ''', (ocorrencia_id,)).fetchall()

    series_list = []
    names_list = []
    for ar in alunos_rows:
        s = (ar['serie'] or '') 
        t = (ar['turma'] or '')
        if s or t:
            series_list.append(f"{s} - {t}".strip(' - '))
        # montar nomes tamb�m como fonte �nica de verdade (caso queira sincronizar)
        names_list.append(ar['nome'] or '')

    # preferir string constru�da a partir de ocorrencias_alunos quando houver
    if series_list:
        rfo_dict['series_turmas'] = '; '.join(series_list)
    else:
        # fallback ao que veio no SELECT (ou campos individuais)
        rfo_dict['series_turmas'] = rfo_dict.get('series_turmas') or ((rfo_dict.get('serie') and rfo_dict.get('turma')) and f"{rfo_dict.get('serie')} - {rfo_dict.get('turma')}" or '')

    # garantir que 'alunos' contenha os nomes corretos (preferir lista constru�da)
    if any(names_list):
        # manter ordem dos alunos da tabela ocorrencias_alunos
        rfo_dict['alunos'] = '; '.join([n for n in names_list if n])
    else:
        rfo_dict['alunos'] = rfo_dict.get('alunos') or rfo_dict.get('nome_aluno') or ''

    # material_recolhido_info: use material_recolhido quando presente; caso contr�rio construir a partir de tratamento
    tratamento = rfo_dict.get('tratamento_tipo') or rfo_dict.get('tipo_ocorrencia_text') or rfo_dict.get('tipo_ocorrencia_nome') or ''
    associado = (rfo_dict.get('advertencia_oral') or rfo_dict.get('subtipo_elogio') or '')
    if isinstance(associado, bool):
        associado = 'Sim' if associado else 'N�o'
    material_info = rfo_dict.get('material_recolhido') or ''
    if (not material_info) and tratamento:
        material_info = tratamento
        if associado:
            material_info = f"{tratamento} � {associado}"
    rfo_dict['material_recolhido_info'] = material_info

    return render_template('disciplinar/visualizar_rfo.html', rfo=rfo_dict)

    if rfo is None:
        flash('RFO n�o encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    # Garantir dict mut�vel e adicionar campo de exibi��o material_recolhido_info
    rfo_dict = dict(rfo)
    tipo = rfo_dict.get('trata_se') or rfo_dict.get('tipo_rfo') or rfo_dict.get('tipo') or rfo_dict.get('trata_tipo') or ''
    associado = (rfo_dict.get('advertencia_oral')
                 or rfo_dict.get('tipo_elogio')
                 or rfo_dict.get('subtipo')
                 or rfo_dict.get('considerar_advertencia_oral')
                 or '')
    if isinstance(associado, bool):
        associado = 'Sim' if associado else 'N�o'
    material_info = tipo
    if associado:
        material_info = f"{tipo} � {associado}"
    rfo_dict['material_recolhido_info'] = material_info

    return render_template('disciplinar/visualizar_rfo.html', rfo=rfo_dict)

    if rfo is None:
        flash('RFO n�o encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    return render_template('disciplinar/visualizar_rfo.html', rfo=dict(rfo))


@disciplinar_bp.route('/imprimir_rfo/<int:ocorrencia_id>')
@admin_secundario_required
def imprimir_rfo(ocorrencia_id):
    db = get_db()

    rfo = db.execute('''
        SELECT
            o.*, a.matricula, a.nome AS nome_aluno, a.serie, a.turma,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            u.username AS responsavel_registro_username
        FROM ocorrencias o
        JOIN alunos a ON o.aluno_id = a.id
        JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        LEFT JOIN usuarios u ON o.responsavel_registro_id = u.id
        WHERE o.id = ?
    ''', (ocorrencia_id,)).fetchone()

    if rfo is None:
        flash('RFO n�o encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    return render_template('formularios/rfo_impressao.html', rfo=dict(rfo))

@disciplinar_bp.route('/export_prontuario/<int:ocorrencia_id>')
@admin_secundario_required
def export_prontuario_pdf(ocorrencia_id):
    db = get_db()

    # Reutiliza a mesma consulta usada em visualizar_rfo/imprimir_rfo para obter dados
    rfo = db.execute('''
        SELECT
            o.*,
            GROUP_CONCAT(a.nome, '; ') AS alunos,
            GROUP_CONCAT(a.serie || ' - ' || a.turma, '; ') AS series_turmas,
            a.matricula, a.nome AS nome_aluno, a.serie, a.turma,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            u.username AS responsavel_registro_username
        FROM ocorrencias o
        LEFT JOIN ocorrencias_alunos oa ON oa.ocorrencia_id = o.id
        LEFT JOIN alunos a ON a.id = oa.aluno_id
        LEFT JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        LEFT JOIN usuarios u ON o.responsavel_registro_id = u.id
        WHERE o.id = ?
        GROUP BY o.id
    ''', (ocorrencia_id,)).fetchone()

    if rfo is None:
        flash('RFO n�o encontrado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    rfo_dict = dict(rfo)

    # Renderizamos um template espec�fico para o PDF (criaremos o template depois).
    # Use, por exemplo, templates/disciplinar/prontuario_pdf.html
    html = render_template('disciplinar/prontuario_pdf.html', rfo=rfo_dict)

    # Detecta wkhtmltopdf (procura no PATH, sen�o usa o local padr�o do Windows)
    wk_path = shutil.which('wkhtmltopdf')
    if not wk_path:
        wk_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

    if not os.path.isfile(wk_path):
        abort(500, description=f"wkhtmltopdf n�o encontrado em: {wk_path}")

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

    # Monta nome seguro do arquivo
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

    ocorrencias = db.execute('''
        SELECT
            o.id, o.rfo_id, o.data_ocorrencia, o.status, o.data_tratamento,
            o.tipo_falta, o.medida_aplicada, o.relato_observador,
            o.aluno_id, a.matricula, a.nome AS nome_aluno,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            o.relato_estudante, o.despacho_gestor, o.data_despacho,
            o.reincidencia
        FROM ocorrencias o
        JOIN alunos a ON o.aluno_id = a.id
        JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        WHERE o.status = 'TRATADO'
        ORDER BY o.data_tratamento DESC
    ''').fetchall()

    ocorrencias_list = [dict(o) for o in ocorrencias]
    return render_template('disciplinar/listar_ocorrencias.html', ocorrencias=ocorrencias_list)

# Substitua a fun��o tratar_rfo existente por este bloco completo.
@disciplinar_bp.route('/tratar_rfo/<int:ocorrencia_id>', methods=['GET', 'POST'])
@admin_secundario_required
def tratar_rfo(ocorrencia_id):
    db = get_db()

    ocorrencia = db.execute('''
        SELECT
            o.*, a.matricula, a.nome AS nome_aluno, a.serie, a.turma,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            u.username AS responsavel_registro_username
        FROM ocorrencias o
        JOIN alunos a ON o.aluno_id = a.id
        JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        LEFT JOIN usuarios u ON o.responsavel_registro_id = u.id
        WHERE o.id = ? AND o.status = 'AGUARDANDO TRATAMENTO'
    ''', (ocorrencia_id,)).fetchone()

    if ocorrencia is None:
        flash('RFO n�o encontrado ou j� tratado.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_rfo'))

    ocorrencia_dict = dict(ocorrencia)
    
    # ---------- NOVO: montar lista completa de alunos associados � ocorrencia ----------
    alunos_rows = db.execute('''
        SELECT al.matricula, al.nome, al.serie, al.turma
        FROM ocorrencias_alunos oa
        LEFT JOIN alunos al ON al.id = oa.aluno_id
        WHERE oa.ocorrencia_id = ?
        ORDER BY oa.id
    ''', (ocorrencia_id,)).fetchall()

    alunos_list = []
    series_list = []
    nomes_list = []
    for ar in alunos_rows:
        nome = ar.get('nome') if isinstance(ar, dict) else ar['nome']
        matricula = ar.get('matricula') if isinstance(ar, dict) else ar['matricula']
        serie = ar.get('serie') if isinstance(ar, dict) else ar['serie']
        turma = ar.get('turma') if isinstance(ar, dict) else ar['turma']
        alunos_list.append({
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

    # manter compatibilidade com o que as outras views/templates esperam
    ocorrencia_dict['alunos_list'] = alunos_list
    ocorrencia_dict['alunos'] = '; '.join([n for n in nomes_list if n]) if any(nomes_list) else ocorrencia_dict.get('alunos') or ocorrencia_dict.get('nome_aluno') or ''
    if series_list:
        ocorrencia_dict['series_turmas'] = '; '.join(series_list)
    else:
        ocorrencia_dict['series_turmas'] = ocorrencia_dict.get('series_turmas') or ((ocorrencia_dict.get('serie') and ocorrencia_dict.get('turma')) and f"{ocorrencia_dict.get('serie')} - {ocorrencia_dict.get('turma')}" or '')

    # -------------------------------------------------------------------------------

    tipos_falta = TIPO_FALTA_MAP
    medidas_map = MEDIDAS_MAP

    if request.method == 'POST':
        # (mantive todo o fluxo POST como estava; s� adaptado para usar ocorrencia_dict ap�s)
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
        reincidencia = request.form.get('reincidencia')
        try:
            reincidencia = int(reincidencia) if reincidencia is not None and reincidencia != '' else None
        except Exception:
            reincidencia = None

        relato_estudante = request.form.get('relato_estudante', '').strip()
        despacho_gestor = request.form.get('despacho_gestor', '').strip()
        data_despacho = request.form.get('data_despacho', '').strip()

        circ_at = request.form.get('circunstancias_atenuantes', '').strip() or 'N�o h�'
        circ_ag = request.form.get('circunstancias_agravantes', '').strip() or 'N�o h�'

        # --- IN�CIO: detectar se este tratamento refere-se a um ELOGIO ---
        tratamento_classificacao = request.form.get('tratamento_classificacao', '').strip() or ''
        tipo_rfo_post = request.form.get('tipo_rfo', '').strip() or ''
        oc_tipo = ocorrencia_dict.get('tipo_rfo') or ocorrencia_dict.get('tipo_ocorrencia_nome') or ''

        # tamb�m aceitar sinaliza��o direta enviada no POST (is_elogio)
        is_elogio_form = request.form.get('is_elogio')
        is_elogio_from_form = str(is_elogio_form).strip().lower() in ('1', 'true', 'on')

        # is_elogio ser� True se qualquer uma das fontes indicar "elogio" ou se o form sinalizou
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

        # Se for elogio, limpar campos de falta (n�o se aplicam) para evitar valida��o desnecess�ria
        if is_elogio:
            tipos_csv = ''
            falta_ids_list = []
            falta_ids_csv = ''
            # tentar inferir medida_aplicada a partir de classifica��es/tipo (caso frontend n�o tenha enviado)
            if not medida_aplicada:
                medida_aplicada = (tratamento_classificacao or tipo_rfo_post or oc_tipo or '').strip()
        # --- FIM: detec��o de ELOGIO ---
        error = None
        # somente exigir campos de falta/medida quando N�O for elogio
        if not is_elogio:
            if not tipos_csv:
                error = 'Tipo de falta � obrigat�rio.'
            elif not falta_ids_list:
                error = 'A descri��o da falta � obrigat�ria.'
            elif not medida_aplicada:
                error = 'A medida aplicada � obrigat�ria.'

        # checagens comuns (reincid�ncia, despacho) v�lidas para ambos os casos
        if error is None:
            if reincidencia not in [0, 1]:
                error = 'Reincid�ncia deve ser "Sim" ou "N�o".'
            elif not despacho_gestor:
                error = 'O despacho do gestor � obrigat�rio.'
            elif not data_despacho:
                error = 'A data do despacho � obrigat�ria.'

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

                cols = _get_table_columns(db, 'ocorrencias')
                update_cols = [
                    "status = 'TRATADO'",
                    "data_tratamento = ?",
                    "tipo_falta = ?",
                    "falta_disciplinar_id = ?",
                    "medida_aplicada = ?",
                    "reincidencia = ?",
                    "relato_estudante = ?",
                    "despacho_gestor = ?",
                    "data_despacho = ?"
                ]
                params = [
                    data_trat,
                    tipos_csv,
                    primeiro_falta_id,
                    medida_aplicada,
                    reincidencia,
                    relato_estudante,
                    despacho_gestor,
                    data_despacho
                ]

                if 'circunstancias_atenuantes' in cols:
                    update_cols.append("circunstancias_atenuantes = ?")
                    params.append(circ_at)
                if 'circunstancias_agravantes' in cols:
                    update_cols.append("circunstancias_agravantes = ?")
                    params.append(circ_ag)

                update_sql = f"UPDATE ocorrencias SET {', '.join(update_cols)} WHERE id = ?"
                params.append(ocorrencia_id)

                db.execute(update_sql, tuple(params))

                falta_ids_ints = []
                for fid in falta_ids_list:
                    try:
                        falta_ids_ints.append(int(fid))
                    except Exception:
                        pass

                salvar_faltas_relacionadas(db, ocorrencia_id, falta_ids_ints)

                # --- INTEGRA��O: calcular delta e aplicar pontua��o ---
                try:
                    # Aplicar pontua��o apenas quando houver uma medida v�lida (pode ocorrer em elogios)
                    if medida_aplicada:
                        try:
                            config = _get_config_values(db)
                            qtd_form = request.form.get('sim_qtd') or request.form.get('dias') or request.form.get('quantidade') or 1
                            delta = _calcular_delta_por_medida(medida_aplicada, qtd_form, config)
                            # manter comportamento anterior: usa ocorrencia['aluno_id'] (se existir)
                            _apply_delta_pontuacao(db, ocorrencia.get('aluno_id'), data_trat, delta, ocorrencia_id, medida_aplicada)
                        except Exception:
                            # falha no c�lculo de pontua��o n�o deve abortar o tratamento; registrar erro em log
                            current_app.logger.exception("Erro ao aplicar delta de pontua��o")
                    else:
                        # sem medida_aplicada � n�o h� base para pontuar; registrar aviso (�til para auditoria)
                        current_app.logger.warning(
                            "Tratamento salvo sem aplicar pontua��o: ocorrencia_id=%s, medida_aplicada ausente (poss�vel elogio sem medida)",
                            ocorrencia_id
                        )

                    try:
                        if isinstance(ocorrencia, dict):
                            rfo_id = ocorrencia.get('rfo_id')
                            aluno_id_local = ocorrencia.get('aluno_id')
                            responsavel_id = ocorrencia.get('responsavel_registro_id') or ocorrencia.get('observador_id')
                        else:
                            try:
                                rfo_id = ocorrencia['rfo_id']
                            except Exception:
                                rfo_id = None
                            try:
                                aluno_id_local = ocorrencia['aluno_id']
                            except Exception:
                                aluno_id_local = None
                            try:
                                responsavel_id = ocorrencia['responsavel_registro_id']
                            except Exception:
                                responsavel_id = None
                            if not responsavel_id:
                                try:
                                    responsavel_id = ocorrencia['observador_id']
                                except Exception:
                                    responsavel_id = None

                        responsavel_id = int(responsavel_id) if responsavel_id is not None else 0
                        tipo_falta_val = tipos_csv if 'tipos_csv' in locals() else (medida_aplicada or '')
                        falta_ids_val = falta_ids_csv if 'falta_ids_csv' in locals() else ''
                        tipo_falta_list_val = tipos_csv if 'tipos_csv' in locals() else ''

                        if rfo_id:
                            existing = db.execute('SELECT id FROM ficha_medida_disciplinar WHERE rfo_id = ?', (rfo_id,)).fetchone()
                            if existing:
                                # NOTE: delta pode n�o existir se n�o houve medida_aplicada; usar 0.0 por seguran�a
                                db.execute('UPDATE ficha_medida_disciplinar SET pontos_aplicados = ? WHERE rfo_id = ?', (float(delta) if 'delta' in locals() else 0.0, rfo_id))
                            else:
                                seq, seq_ano = _next_fmd_sequence(db)
                                fmd_id = f"FMD-{seq:04d}/{seq_ano}"
                                data_fmd = datetime.now().strftime('%Y-%m-%d')
                                db.execute(
                                    'INSERT INTO ficha_medida_disciplinar (fmd_id, aluno_id, rfo_id, data_fmd, tipo_falta, medida_aplicada, descricao_falta, observacoes, responsavel_id, data_registro, falta_disciplinar_ids, tipo_falta_list, pontos_aplicados) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                    (fmd_id, aluno_id_local, rfo_id, data_fmd, tipo_falta_val, medida_aplicada, '', '', responsavel_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), falta_ids_val, tipo_falta_list_val, float(delta) if 'delta' in locals() else 0.0)
                                )
                    except Exception:
                        current_app.logger.exception('Erro ao gravar pontos_aplicados em ficha_medida_disciplinar')

                    try:
                        if ocorrencia_id:
                            db.execute('UPDATE ocorrencias SET pontos_aplicados = ? WHERE id = ?', (float(delta) if 'delta' in locals() else 0.0, ocorrencia_id))
                    except Exception:
                        current_app.logger.exception('Erro ao gravar pontos_aplicados em ocorrencias')

                except Exception:
                    current_app.logger.exception('Erro ao aplicar atualiza��o de pontuacao')

                # dentro da fun��o que trata o RFO, antes de db.commit()
                # (apenas inserir estas linhas)
                try:
                    # integrar RFO ao prontu�rio do aluno (evita duplica��o)
                    ok, msg = create_or_append_prontuario_por_rfo(db, ocorrencia_id, session.get('username'))
                    if not ok:
                        # msg pode indicar "j� integrado" ou erro; n�o abortamos o tratamento por isso
                        current_app.logger.debug('create_or_append_prontuario_por_rfo: ' + str(msg))
                except Exception:
                    current_app.logger.exception('Erro ao integrar RFO ao prontu�rio (tarefa auxiliar)')

                db.commit()
                flash(f'RFO {ocorrencia_dict["rfo_id"]} tratado com sucesso.', 'success')
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
        associado = 'Sim' if associado else 'N�o'
    material_info = tipo
    if associado:
        material_info = f"{tipo} � {associado}"
    ocorrencia_dict['material_recolhido_info'] = material_info

    return render_template('disciplinar/tratar_rfo.html',
                           ocorrencia=ocorrencia_dict,
                           tipos_falta=tipos_falta,
                           medidas_map=medidas_map,
                           request_form=request.form if request.method == 'POST' else None)

@disciplinar_bp.route('/editar_ocorrencia/<int:ocorrencia_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_ocorrencia(ocorrencia_id):
    db = get_db()
    ocorrencia = db.execute('''
        SELECT
            o.*, a.matricula, a.nome AS nome_aluno,
            tipo_oc.nome AS tipo_ocorrencia_nome
        FROM ocorrencias o
        JOIN alunos a ON o.aluno_id = a.id
        JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        WHERE o.id = ? AND o.status = 'TRATADO'
    ''', (ocorrencia_id,)).fetchone()

    if ocorrencia is None:
        flash('Ocorr�ncia n�o encontrada ou ainda n�o foi tratada.', 'danger')
        return redirect(url_for('disciplinar_bp.listar_ocorrencias'))

    ocorrencia_dict = dict(ocorrencia)

    if request.method == 'POST':
        tipo_falta = request.form.get('tipo_falta', '').strip()
        medida_aplicada = request.form.get('medida_aplicada', '').strip()
        relato_observador = request.form.get('relato_observador', '').strip()
        advertencia_oral = request.form.get('advertencia_oral', '').strip()
        error = None

        if not tipo_falta:
            error = 'Tipo de falta � obrigat�rio.'
        elif not medida_aplicada:
            error = 'A medida aplicada � obrigat�ria.'
        elif not advertencia_oral or advertencia_oral not in ['sim', 'nao']:
            error = 'Selecione se a ocorr�ncia deve ser considerada como Advert�ncia Oral.'

        if error is not None:
            flash(error, 'danger')
        else:
            try:
                db.execute('''
                    UPDATE ocorrencias
                    SET
                        tipo_falta = ?,
                        medida_aplicada = ?,
                        relato_observador = ?,
                        advertencia_oral = ?
                    WHERE id = ?
                ''', (
                    tipo_falta,
                    medida_aplicada,
                    relato_observador,
                    advertencia_oral,
                    ocorrencia_id
                ))
                db.commit()
                flash(f'Ocorr�ncia {ocorrencia_dict["rfo_id"]} editada com sucesso.', 'success')
                return redirect(url_for('disciplinar_bp.listar_ocorrencias'))
            except Exception as e:
                db.rollback()
                flash(f'Erro ao editar ocorr�ncia: {e}', 'danger')

    tipos_ocorrencia_db = get_tipos_ocorrencia()
    return render_template('disciplinar/adicionar_ocorrencia.html',
                            ocorrencia=ocorrencia_dict,
                            tipos_ocorrencia=tipos_ocorrencia_db,
                            tipos_falta=TIPO_FALTA_MAP,
                            medidas_map=MEDIDAS_MAP,
                            request_form=request.form)


@disciplinar_bp.route('/excluir_ocorrencia/<int:ocorrencia_id>', methods=['POST'])
@admin_required
def excluir_ocorrencia(ocorrencia_id):
    db = get_db()

    try:
        rfo = db.execute('SELECT rfo_id FROM ocorrencias WHERE id = ?', (ocorrencia_id,)).fetchone()

        if rfo is None:
            flash('Ocorr�ncia/RFO n�o encontrado.', 'danger')
            return redirect(url_for('disciplinar_bp.listar_ocorrencias'))

        rfo_id_nome = rfo['rfo_id']

        db.execute('DELETE FROM ocorrencias WHERE id = ?', (ocorrencia_id,))
        db.commit()

        flash(f'Oorr�ncia/RFO {rfo_id_nome} exclu�do com sucesso.', 'success')

    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir ocorr�ncia/RFO: {e}', 'danger')

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
        atenuantes = request.form.get('circunstancias_atenuantes', '').strip() or 'N�o h�'
        agravantes = request.form.get('circunstancias_agravantes', '').strip() or 'N�o h�'
        gestor_id = request.form.get('gestor_id') or session.get('user_id')

        error = None
        if not aluno_id:
            error = 'Aluno � obrigat�rio.'
        elif not data_fmd:
            error = 'Data � obrigat�ria.'
        elif not tipo_falta_csv:
            error = 'Tipo de falta � obrigat�rio.'
        elif not medida_aplicada:
            error = 'Medida aplicada � obrigat�ria.'

        if error:
            flash(error, 'danger')
        else:
            try:
                fmd_id_final = get_proximo_fmd_id(incrementar=True)

                db.execute('''
                    INSERT INTO ficha_medida_disciplinar
                    (fmd_id, aluno_id, rfo_id, data_fmd, tipo_falta, medida_aplicada,
                     descricao_falta, observacoes, responsavel_id, status,
                     data_falta, relato_faltas, itens_faltas_ids,
                     comportamento_id, pontuacao_id, comparecimento_responsavel,
                     prazo_comparecimento, atenuantes, agravantes, gestor_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATIVA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fmd_id_final,
                    int(aluno_id) if aluno_id and str(aluno_id).isdigit() else None,
                    None,  # rfo_id (opcional)
                    data_fmd,
                    tipo_falta_csv,
                    medida_aplicada,
                    descricao_falta if descricao_falta else None,
                    None,  # observacoes (opcional)
                    session.get('user_id'),
                    # novos campos
                    request.form.get('data_falta') or None,
                    relato_faltas or None,
                    ','.join(falta_ids_list) if falta_ids_list else None,
                    int(comportamento_id) if comportamento_id and str(comportamento_id).isdigit() else None,
                    int(pontuacao_id) if pontuacao_id and str(pontuacao_id).isdigit() else None,
                    comparecimento_val,
                    prazo_comparecimento if prazo_comparecimento else None,
                    atenuantes,
                    agravantes,
                    int(gestor_id) if gestor_id and str(gestor_id).isdigit() else session.get('user_id')
                ))

                db.commit()
                flash(f'FMD {fmd_id_final} registrada com sucesso!', 'success')
                return redirect(url_for('visualizacoes_bp.listar_fmds'))
            except sqlite3.Error as e:
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
    fmd = db.execute('''
        SELECT f.*, a.matricula, a.nome AS nome_aluno, a.serie, a.turma
        FROM ficha_medida_disciplinar f
        JOIN alunos a ON f.aluno_id = a.id
        WHERE f.id = ?
    ''', (fmd_id,)).fetchone()

    if fmd is None:
        flash('FMD n�o encontrada.', 'danger')
        return redirect(url_for('visualizacoes_bp.listar_fmds'))

    faltas = get_faltas_disciplinares()

    if request.method == 'POST':
        data_fmd = request.form.get('data_fmd')
        tipo_falta = request.form.get('tipo_falta', '').strip()
        medida_aplicada = request.form.get('medida_aplicada', '').strip()
        descricao_falta = request.form.get('descricao_falta', '').strip()
        observacoes = request.form.get('observacoes', '').strip()
        status = request.form.get('status')

        error = None
        if not data_fmd:
            error = 'Data da FMD � obrigat�ria.'
        elif not tipo_falta:
            error = 'Tipo de falta � obrigat�rio.'
        elif not medida_aplicada:
            error = 'Medida aplicada � obrigat�ria.'
        elif not status:
            error = 'Status � obrigat�rio.'

        if error is None:
            try:
                db.execute('''
                    UPDATE ficha_medida_disciplinar
                    SET data_fmd = ?, tipo_falta = ?, medida_aplicada = ?,
                        descricao_falta = ?, observacoes = ?, status = ?
                    WHERE id = ?
                ''', (data_fmd, tipo_falta, medida_aplicada, descricao_falta,
                      observacoes, status, fmd_id))

                db.commit()
                flash(f'FMD {fmd["fmd_id"]} atualizada com sucesso!', 'success')
                return redirect(url_for('visualizacoes_bp.listar_fmds'))
            except sqlite3.Error as e:
                db.rollback()
                flash(f'Erro ao atualizar FMD: {e}', 'danger')
        else:
            flash(error, 'danger')

    return render_template('disciplinar/editar_fmd.html',
                         fmd=dict(fmd),
                         faltas=faltas,
                         medidas_map=MEDIDAS_MAP)


@disciplinar_bp.route('/excluir_fmd/<int:fmd_id>', methods=['POST'])
@admin_required
def excluir_fmd(fmd_id):
    db = get_db()

    try:
        fmd = db.execute('SELECT fmd_id FROM ficha_medida_disciplinar WHERE id = ?', (fmd_id,)).fetchone()

        if fmd is None:
            flash('FMD n�o encontrada.', 'danger')
            return redirect(url_for('visualizacoes_bp.listar_fmds'))

        fmd_id_nome = fmd['fmd_id']

        db.execute('DELETE FROM ficha_medida_disciplinar WHERE id = ?', (fmd_id,))
        db.commit()

        flash(f'FMD {fmd_id_nome} exclu�da com sucesso.', 'success')
    except sqlite3.Error as e:
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
            placeholders = ','.join('?' for _ in ids)
            sql = f'''
                SELECT DISTINCT id, descricao
                FROM faltas_disciplinares
                WHERE id IN ({placeholders})
                ORDER BY descricao
                LIMIT 50
            '''
            rows = db.execute(sql, tuple(ids)).fetchall()
        else:
            q_like = f'%{q}%'
            rows = db.execute('''
                SELECT DISTINCT id, descricao
                FROM faltas_disciplinares
                WHERE descricao LIKE ? COLLATE NOCASE
                ORDER BY descricao
                LIMIT 50
            ''', (q_like,)).fetchall()

        result = []
        seen = set()
        for r in rows:
            rid = int(r['id'])
            if rid in seen:
                continue
            seen.add(rid)
            result.append({'id': rid, 'descricao': r['descricao']})
        return jsonify(result)
    except sqlite3.Error:
        return jsonify([])


@disciplinar_bp.route('/api/comportamentos_busca')
def api_comportamentos_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        rows = db.execute('''
            SELECT DISTINCT id, nome
            FROM comportamentos
            WHERE nome LIKE ? COLLATE NOCASE
            ORDER BY nome
            LIMIT 50
        ''', (q_like,)).fetchall()
    except sqlite3.Error:
        return jsonify([])
    result = [{'id': r['id'], 'nome': r['nome']} for r in rows]
    return jsonify(result)


@disciplinar_bp.route('/api/pontuacoes_busca')
def api_pontuacoes_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        rows = db.execute('''
            SELECT DISTINCT id, descricao
            FROM pontuacoes
            WHERE descricao LIKE ? COLLATE NOCASE
            ORDER BY descricao
            LIMIT 50
        ''', (q_like,)).fetchall()
    except sqlite3.Error:
        return jsonify([])
    result = [{'id': r['id'], 'descricao': r['descricao']} for r in rows]
    return jsonify(result)


@disciplinar_bp.route('/api/usuarios_busca')
def api_usuarios_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        rows = db.execute('''
            SELECT id, username, COALESCE(full_name, '') AS full_name
            FROM usuarios
            WHERE username LIKE ? OR full_name LIKE ?
            ORDER BY username
            LIMIT 50
        ''', (q_like, q_like)).fetchall()
    except sqlite3.Error:
        return jsonify([])
    result = [{'id': r['id'], 'username': r['username'], 'full_name': r['full_name']} for r in rows]
    return jsonify(result)

from flask import render_template

@disciplinar_bp.route('/fmd_teste_novo')
def fmd_teste_novo():
    # Simula��o de dados
    aluno = {
        'nome': 'FULANO DE TAL',
        'serie': '7�',
        'turma': 'B'
    }
    fmd = {
        'fmd_id': 'FMD-0001/2026',
        'pontos_aplicados': -2.0,
        'comportamento': 'Descumprimento das normas',
        'medida_aplicada': 'Advert�ncia Escrita',
        'agravantes': 'Reincid�ncia',
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
        'secretaria': 'Secretaria Municipal de Educa��o',
        'coordenacao': 'Coordena��o Pedag�gica',
        'estado': 'Estado do Exemplo',
    }
    usuario = {
        'nome': 'M�RIO RESPONS�VEL',
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

@disciplinar_bp.route('/fmd_novo_real/<path:fmd_id>')
def fmd_novo_real(fmd_id):
    from flask import session
    import sqlite3
    db = g.db if hasattr(g, 'db') else sqlite3.connect('escola.db')
    db.row_factory = sqlite3.Row

    # ==== 1. PEGA O USU�RIO LOGADO NA SESS�O ====
    user_id = session.get('user_id')
    usuario_sessao = None
    if user_id:
        usuario_sessao = db.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    print('[FMD] Usu�rio ativo:', dict(usuario_sessao) if usuario_sessao else None)
    if not usuario_sessao or usuario_sessao['nivel'] not in [1, 2]:
        return "Voc� n�o tem permiss�o para acessar este documento.", 403

    # ==== 2. Busca a FMD ====
    fmd = db.execute("SELECT * FROM ficha_medida_disciplinar WHERE fmd_id = ?", (fmd_id,)).fetchone()
    if not fmd:
        return 'FMD n�o encontrada', 404

    # ==== 3. Busca o aluno relacionado ====
    aluno = db.execute("SELECT * FROM alunos WHERE id = ?", (fmd['aluno_id'],)).fetchone() or {}
    from escola.models import get_aluno_estado_atual

    estado = {}
    comportamento = None
    pontuacao = None
    if aluno and 'id' in aluno.keys():
        estado = get_aluno_estado_atual(aluno['id']) or {}
        comportamento = estado.get('comportamento')
        pontuacao = estado.get('pontuacao')

    # ==== 4. Busca ocorr�ncia relacionada (RFO) ====
    rfo = db.execute("SELECT * FROM ocorrencias WHERE rfo_id = ?", (fmd['rfo_id'],)).fetchone() or {}
    item_descricoes_faltas = []

    ids_faltas = []
    if 'falta_disciplinar_id' in rfo.keys() and rfo['falta_disciplinar_id']:
        ids_faltas.append(str(rfo['falta_disciplinar_id']))
    elif 'falta_ids_csv' in rfo.keys() and rfo['falta_ids_csv']:
        ids_faltas = [id.strip() for id in str(rfo['falta_ids_csv']).split(',') if id.strip()]

    for falta_id in ids_faltas:
        res = db.execute(
            "SELECT id, descricao FROM faltas_disciplinares WHERE id = ?", 
            (falta_id,)
        ).fetchone()
        if res:
            item_descricoes_faltas.append(f"{res[0]} - {res[1]}")

    if item_descricoes_faltas:
        item_descricao_falta = "<br>".join(item_descricoes_faltas)
    else:
        item_descricao_falta = "-"
    print("RFO ->", dict(rfo))
    print("RFO TODOS OS CAMPOS:", list(rfo.keys()))

    itens_especificacao = (
        rfo['item_descricao'] if 'item_descricao' in rfo.keys() and rfo['item_descricao'] else
        rfo['descricao_item'] if 'descricao_item' in rfo.keys() and rfo['descricao_item'] else
        rfo['descricao'] if 'descricao' in rfo.keys() and rfo['descricao'] else
        rfo['falta_descricao'] if 'falta_descricao' in rfo.keys() and rfo['falta_descricao'] else
        '-'
    )

    # ==== 5. Cabe�alho institucional ====
    cabecalho = db.execute("SELECT * FROM cabecalhos LIMIT 1;").fetchone() or {}

    escola = {
        'estado': cabecalho['estado'],
        'secretaria': cabecalho['secretaria'],
        'coordenacao': cabecalho['coordenacao'],
        'nome': cabecalho['escola'],
        'logotipo_url': '/static/uploads/cabecalhos/' + cabecalho['logo_escola'] if ('logo_escola' in cabecalho.keys() and cabecalho['logo_escola']) else ''
    }

    # Ajuste para futuro campo correto de envio de e-mail
    envio = {
        'data_hora': fmd['email_enviado_data'] if 'email_enviado_data' in fmd.keys() and fmd['email_enviado_data'] else None,
        'email_destinatario': fmd['email_enviado_para'] if 'email_enviado_para' in fmd.keys() and fmd['email_enviado_para'] else None,
    }

    # ==== 6. Busca gestor/respons�vel para carimbo/assinatura ====
    usuario_id_registro = fmd['gestor_id'] or fmd['responsavel_id']
    usuario_registro = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id_registro,)).fetchone() or {}
    print("USUARIO REGISTRO -->", dict(usuario_registro) if usuario_registro else "NENHUM")

    atenuantes = fmd['atenuantes'] or (rfo['circunstancias_atenuantes'] if rfo and 'circunstancias_atenuantes' in rfo.keys() else '')
    agravantes = fmd['agravantes'] or (rfo['circunstancias_agravantes'] if rfo and 'circunstancias_agravantes' in rfo.keys() else '')

    nome_usuario = usuario_sessao['username'] if usuario_sessao and 'username' in usuario_sessao.keys() else '-'
    cargo_usuario = usuario_sessao['cargo'] if usuario_sessao and 'cargo' in usuario_sessao.keys() else '-'

    contexto = {
        'escola': escola,
        'aluno': aluno,
        'fmd': fmd,
        'rfo': rfo,
        'nome_usuario': nome_usuario,
        'cargo_usuario': cargo_usuario,
        'envio': envio,
        'atenuantes': atenuantes,
        'agravantes': agravantes,
        'comportamento': comportamento,
        'pontuacao': pontuacao,
        'itens_especificacao': item_descricao_falta,
    }

    if request.args.get('salvar_pdf') == '1':
        import pdfkit, os
        from urllib.parse import quote

        # AJUSTE: monta o caminho absoluto do logo do PDF
        logo_relativo = contexto.get('escola', {}).get('logotipo_url', '')
        if logo_relativo:
            logo_relativo = logo_relativo.lstrip("/")
            caminho_absoluto = os.path.join(
                r"C:\Users\Usu�rio\Documents\GitHub\escolar\escola", logo_relativo
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
    import sqlite3
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import os
    from email.mime.application import MIMEApplication

    db = g.db if hasattr(g, 'db') else sqlite3.connect('escola.db')
    db.row_factory = sqlite3.Row

    # Busca os dados da FMD
    fmd = db.execute("SELECT * FROM ficha_medida_disciplinar WHERE fmd_id = ?", (fmd_id,)).fetchone()
    if not fmd:
        flash('FMD n�o encontrada!', 'alert-danger')
        return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

    # Busca o aluno e seu e-mail
    aluno = db.execute("SELECT * FROM alunos WHERE id = ?", (fmd['aluno_id'],)).fetchone()
    email_destinatario = aluno['email'] if aluno and 'email' in aluno.keys() and aluno['email'] else None

    # SE N�O existir e-mail cadastrado, retorna erro e n�o envia
    if not email_destinatario:
        flash('N�o existe e-mail cadastrado para este aluno.', 'alert-danger')
        return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

    # Busca o e-mail e a senha de app da escola
    dados_escola = db.execute("SELECT email_remetente, senha_email_app, telefone FROM dados_escola LIMIT 1").fetchone()
    if not dados_escola or not dados_escola['email_remetente'] or not dados_escola['senha_email_app']:
        flash('N�o h� e-mail institucional e/ou senha de aplicativo cadastrados para a escola.', 'danger')
        return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))
    email_remetente = dados_escola['email_remetente']
    senha_email_app = dados_escola['senha_email_app']

    # MONTE AQUI O CORPO DO E-MAIL (exemplo simples abaixo)
    assunto = "Ficha de Medida Disciplinar"

    # Fun��o utilit�ria para pegar campo ou retorno vazio
    def get_fmd_field(row, key):
        try:
            return row[key]
        except Exception:
            return ''

    # Pegue o telefone em Python ANTES da string do e-mail
    telefone_escola = dados_escola['telefone'] if 'telefone' in dados_escola.keys() else ''

    corpo_html = f"""
    <html>
    <body>
        <p>Prezado respons�vel,<br>
        Segue a Ficha de Medida Disciplinar referente ao(a) aluno(a): <b>{aluno['nome']}</b>.
        <br><br>
        Tipo de falta: <b>{get_fmd_field(fmd,'tipo_falta')}</b><br>
        Medida aplicada: <b>{get_fmd_field(fmd,'medida_aplicada')}</b><br>
        {"Descri��o: <b>{}</b><br>".format(get_fmd_field(fmd,'descricao_detalhada')) if get_fmd_field(fmd,'descricao_detalhada') else ""}
        Status: <b>{get_fmd_field(fmd,'status')}</b><br>
        <br>
        <i>Favor entrar em contato com a escola caso necess�rio. Telefone: <b>{telefone_escola}</b></i>
        </p>
    </body>
    </html>
    """

    # ========== ENVIO REAL DO E-MAIL ==========
    try:
        temp_dir = "tmp"
        safe_fmd_id = str(fmd_id).replace('/', '_')
        pdf_path = os.path.join(temp_dir, f"fmd_{safe_fmd_id}.pdf")
        if not os.path.exists(pdf_path):
            flash("O PDF da FMD ainda n�o foi gerado! Gere a FMD antes de enviar o e-mail.", "danger")
            return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))

        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = email_destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html'))

        # ----- ANEXO PDF -----
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
            msg.attach(part)
        # ---------------------
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_remetente, senha_email_app)
        server.sendmail(email_remetente, email_destinatario, msg.as_string())
        server.quit()

        data_envio = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        db.execute("UPDATE ficha_medida_disciplinar SET email_enviado_data=?, email_enviado_para=? WHERE fmd_id=?",
                   (data_envio, email_destinatario, fmd_id))
        db.commit()
        flash("FMD enviada por e-mail com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao enviar o e-mail: {e}", "danger")

    return redirect(url_for('disciplinar_bp.fmd_novo_real', fmd_id=fmd_id))
