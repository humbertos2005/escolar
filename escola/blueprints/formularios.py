from flask import Blueprint, render_template, request, make_response, jsonify, current_app
from escola.database import get_db
from .utils import login_required, admin_secundario_required
from datetime import datetime

formularios_bp = Blueprint('formularios_bp', __name__)

@formularios_bp.route('/tabela_disciplinar')
@admin_secundario_required
def tabela_disciplinar():
    """Exibe a tabela disciplinar com todas as faltas e medidas."""
    db = get_db()
    faltas = db.execute('''
        SELECT id, natureza, descricao 
        FROM faltas_disciplinares 
        ORDER BY 
            CASE natureza 
                WHEN 'LEVE' THEN 1 
                WHEN 'MÉDIA' THEN 2 
                WHEN 'GRAVE' THEN 3 
                WHEN 'GRAVÍSSIMA' THEN 4 
                ELSE 5 
            END,
            descricao
    ''').fetchall()
    
    return render_template('formularios/tabela_disciplinar.html', faltas=faltas)

@formularios_bp.route('/rfo/<int:ocorrencia_id>')
@admin_secundario_required
def formulario_rfo(ocorrencia_id):
    """Gera o formulário RFO imprimível."""
    db = get_db()
    
    rfo = db.execute('''
        SELECT
            o.*, 
            a.matricula, a.nome AS nome_aluno, a.serie, a.turma,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            u.username AS responsavel_registro_username
        FROM ocorrencias o
        JOIN alunos a ON o.aluno_id = a.id
        JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        LEFT JOIN usuarios u ON o.responsavel_registro_id = u.id
        WHERE o.id = ?
    ''', (ocorrencia_id,)).fetchone()
    
    if rfo is None:
        return "RFO não encontrado", 404
    
    return render_template('formularios/rfo.html', rfo=dict(rfo))

@formularios_bp.route('/fmd/<int:fmd_id>')
@admin_secundario_required
def formulario_fmd(fmd_id):
    """Gera o formulário FMD imprimível."""
    db = get_db()
    
    fmd = db.execute('''
        SELECT
            f.*, 
            a.matricula, a.nome AS nome_aluno, a.serie, a.turma,
            u.username AS responsavel_username
        FROM ficha_medida_disciplinar f
        JOIN alunos a ON f.aluno_id = a.id
        LEFT JOIN usuarios u ON f.responsavel_id = u.id
        WHERE f.id = ?
    ''', (fmd_id,)).fetchone()
    
    if fmd is None:
        return "FMD não encontrada", 404
    
    return render_template('formularios/fmd.html', fmd=dict(fmd))

@formularios_bp.route('/prontuario/<int:aluno_id>')
@admin_secundario_required
def prontuario(aluno_id):
    """Gera o prontuário completo do aluno."""
    db = get_db()
    
    aluno = db.execute('SELECT * FROM alunos WHERE id = ?', (aluno_id,)).fetchone()
    if aluno is None:
        return "Aluno não encontrado", 404
    
    rfos = db.execute('''
        SELECT
            o.rfo_id, o.data_ocorrencia, o.status,
            tipo_oc.nome AS tipo_ocorrencia_nome,
            o.tipo_falta, o.medida_aplicada
        FROM ocorrencias o
        LEFT JOIN tipos_ocorrencia tipo_oc ON o.tipo_ocorrencia_id = tipo_oc.id
        WHERE o.aluno_id = ?
        ORDER BY o.data_ocorrencia DESC
    ''', (aluno_id,)).fetchall()
    
    fmds = db.execute('''
        SELECT fmd_id, data_fmd, tipo_falta, medida_aplicada, status
        FROM ficha_medida_disciplinar
        WHERE aluno_id = ?
        ORDER BY data_fmd DESC
    ''', (aluno_id,)).fetchall()
    
    return render_template('formularios/prontuario.html', 
                         aluno=dict(aluno), 
                         rfos=rfos, 
                         fmds=fmds)


# =========================
# Novos endpoints API
# =========================

@formularios_bp.route('/api/bimestres')
@login_required
def api_bimestres():
    """Retorna os bimestres cadastrados: [{ano, numero, inicio, fim}]"""
    db = get_db()
    try:
        rows = db.execute('SELECT ano, numero, inicio, fim FROM bimestres ORDER BY ano DESC, numero').fetchall()
        data = [{'ano': r['ano'], 'numero': r['numero'], 'inicio': r['inicio'], 'fim': r['fim']} for r in rows]
        return jsonify(data)
    except Exception:
        return jsonify([])

@formularios_bp.route('/api/config', methods=['GET', 'POST'])
@login_required
def api_config():
    """
    GET: retorna os valores-padrão das medidas.
    POST: atualiza os valores (recebe JSON).
    """
    db = get_db()
    if request.method == 'GET':
        try:
            rows = db.execute('SELECT chave, valor FROM tabela_disciplinar_config').fetchall()
            res = {r['chave']: float(r['valor']) for r in rows}
            # garantir keys padrão
            defaults = {
                'advertencia_oral': -0.1,
                'advertencia_escrita': -0.3,
                'suspensao_dia': -0.5,
                'acao_educativa_dia': -1.0,
                'elogio_individual': 0.5,
                'elogio_coletivo': 0.3
            }
            for k, v in defaults.items():
                if k not in res:
                    res[k] = v
            return jsonify(res)
        except Exception:
            return jsonify({
                'advertencia_oral': -0.1,
                'advertencia_escrita': -0.3,
                'suspensao_dia': -0.5,
                'acao_educativa_dia': -1.0,
                'elogio_individual': 0.5,
                'elogio_coletivo': 0.3
            })
    else:
        # POST: espera JSON com as chaves e valores numéricos
        try:
            payload = request.get_json(force=True)
            mapping = {
                'advertencia_oral': float(payload.get('advertencia_oral', -0.1)),
                'advertencia_escrita': float(payload.get('advertencia_escrita', -0.3)),
                'suspensao_dia': float(payload.get('suspensao_dia', -0.5)),
                'acao_educativa_dia': float(payload.get('acao_educativa_dia', -1.0)),
                'elogio_individual': float(payload.get('elogio_individual', 0.5)),
                'elogio_coletivo': float(payload.get('elogio_coletivo', 0.3))
            }
            for chave, valor in mapping.items():
                # INSERT OR REPLACE behavior: attempt update, else insert
                try:
                    db.execute('INSERT INTO tabela_disciplinar_config (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=datetime("now")', (chave, valor))
                except Exception:
                    # fallback para SQLite sem DO UPDATE (compatibilidade)
                    try:
                        db.execute('INSERT OR REPLACE INTO tabela_disciplinar_config (id, chave, valor, atualizado_em) VALUES ((SELECT id FROM tabela_disciplinar_config WHERE chave = ?), ?, ?, datetime("now"))', (chave, chave, valor))
                    except Exception:
                        pass
            db.commit()
            return jsonify({'success': True})
        except Exception as e:
            current_app.logger.exception('Erro ao salvar config de tabela disciplinar')
            return jsonify({'success': False, 'error': str(e)}), 500


@formularios_bp.route('/api/aluno_pontuacao')
@login_required
def api_aluno_pontuacao():
    """
    Retorna pontuação do aluno para ano/bimestre informado (ou bimestre atual por data se não informado).
    Response:
      { pontuacao_inicial, pontuacao_atual, acrescimo_info (opcional) }
    """
    aluno_id = request.args.get('aluno_id')
    ano = request.args.get('ano')
    bimestre = request.args.get('bimestre')
    db = get_db()
    if not aluno_id:
        return jsonify({'error':'aluno_id obrigatório'}), 400

    try:
        # se não veio ano/bimestre, determina por data atual
        if not ano or not bimestre:
            hoje = datetime.now().strftime('%Y-%m-%d')
            # tenta encontrar bimestre por data
            row = db.execute('SELECT ano, numero FROM bimestres WHERE ? BETWEEN inicio AND fim LIMIT 1', (hoje,)).fetchone()
            if row:
                ano = row['ano']; bimestre = row['numero']
            else:
                # fallback: bimestre por mês (2 meses por bimestre)
                from datetime import date
                m = date.today().month
                bimestre = ((m - 1) // 2) + 1
                ano = date.today().year

        row = db.execute('SELECT pontuacao_inicial, pontuacao_atual, atualizado_em FROM pontuacao_bimestral WHERE aluno_id = ? AND ano = ? AND bimestre = ?', (aluno_id, int(ano), int(bimestre))).fetchone()
        if row:
            inicial = float(row['pontuacao_inicial'])
            atual = float(row['pontuacao_atual'])
        else:
            inicial = 8.0
            atual = 8.0

        # Calcular acrescimo diário (projeção) baseado no histórico:
        last_negative = db.execute('SELECT criado_em FROM pontuacao_historico WHERE aluno_id = ? AND valor_delta < 0 ORDER BY criado_em DESC LIMIT 1', (aluno_id,)).fetchone()
        acrescimo_info = None
        if last_negative:
            from datetime import datetime, timedelta
            last_date = datetime.strptime(last_negative['criado_em'][:19], '%Y-%m-%d %H:%M:%S')
            diff_days = (datetime.now() - last_date).days
            if diff_days > 60:
                dias_acresc = diff_days - 60
                potencial = dias_acresc * 0.2
                max_possivel = max(0, 10.0 - atual)
                acrescimo = min(potencial, max_possivel)
                if acrescimo > 0:
                    acrescimo_info = f'Bônus projetado: +{acrescimo:.2f} pontos (após {diff_days} dias sem perda).'
        return jsonify({
            'pontuacao_inicial': round(inicial, 2),
            'pontuacao_atual': round(atual, 2),
            'acrescimo_info': acrescimo_info
        })
    except Exception:
        return jsonify({'pontuacao_inicial': 8.0, 'pontuacao_atual': 8.0})


# fim de blueprints/formularios.py
