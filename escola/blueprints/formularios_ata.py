from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from escola.database import get_db
from datetime import datetime
from .utils import login_required, admin_required, admin_secundario_required
import sqlite3

formularios_ata_bp = Blueprint('formularios_ata_bp', __name__, url_prefix='/formularios/atas')

def detect_alunos(db):
    cur = db.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    candidates = [t for t in tables if any(s in t.lower() for s in ('alun', 'student', 'pessoa', 'person', 'cadast'))]
    for t in candidates:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        name_col = None
        for c in cols:
            if c.lower() in ('nome', 'name', 'full_name', 'nome_completo'):
                name_col = c
                break
        id_col = None
        for c in cols:
            if c.lower() == 'id' or c.lower().endswith('_id'):
                id_col = c
                break
        if id_col and name_col:
            return {'table': t, 'id_col': id_col, 'name_col': name_col}
    return None

@formularios_ata_bp.route('/', methods=['GET'])
@admin_secundario_required
def list_atas():
    db = get_db()
    try:
        # tenta detectar a tabela de alunos para fazer LEFT JOIN (schema din�mico)
        aluno_info = detect_alunos(db)
        if aluno_info:
            # monta consulta que preenche serie_turma a partir de alunos quando necess�rio
            tabela = aluno_info['table']
            id_col = aluno_info['id_col']
            # COALESCE prioriza serie_turma da ATA, sen�o concatena serie / turma do aluno, sen�o serie do aluno
            sql = f"""
                SELECT
                    atas.id,
                    COALESCE(atas.aluno_nome, '') AS aluno_nome,
                    COALESCE(
                        NULLIF(atas.serie_turma, ''),
                        (CASE
                            WHEN {tabela}.serie IS NOT NULL AND {tabela}.turma IS NOT NULL AND {tabela}.turma != ''
                                THEN {tabela}.serie || ' / ' || {tabela}.turma
                            WHEN {tabela}.serie IS NOT NULL AND {tabela}.serie != ''
                                THEN {tabela}.serie
                            ELSE NULL
                         END),
                        ''
                    ) AS serie_turma,
                    atas.numero,
                    atas.ano,
                    atas.created_at
                FROM atas
                LEFT JOIN {tabela} ON atas.aluno_id = {tabela}.{id_col}
                ORDER BY atas.ano DESC, atas.numero DESC
            """
            atas = db.execute(sql).fetchall()
        else:
            atas = db.execute('SELECT id, aluno_nome, serie_turma, numero, ano, created_at FROM atas ORDER BY ano DESC, numero DESC').fetchall()
    except sqlite3.OperationalError:
        atas = []
    atas_list = [dict(a) for a in atas]
    return render_template('formularios/atas_list.html', atas=atas_list)
@formularios_ata_bp.route('/nova', methods=['GET', 'POST'])
@admin_secundario_required
def nova_ata():
    db = get_db()
    aluno_info = detect_alunos(db)
    alunos = []
    if aluno_info:
        try:
            alunos = db.execute(f"SELECT {aluno_info['id_col']} AS id, {aluno_info['name_col']} AS nome FROM {aluno_info['table']} ORDER BY {aluno_info['name_col']}").fetchall()
        except sqlite3.Error:
            alunos = []

    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id') or None
        aluno_nome = request.form.get('aluno_nome', '').strip()
        serie_turma = request.form.get('serie_turma', '').strip()
        ano = int(request.form.get('ano') or datetime.now().year)

        # calcular numero sequencial por ano
        try:
            cur = db.execute("SELECT MAX(numero) AS last FROM atas WHERE ano = ?", (ano,))
            r = cur.fetchone()
            last = r['last'] if r and r['last'] is not None else 0
            numero = int(last) + 1
        except Exception:
            numero = 1

        if aluno_info and aluno_id:
            try:
                r = db.execute(f"SELECT {aluno_info['name_col']} FROM {aluno_info['table']} WHERE {aluno_info['id_col']} = ?", (aluno_id,)).fetchone()
                if r:
                    aluno_nome = r[0] if isinstance(r, (tuple, list)) else r[aluno_info['name_col']]
            except Exception:
                pass

        conteudo = request.form.get('conteudo', '').strip()
        participants_json = request.form.get('participants_json', '[]').strip()
        created_by = session.get('user_id')

        try:
            db.execute(
                "INSERT INTO atas (aluno_id, aluno_nome, serie_turma, numero, ano, conteudo, participants_json, created_at, updated_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (aluno_id, aluno_nome, serie_turma, numero, ano, conteudo, participants_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), created_by)
            )
            db.commit()
            flash(f'ATA {numero}/{ano} criada com sucesso.', 'success')
            return redirect(url_for('formularios_ata_bp.list_atas'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash('Falha: n�mero duplicado para o ano (unique). Tente novamente.', 'danger')
        except Exception as e:
            db.rollback()
            flash(f'Erro ao criar ATA: {e}', 'danger')

        # calcular pr�ximo n�mero para exibi��o (NNN/AAAA)
    ano = datetime.now().year
    try:
        cur = db.execute("SELECT MAX(numero) AS last FROM atas WHERE ano = ?", (ano,))
        r = cur.fetchone()
        last = r['last'] if r and r['last'] is not None else 0
        next_num = int(last) + 1
    except Exception:
        next_num = 1
    next_number = f"{next_num:03d}/{ano}"

        # normalizar alunos para JSON serializ�vel (Row -> dict)
    try:
        if isinstance(alunos, list) and len(alunos) > 0 and not isinstance(alunos[0], dict):
            alunos = [dict(a) for a in alunos]
    except Exception:
        pass
    return render_template('formularios/ata_form.html', alunos=alunos, aluno_info=aluno_info, ata=None, next_number=next_number, next_number_int=next_num, year=ano)

@formularios_ata_bp.route('/<int:ata_id>', methods=['GET'])
@admin_secundario_required
def view_ata(ata_id):
    db = get_db()
    ata_row = db.execute("SELECT * FROM atas WHERE id = ?", (ata_id,)).fetchone()
    if not ata_row:
        flash('ATA n�o encontrada.', 'danger')
        return redirect(url_for('formularios_ata_bp.list_atas'))

    ata = dict(ata_row)

    # carregar participants_json se armazenado como string JSON
    participants = []
    try:
        if "participants_json" in ata and isinstance(ata.get("participants_json"), str) and ata.get("participants_json").strip():
            import json
            try:
                participants = json.loads(ata.get("participants_json"))
                if not isinstance(participants, list):
                    participants = []
            except Exception:
                participants = []
    except Exception:
        participants = []

    # tentar enriquecer com dados do aluno (serie, turma, responsavel) se faltarem
    try:
        aluno_id = ata.get("aluno_id") or ata.get("aluno")
        aluno_info = detect_alunos(db)
        if aluno_info and aluno_id:
            try:
                ar = db.execute(f"SELECT * FROM {aluno_info['table']} WHERE {aluno_info['id_col']} = ?", (aluno_id,)).fetchone()
                if ar:
                    aluno = dict(ar)
                    if not ata.get("aluno_nome"):
                        ata["aluno_nome"] = aluno.get(aluno_info['name_col']) or ata.get("aluno_nome")
                    if not ata.get("serie_turma"):
                        s = aluno.get("serie")
                        t = aluno.get("turma")
                        if s and t:
                            ata["serie_turma"] = f"{s} / {t}"
                        elif s:
                            ata["serie_turma"] = s
                        elif aluno.get("serie_turma"):
                            ata["serie_turma"] = aluno.get("serie_turma")
                    if not ata.get("responsavel"):
                        for k in ("responsavel", "responsavel_nome", "nome_responsavel"):
                            if k in aluno and aluno.get(k):
                                ata["responsavel"] = aluno.get(k)
                                break
            except Exception:
                pass
    except Exception:
        pass

    return render_template('formularios/ata_view.html', ata=ata, participants=participants)

@formularios_ata_bp.route('/<int:ata_id>/editar', methods=['GET','POST'])
@admin_secundario_required
def edit_ata(ata_id):
    db = get_db()
    ata = db.execute("SELECT * FROM atas WHERE id = ?", (ata_id,)).fetchone()
    if not ata:
        flash('ATA n�o encontrada.', 'danger')
        return redirect(url_for('formularios_ata_bp.list_atas'))

    aluno_info = detect_alunos(db)
    alunos = []
    if aluno_info:
        try:
            alunos = db.execute(f"SELECT {aluno_info['id_col']} AS id, {aluno_info['name_col']} AS nome FROM {aluno_info['table']} ORDER BY {aluno_info['name_col']}").fetchall()
        except sqlite3.Error:
            alunos = []

    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id') or None
        aluno_nome = request.form.get('aluno_nome', '').strip()
        serie_turma = request.form.get('serie_turma', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        participants_json = request.form.get('participants_json', '[]').strip()

        if aluno_info and aluno_id:
            try:
                r = db.execute(f"SELECT {aluno_info['name_col']} FROM {aluno_info['table']} WHERE {aluno_info['id_col']} = ?", (aluno_id,)).fetchone()
                if r:
                    aluno_nome = r[0] if isinstance(r, (tuple, list)) else r[aluno_info['name_col']]
            except Exception:
                pass

        try:
            db.execute(
                "UPDATE atas SET aluno_id = ?, aluno_nome = ?, serie_turma = ?, conteudo = ?, participants_json = ?, updated_at = ? WHERE id = ?",
                (aluno_id, aluno_nome, serie_turma, conteudo, participants_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ata_id)
            )
            db.commit()
            flash('ATA atualizada com sucesso.', 'success')
            return redirect(url_for('formularios_ata_bp.list_atas'))
        except Exception as e:
            db.rollback()
            flash(f'Erro ao atualizar ATA: {e}', 'danger')

        # normalizar alunos para JSON serializ�vel (Row -> dict)
    try:
        if isinstance(alunos, list) and len(alunos) > 0 and not isinstance(alunos[0], dict):
            alunos = [dict(a) for a in alunos]
    except Exception:
        pass
    return render_template('formularios/ata_form.html', ata=dict(ata), alunos=alunos, aluno_info=aluno_info)

@formularios_ata_bp.route('/<int:ata_id>/excluir', methods=['POST'])
@admin_secundario_required
def delete_ata(ata_id):
    db = get_db()
    ata = db.execute("SELECT id, numero, ano FROM atas WHERE id = ?", (ata_id,)).fetchone()
    if not ata:
        flash('ATA n�o encontrada.', 'danger')
        return redirect(url_for('formularios_ata_bp.list_atas'))
    try:
        db.execute("DELETE FROM atas WHERE id = ?", (ata_id,))
        db.commit()
        flash(f'ATA {ata["numero"]}/{ata["ano"]} exclu�da.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir ATA: {e}', 'danger')
    return redirect(url_for('formularios_ata_bp.list_atas'))

# --- endpoint para obter dados completos de um aluno (usado pelo autocomplete) ---
@formularios_ata_bp.route("/api/student/<int:student_id>")
def api_student(student_id):
    db = get_db()
    info = detect_alunos(db)
    if not info:
        return jsonify({}), 404
    try:
        # buscar registro completo na tabela detectada
        r = db.execute(f"SELECT * FROM {info['table']} WHERE {info['id_col']} = ?", (student_id,)).fetchone()
        if not r:
            return jsonify({}), 404
        data = dict(r)
        # normalizar algumas chaves comuns para facilitar o JS
        normalized = {}
        normalized['id'] = data.get(info['id_col'])
        normalized['nome'] = data.get(info['name_col'])
        # tentar mapear campos comuns
        for k in ('serie','serie_turma','turma','turma_nome','responsavel','responsavel_nome','nome_responsavel'):
            if k in data and data.get(k) not in (None, ''):
                normalized[k] = data.get(k)
        # mesclar e devolver
        data.update(normalized)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# --- fim endpoint aluno ---
# --- API: devolver dados de uma ATA em JSON (usado pela visualiza��o) ---
@formularios_ata_bp.route("/api/ata/<int:ata_id>")
def api_ata(ata_id):
    try:
        db = get_db()
        r = db.execute("SELECT * FROM atas WHERE id = ?", (ata_id,)).fetchone()
        if not r:
            return ("Not found", 404)
        data = dict(r)

        # garantir participants_json como lista
        try:
            if "participants_json" in data and isinstance(data["participants_json"], str):
                import json
                try:
                    data["participants_json"] = json.loads(data["participants_json"])
                except Exception:
                    data["participants_json"] = []
            else:
                data["participants_json"] = data.get("participants_json") or []
        except Exception:
            data["participants_json"] = []

        # incluir dados do aluno se poss�vel
        try:
            aluno_id = data.get("aluno_id") or data.get("aluno")
            if aluno_id:
                ar = db.execute("SELECT * FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
                if ar:
                    data["aluno"] = dict(ar)
        except Exception:
            pass

        # construir data por extenso (dia e ano por extenso em palavras)
        try:
            from datetime import datetime
            import unicodedata

            def int_to_words_pt(n):
                # suportar 0..9999 (suficiente para anos como 2025)
                unidades = {0:"zero",1:"um",2:"dois",3:"tr�s",4:"quatro",5:"cinco",6:"seis",7:"sete",8:"oito",9:"nove",
                            10:"dez",11:"onze",12:"doze",13:"treze",14:"quatorze",15:"quinze",16:"dezesseis",17:"dezessete",
                            18:"dezoito",19:"dezenove"}
                dezenas = {20:"vinte",30:"trinta",40:"quarenta",50:"cinquenta",60:"sessenta",70:"setenta",80:"oitenta",90:"noventa"}
                centenas = {100:"cem",200:"duzentos",300:"trezentos",400:"quatrocentos",500:"quinhentos",600:"seiscentos",700:"setecentos",800:"oitocentos",900:"novecentos"}

                if n < 0:
                    return "menos " + int_to_words_pt(-n)
                if n < 20:
                    return unidades[n]
                if n < 100:
                    d = (n // 10) * 10
                    r = n - d
                    if r == 0:
                        return dezenas[d]
                    return dezenas[d] + " e " + int_to_words_pt(r)
                if n < 1000:
                    c = (n // 100) * 100
                    r = n - c
                    if n == 100:
                        return "cem"
                    nomec = centenas.get(c, "")
                    if r == 0:
                        return nomec
                    return nomec + " e " + int_to_words_pt(r)
                if n < 1000000:
                    mil = n // 1000
                    r = n % 1000
                    mil_part = ""
                    if mil == 1:
                        mil_part = "mil"
                    else:
                        mil_part = int_to_words_pt(mil) + " mil"
                    if r == 0:
                        return mil_part
                    return mil_part + " e " + int_to_words_pt(r)
                return str(n)

            if data.get("created_at"):
                try:
                    dt = datetime.strptime(data["created_at"], "%Y-%m-%d %H:%M:%S")
                    months = ["janeiro","fevereiro","mar�o","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
                    day_words = int_to_words_pt(dt.day)
                    year_words = int_to_words_pt(dt.year)
                    # formar frase no estilo que voc� pediu:
                    # "dezesseis dias do m�s de dezembro do ano de dois mil e vinte e cinco"
                    data["data_extenso"] = f"{day_words} dias do m�s de {months[dt.month-1]} do ano de {year_words}"
                except Exception:
                    data["data_extenso"] = data.get("created_at")
        except Exception:
            pass

        # normalizar e deduplicar participants_json; garantir inclus�o do respons�vel
        try:
            import unicodedata
            def norm(s):
                if not s:
                    return ""
                s2 = str(s).strip().lower()
                s2 = unicodedata.normalize('NFD', s2)
                s2 = ''.join(ch for ch in s2 if not unicodedata.combining(ch))
                return s2

            parts = []
            seen = set()
            raw_parts = data.get("participants_json") or []
            if isinstance(raw_parts, list):
                for p in raw_parts:
                    if not isinstance(p, dict):
                        continue
                    name = p.get("name") or p.get("nome") or ""
                    cargo = p.get("cargo") or p.get("role") or ""
                    n = norm(name)
                    if n and n not in seen:
                        seen.add(n)
                        parts.append({"name": name, "cargo": cargo})

            # buscar respons�vel (tanto em ata.responsavel quanto em aluno.responsavel)
            resp = ""
            if data.get("responsavel"):
                resp = data.get("responsavel")
            elif data.get("aluno") and data["aluno"].get("responsavel"):
                resp = data["aluno"].get("responsavel")

            if resp:
                if norm(resp) not in seen:
                    parts.append({"name": resp, "cargo": "Respons�vel"})

            data["participants_json"] = parts
        except Exception:
            pass

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --- fim API ATA ---








