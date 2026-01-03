#!/usr/bin/env python3
"""
Blueprint mínimo para atualizar alunos.data_matricula.

Rota:
  POST /alunos/<int:aluno_id>/matricula
Body (JSON or form):
  data_matricula: "dd/mm/aaaa" ou "YYYY-MM-DD"

Retorno JSON:
  { "ok": True/False, "updated": True/False, "data_matricula_stored": "YYYY-MM-DD" }
"""
from flask import Blueprint, request, jsonify, current_app
import sqlite3
import os
from datetime import datetime

bp_matricula = Blueprint("matricula_bp", __name__)

# tenta importar login_required do projeto (se existir)
try:
    from blueprints import utils as _utils_mod
    login_required = getattr(_utils_mod, "login_required", lambda f: f)
except Exception:
    login_required = lambda f: f

# caminho relativo ao arquivo do projeto (assume escola.db na raiz do repo)
DB_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "escola.db")

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

    if not os.path.exists(DB_PATH):
        return jsonify({"ok": False, "error": f"DB não encontrado em {DB_PATH}"}), 500

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # verifica se aluno existe
        r = cur.execute("SELECT id FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
        if not r:
            return jsonify({"ok": False, "error": "Aluno não encontrado"}), 404

        # atualiza (pode ser NULL)
        cur.execute("UPDATE alunos SET data_matricula = ? WHERE id = ?", (iso, aluno_id))
        conn.commit()
        return jsonify({"ok": True, "updated": True, "data_matricula_stored": iso}), 200
    except Exception as e:
        current_app.logger.exception("Erro update data_matricula")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass
