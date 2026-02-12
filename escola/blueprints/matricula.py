#!/usr/bin/env python3
"""
Blueprint para atualizar alunos.data_matricula e pontuação inicial automática.

Rota:
  POST /alunos/<int:aluno_id>/matricula
Body (JSON ou form):
  data_matricula: "dd/mm/aaaa" ou "YYYY-MM-DD"

Retorno JSON:
  { "ok": True/False, "updated": True/False, "data_matricula_stored": "YYYY-MM-DD" }
"""
from flask import Blueprint, request, jsonify, current_app
from database import get_db
from models_sqlalchemy import Aluno, PontuacaoBimestral
from datetime import datetime

bp_matricula = Blueprint("matricula_bp", __name__)

# tenta importar login_required do projeto (se existir)
try:
    from blueprints import utils as _utils_mod
    login_required = getattr(_utils_mod, "login_required", lambda f: f)
except Exception:
    login_required = lambda f: f

def br_to_iso(date_str):
    """Converte dd/mm/aaaa -> YYYY-MM-DD. Se já for ISO, retorna como está."""
    if not date_str:
        return None
    s = date_str.strip()
    # já no formato ISO?
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        pass
    # formato BR dd/mm/aaaa
    try:
        d = datetime.strptime(s, "%d/%m/%Y")
        return d.strftime("%Y-%m-%d")
    except Exception:
        return None

@bp_matricula.route("/alunos/<int:aluno_id>/matricula", methods=["POST"])
@login_required
def update_data_matricula(aluno_id):
    # aceita JSON ou form
    data = request.get_json(silent=True) or {}
    if not data:
        data = request.form.to_dict() or {}

    raw = (data.get("data_matricula") or data.get("data_matricula_br") or "").strip()
    iso = br_to_iso(raw) if raw else None
    if raw and not iso:
        return jsonify({"ok": False, "error": "Formato de data inválido. Use dd/mm/aaaa ou YYYY-MM-DD."}), 400

    db = get_db()
    try:
        aluno = db.query(Aluno).filter_by(id=aluno_id).first()
        if not aluno:
            return jsonify({"ok": False, "error": "Aluno não encontrado"}), 404

        aluno.data_matricula = iso
        
        # --- INÍCIO: Bloco de pontuação automática ---
        ano_matricula = int(iso[:4]) if iso else None
        bimestre_inicial = 1

        if ano_matricula:
            # Busca início do 1º bimestre
            bim = db.execute(
                "SELECT inicio FROM bimestres WHERE ano = %s AND numero = 1", (ano_matricula,)
            ).fetchone()
            inicio_bimestre = bim[0] if bim and bim[0] else None

            # Determina data do lançamento de pontos
            data_matricula_dt = datetime.strptime(iso, "%Y-%m-%d")
            data_pontos = None
            if inicio_bimestre:
                inicio_bimestre_dt = datetime.strptime(str(inicio_bimestre), "%Y-%m-%d")
                # Se aluno matriculado antes do bimestre, pontuação entra no 1º dia do bimestre, senão no dia da matrícula
                data_pontos = inicio_bimestre_dt if data_matricula_dt < inicio_bimestre_dt else data_matricula_dt
            else:
                data_pontos = data_matricula_dt

            existe = db.query(PontuacaoBimestral).filter_by(
                aluno_id=aluno_id, ano=str(ano_matricula), bimestre=bimestre_inicial
            ).first()
            if not existe:
                row = PontuacaoBimestral(
                    aluno_id=aluno_id,
                    ano=str(ano_matricula),
                    bimestre=bimestre_inicial,
                    pontuacao_inicial=8.0,
                    pontuacao_atual=8.0,
                    atualizado_em=data_pontos.strftime('%Y-%m-%d %H:%M:%S')
                )
                db.add(row)

            # Lança também no histórico (auditoria)
            from models_sqlalchemy import PontuacaoHistorico
            existe_hist = db.query(PontuacaoHistorico).filter_by(
                aluno_id=aluno_id, ano=ano_matricula, bimestre=bimestre_inicial, tipo_evento='INICIO_ANO'
            ).first()
            if not existe_hist:
                hist = PontuacaoHistorico(
                    aluno_id=aluno_id,
                    ano=ano_matricula,
                    bimestre=bimestre_inicial,
                    valor_delta=8.0,
                    criado_em=data_pontos.strftime('%Y-%m-%d'),
                    tipo_evento="INICIO_ANO"
                )
                db.add(hist)
        # --- FIM: Bloco de pontuação automática ---

        db.commit()
        return jsonify({"ok": True, "updated": True, "data_matricula_stored": iso}), 200
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Erro update data_matricula")
        return jsonify({"ok": False, "error": str(e)}), 500
