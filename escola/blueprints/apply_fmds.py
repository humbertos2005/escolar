#!/usr/bin/env python3
"""
Blueprint que expõe uma rota para aplicar (criar/atualizar) FMDs a partir de um RFO.

POST /disciplinar/apply_fmds
Content-Type: application/json
Body:
{
  "rfo_id": "RFO-2026-0001",
  "pontos": -0.5,                # opcional
  "medida": "Advertência escrita", # opcional
  "apply": true                  # se true executa (--apply); se falso faz dry-run
}

Retorna JSON com stdout/stderr/returncode do script.
"""
import os
import sys
import subprocess
from flask import Blueprint, request, jsonify, current_app

# tentar importar o decorator de login do projeto (suporte a diferentes import styles)
try:
    from blueprints import utils as utils_mod
except Exception:
    try:
        import utils as utils_mod
    except Exception:
        utils_mod = None

bp_apply_fmds = Blueprint("apply_fmds_bp", __name__)

def _find_cli_script():
    # blueprint está em blueprints/, queremos o apply_rfo_create_fmds.py na raiz do projeto
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(base, "apply_rfo_create_fmds.py"),
        os.path.join(base, "apply_rfo_create_fmds", "apply_rfo_create_fmds.py"),
        os.path.join(base, "apply_rfo_create_fmds.py")
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # fallback: relativo ao current_app.root_path
    p = os.path.join(current_app.root_path, "apply_rfo_create_fmds.py")
    return p

# proteger acesso com login_required se disponível
def _login_required(f):
    if utils_mod and hasattr(utils_mod, "login_required"):
        return utils_mod.login_required(f)
    return f

@bp_apply_fmds.route("/disciplinar/apply_fmds", methods=["POST"])
@_login_required
def apply_fmds():
    data = {}
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    # also accept form data
    if not data:
        data = request.form.to_dict()

    rfo_id = data.get("rfo_id")
    if not rfo_id:
        return jsonify({"ok": False, "error": "rfo_id obrigatório"}), 400

    pontos = data.get("pontos", None)
    medida = data.get("medida", "Medida automática")
    apply_flag = bool(data.get("apply", False))

    # build command
    pyexe = sys.executable or "python"
    script_path = _find_cli_script()
    if not os.path.exists(script_path):
        return jsonify({"ok": False, "error": f"CLI não encontrada em {script_path}"}), 500

    cmd = [pyexe, script_path, rfo_id, "--medida", str(medida)]
    if pontos is not None:
        cmd += ["--pontos", str(pontos)]
    if apply_flag:
        cmd.append("--apply")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        resp = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "applied": apply_flag,
            "cmd": cmd,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
        status = 200 if proc.returncode == 0 else 500
        return jsonify(resp), status
    except Exception as e:
        try:
            current_app.logger.exception("Erro ao executar apply_rfo_create_fmds")
        except Exception:
            pass
        return jsonify({"ok": False, "error": str(e)}), 500