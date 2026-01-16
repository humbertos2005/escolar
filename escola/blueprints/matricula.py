#!/usr/bin/env python3
"""
Blueprint m�nimo para atualizar alunos.data_matricula.

Rota:
  POST /alunos/<int:aluno_id>/matricula
Body (JSON or form):
  data_matricula: "dd/mm/aaaa" ou "YYYY-MM-DD"

Retorno JSON:
  { "ok": True/False, "updated": True/False, "data_matricula_stored": "YYYY-MM-DD" }
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

bp_matricula = Blueprint("matricula_bp", __name__)

# tenta importar login_required do projeto (se existir)
try:
    from blueprints import utils as _utils_mod
    login_required = getattr(_utils_mod, "login_required", lambda f: f)
except Exception:
    login_required = lambda f: f

def br_to_iso(date_str):
    """Converte dd/mm/aaaa -> YYYY-MM-DD. Se j� for ISO, retorna como est�."""
    if not date_str:
        return None
    s = date_str.strip()
    # j� no formato ISO?
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

from escola.models_sqlalchemy import Aluno
from escola.database import get_db

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
        return jsonify({"ok": False, "error": "Formato de data inv�lido. Use dd/mm/aaaa ou YYYY-MM-DD."}), 400

    db = get_db()
    try:
        aluno = db.query(Aluno).filter_by(id=aluno_id).first()
        if not aluno:
            return jsonify({"ok": False, "error": "Aluno n�o encontrado"}), 404

        aluno.data_matricula = iso
        db.commit()
        return jsonify({"ok": True, "updated": True, "data_matricula_stored": iso}), 200
    except Exception as e:
        current_app.logger.exception("Erro update data_matricula")
        return jsonify({"ok": False, "error": str(e)}), 500
