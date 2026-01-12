from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
import os, json, datetime

formularios_ata_ui_bp = Blueprint("formularios_ata_ui_bp", __name__)

def data_path(filename):
    return os.path.join(current_app.root_path, "data", filename)

def load_json_file(filename):
    path = data_path(filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(filename, obj):
    path = data_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def get_next_number_from_store():
    atas = load_json_file("atas.json")
    year = datetime.datetime.now().year
    max_num = 0
    for a in atas:
        try:
            if int(a.get("ano", 0)) == year:
                num = int(a.get("numero_int", 0))
                if num > max_num:
                    max_num = num
        except Exception:
            continue
    next_int = max_num + 1
    formatted = f"{next_int:03d}/{year}"
    return {"numero": formatted, "numero_int": next_int, "ano": year}

@formularios_ata_ui_bp.route("/formularios/atas/new", methods=["GET"])
def new_ata():
    nxt = get_next_number_from_store()
    return render_template("formularios/ata_form.html", next_number=nxt["numero"], next_number_int=nxt["numero_int"], year=nxt["ano"])

@formularios_ata_ui_bp.route("/formularios/atas/new", methods=["POST"])
def create_ata():
    data = request.form.to_dict() if request.form else request.get_json() or {}
    numero = data.get("numero") or data.get("next_number")
    aluno_id = data.get("aluno_id") or None
    aluno_nome = data.get("aluno_nome") or data.get("aluno")
    serie = data.get("serie") or ""
    turma = data.get("turma") or ""
    responsavel = data.get("responsavel") or ""
    relato = data.get("relato") or ""
    participantes = []
    if data.get("participants_json"):
        try:
            participantes = json.loads(data.get("participants_json"))
        except Exception:
            participantes = []

    store = load_json_file("atas.json")
    year = datetime.datetime.now().year
    try:
        numero_int = int(str(numero).split("/")[0])
    except Exception:
        numero_int = get_next_number_from_store()["numero_int"]

    new_id = int(datetime.datetime.now().timestamp() * 1000)
    ata_obj = {
        "id": new_id,
        "numero": numero,
        "numero_int": numero_int,
        "ano": year,
        "aluno_id": int(aluno_id) if aluno_id else None,
        "aluno_nome": aluno_nome,
        "serie": serie,
        "turma": turma,
        "responsavel": responsavel,
        "relato": relato,
        "participantes": participantes,
        "created_at": datetime.datetime.now().isoformat()
    }
    store.append(ata_obj)
    save_json_file("atas.json", store)
    flash("ATA registrada com sucesso.", "success")
    return redirect(url_for("dashboard"))

@formularios_ata_ui_bp.route("/api/students")
def api_students():
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify([])

    students = load_json_file("students.json")
    qlow = q.lower()
    results = []
    for s in students:
        nome = s.get("nome","")
        if qlow in nome.lower():
            results.append({
                "id": s.get("id"),
                "nome": nome,
                "serie": s.get("serie",""),
                "turma": s.get("turma",""),
                "responsavel": s.get("responsavel","")
            })
    return jsonify(results[:20])

@formularios_ata_ui_bp.route("/api/ata/next_number")
def api_next_number():
    nxt = get_next_number_from_store()
    return jsonify(nxt)
