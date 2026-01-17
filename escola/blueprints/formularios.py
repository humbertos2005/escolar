from flask import Blueprint, render_template, request, jsonify, current_app
from escola.database import get_db
from .utils import login_required, admin_secundario_required
from datetime import datetime, date
from escola.models_sqlalchemy import (
    FaltaDisciplinar, Ocorrencia, Aluno, FichaMedidaDisciplinar,
    Usuario, TipoOcorrencia, Bimestre, TabelaDisciplinarConfig,
    PontuacaoBimestral, PontuacaoHistorico
)

formularios_bp = Blueprint('formularios_bp', __name__)

@formularios_bp.route('/tabela_disciplinar')
@admin_secundario_required
def tabela_disciplinar():
    """Exibe a tabela disciplinar com todas as faltas e medidas."""
    db = get_db()
    ordem_natureza = {
        'LEVE': 1, 'MÉDIA': 2, 'GRAVE': 3, 'GRAVÍSSIMA': 4
    }
    faltas = db.query(FaltaDisciplinar).all()
    # Ordena na mesma lógica do SQL
    faltas = sorted(
        faltas,
        key=lambda f: (ordem_natureza.get((f.natureza or '').upper(), 5), f.descricao or '')
    )
    return render_template('formularios/tabela_disciplinar.html', faltas=faltas)

@formularios_bp.route('/rfo/<int:ocorrencia_id>')
@admin_secundario_required
def formulario_rfo(ocorrencia_id):
    """Gera o formulário RFO imprimível."""
    db = get_db()
    rfo = (
        db.query(Ocorrencia, Aluno, TipoOcorrencia, Usuario)
          .join(Aluno, Ocorrencia.aluno_id == Aluno.id)
          .join(TipoOcorrencia, Ocorrencia.tipo_ocorrencia_id == TipoOcorrencia.id)
          .outerjoin(Usuario, Ocorrencia.responsavel_registro_id == Usuario.id)
          .filter(Ocorrencia.id == ocorrencia_id)
          .first()
    )
    if not rfo:
        return "RFO não encontrado", 404

    oc, aluno, tipoc, usuario = rfo
    # Monta dict para facilitar no template  
    rfo_dict = {**oc.__dict__, 
                "matricula": aluno.matricula, "nome_aluno": aluno.nome,
                "serie": aluno.serie, "turma": aluno.turma,
                "tipo_ocorrencia_nome": tipoc.nome,
                "responsavel_registro_username": getattr(usuario, "username", "") if usuario else ""}
    return render_template('formularios/rfo.html', rfo=rfo_dict)

@formularios_bp.route('/fmd/<int:fmd_id>')
@admin_secundario_required
def formulario_fmd(fmd_id):
    """Gera o formulário FMD imprimível."""
    db = get_db()
    fmd = (
        db.query(FichaMedidaDisciplinar, Aluno, Usuario)
        .join(Aluno, FichaMedidaDisciplinar.aluno_id == Aluno.id)
        .outerjoin(Usuario, FichaMedidaDisciplinar.responsavel_id == Usuario.id)
        .filter(FichaMedidaDisciplinar.id == fmd_id)
        .first()
    )
    if not fmd:
        return "FMD não encontrada", 404

    fmd_obj, aluno, usuario = fmd
    fmd_dict = {**fmd_obj.__dict__, 
                "matricula": aluno.matricula, "nome_aluno": aluno.nome,
                "serie": aluno.serie, "turma": aluno.turma,
                "responsavel_username": getattr(usuario, "username", "") if usuario else ""}
    return render_template('formularios/fmd.html', fmd=fmd_dict)

@formularios_bp.route('/prontuario/<int:aluno_id>')
@admin_secundario_required
def prontuario(aluno_id):
    """Gera o prontuário completo do aluno."""
    db = get_db()
    aluno = db.query(Aluno).filter_by(id=aluno_id).first()
    if aluno is None:
        return "Aluno não encontrado", 404

    rfos = (
        db.query(
            Ocorrencia.rfo_id, Ocorrencia.data_ocorrencia, Ocorrencia.status,
            TipoOcorrencia.nome.label("tipo_ocorrencia_nome"),
            Ocorrencia.tipo_falta, Ocorrencia.medida_aplicada
        )
        .outerjoin(TipoOcorrencia, Ocorrencia.tipo_ocorrencia_id == TipoOcorrencia.id)
        .filter(Ocorrencia.aluno_id == aluno_id)
        .order_by(Ocorrencia.data_ocorrencia.desc())
        .all()
    )
    fmds = (
        db.query(
            FichaMedidaDisciplinar.fmd_id, FichaMedidaDisciplinar.data_fmd,
            FichaMedidaDisciplinar.tipo_falta, FichaMedidaDisciplinar.medida_aplicada,
            FichaMedidaDisciplinar.status
        )
        .filter(FichaMedidaDisciplinar.aluno_id == aluno_id)
        .order_by(FichaMedidaDisciplinar.data_fmd.desc())
        .all()
    )
    return render_template(
        'formularios/prontuario.html',
        aluno=aluno,
        rfos=rfos,
        fmds=fmds
    )

# =========================
# Novos endpoints API
# =========================

@formularios_bp.route('/api/bimestres')
@login_required
def api_bimestres():
    """Retorna os bimestres cadastrados: [{ano, numero, inicio, fim}]"""
    db = get_db()
    try:
        rows = (
            db.query(Bimestre)
              .order_by(Bimestre.ano.desc(), Bimestre.numero)
              .all()
        )
        data = [{'ano': r.ano, 'numero': r.numero, 'inicio': r.inicio, 'fim': r.fim} for r in rows]
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
            rows = db.query(TabelaDisciplinarConfig).all()
            res = {r.chave: float(r.valor) for r in rows}
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
                # Tenta atualizar primeiro
                record = db.query(TabelaDisciplinarConfig).filter_by(chave=chave).first()
                if record:
                    record.valor = valor
                    from datetime import datetime as dt
                    record.atualizado_em = dt.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    from datetime import datetime as dt
                    novo = TabelaDisciplinarConfig(
                        chave=chave, valor=valor,
                        atualizado_em=dt.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    db.add(novo)
            db.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.rollback()
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
        return jsonify({'error': 'aluno_id obrigatório'}), 400

    try:
        if not ano or not bimestre:
            hoje = datetime.now().strftime('%Y-%m-%d')
            row = db.query(Bimestre).filter(
                Bimestre.inicio <= hoje, Bimestre.fim >= hoje
            ).order_by(Bimestre.ano.desc(), Bimestre.numero.desc()).first()
            if row:
                ano = row.ano
                bimestre = row.numero
            else:
                m = date.today().month
                bimestre = ((m - 1) // 2) + 1
                ano = date.today().year

        pb = db.query(PontuacaoBimestral).filter_by(
            aluno_id=aluno_id, ano=int(ano), bimestre=int(bimestre)
        ).first()
        if pb:
            inicial = float(pb.pontuacao_inicial)
            atual = float(pb.pontuacao_atual)
        else:
            inicial = 8.0
            atual = 8.0

        last_negative = (
            db.query(PontuacaoHistorico)
            .filter(
                PontuacaoHistorico.aluno_id == aluno_id,
                PontuacaoHistorico.valor_delta < 0
            )
            .order_by(PontuacaoHistorico.criado_em.desc())
            .first()
        )
        acrescimo_info = None
        if last_negative:
            from datetime import timedelta
            last_date = datetime.strptime(last_negative.criado_em[:19], '%Y-%m-%d %H:%M:%S')
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