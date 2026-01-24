from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database import get_db
from datetime import datetime
from .utils import login_required, admin_required, admin_secundario_required
from models_sqlalchemy import Cabecalho
import json
import unicodedata
from models_sqlalchemy import Ata, Aluno

formularios_ata_bp = Blueprint('formularios_ata_bp', __name__, url_prefix='/formularios/atas')

def int_to_words_pt(n):
    unidades = {0:"zero",1:"um",2:"dois",3:"três",4:"quatro",5:"cinco",6:"seis",7:"sete",8:"oito",9:"nove",
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

def norm(s):
    if not s:
        return ""
    s2 = str(s).strip().lower()
    s2 = unicodedata.normalize('NFD', s2)
    s2 = ''.join(ch for ch in s2 if not unicodedata.combining(ch))
    return s2

@formularios_ata_bp.route('/', methods=['GET'])
@admin_secundario_required
def list_atas():
    db = get_db()
    try:
        atas = db.query(Ata).order_by(Ata.ano.desc(), Ata.numero.desc()).all()
        atas_list = []
        for a in atas:
            aluno_nome = a.aluno_nome or ""
            serie_turma = a.serie_turma or ""

            # ENRIQUECER (LOAD) - se faltar, tenta enriquecer com dados do aluno
            if not aluno_nome or not serie_turma:
                aluno = db.query(Aluno).filter_by(id=a.aluno_id).first() if a.aluno_id else None
                if aluno:
                    if not aluno_nome:
                        aluno_nome = aluno.nome
                    if not serie_turma:
                        s = getattr(aluno, 'serie', None)
                        t = getattr(aluno, 'turma', None)
                        if s and t:
                            serie_turma = f"{s} / {t}"
                        elif s:
                            serie_turma = s
                        elif hasattr(aluno, 'serie_turma'):
                            serie_turma = getattr(aluno, 'serie_turma', '')
            atas_list.append({
                "id": a.id,
                "aluno_nome": aluno_nome,
                "serie_turma": serie_turma,
                "numero": a.numero,
                "ano": a.ano,
                "created_at": a.created_at
            })
    except Exception:
        atas_list = []
    return render_template('formularios/atas_list.html', atas=atas_list)

@formularios_ata_bp.route('/nova', methods=['GET', 'POST'])
@admin_secundario_required
def nova_ata():
    db = get_db()
    db.rollback()
    alunos_query = db.query(Aluno).order_by(Aluno.nome).all()
    alunos = [
        {
            'id': a.id,
            'nome': getattr(a, 'nome', ''),
            'serie': getattr(a, 'serie', ''),
            'turma': getattr(a, 'turma', ''),
            'responsavel': getattr(a, 'responsavel', ''),
        } for a in alunos_query
    ]
    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id') or None
        aluno_nome = request.form.get('aluno_nome', '').strip()
        serie_turma = request.form.get('serie_turma', '').strip()
        ano = int(request.form.get('ano') or datetime.now().year)

        try:
            last = db.query(Ata).filter(Ata.ano==ano).order_by(Ata.numero.desc()).first()
            last_num = last.numero if last else 0
            numero = int(last_num) + 1
        except Exception:
            numero = 1

        # Se informar o aluno deixado em branco, busca nome.
        if aluno_id and not aluno_nome:
            a = db.query(Aluno).filter_by(id=aluno_id).first()
            if a:
                aluno_nome = a.nome

        conteudo = request.form.get('conteudo', '').strip()
        participants_json = request.form.get('participants_json', '[]').strip()
        created_by = session.get('user_id')

        try:
            ata = Ata(
                aluno_id = aluno_id,
                aluno_nome = aluno_nome,
                serie_turma = serie_turma,
                numero = numero,
                ano = ano,
                conteudo = conteudo,
                participants_json = participants_json,
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                created_by = created_by
            )
            db.add(ata)
            db.commit()
            flash(f'ATA {numero}/{ano} criada com sucesso.', 'success')
            return redirect(url_for('formularios_ata_bp.list_atas'))
        except Exception as e:
            db.rollback()
            if hasattr(e, "orig") and "unique" in str(e.orig).lower():
                flash('Falha: número duplicado para o ano (unique). Tente novamente.', 'danger')
            else:
                flash(f'Erro ao criar ATA: {e}', 'danger')

    # calcular próximo número para exibição (NNN/AAAA)
    ano_atual = datetime.now().year
    try:
        last = db.query(Ata).filter(Ata.ano==ano_atual).order_by(Ata.numero.desc()).first()
        last_num = last.numero if last else 0
        next_num = int(last_num) + 1
    except Exception:
        next_num = 1
    next_number = f"{next_num:03d}/{ano_atual}"

    return render_template('formularios/ata_form.html', alunos=alunos, aluno_info=None, ata=None, next_number=next_number, next_number_int=next_num, year=ano_atual)

@formularios_ata_bp.route('/<int:ata_id>', methods=['GET'])
@admin_secundario_required
def view_ata(ata_id):
    db = get_db()
    ata_obj = db.query(Ata).filter_by(id=ata_id).first()
    if not ata_obj:
        flash('ATA não encontrada.', 'danger')
        return redirect(url_for('formularios_ata_bp.list_atas'))

    ata = ata_obj.__dict__.copy()
    participants = []
    try:
        if "participants_json" in ata and isinstance(ata.get("participants_json"), str) and ata.get("participants_json").strip():
            participants = json.loads(ata.get("participants_json"))
            if not isinstance(participants, list):
                participants = []
    except Exception:
        participants = []

    # enriquecer campos faltantes de aluno
    if (not ata.get("aluno_nome") or not ata.get("serie_turma") or not ata.get("responsavel")) and ata_obj.aluno_id:
        aluno = db.query(Aluno).filter_by(id=ata_obj.aluno_id).first()
        if aluno:
            if not ata.get("aluno_nome"):
                ata["aluno_nome"] = aluno.nome
            if not ata.get("serie_turma"):
                s = getattr(aluno, "serie", None)
                t = getattr(aluno, "turma", None)
                if s and t:
                    ata["serie_turma"] = f"{s} / {t}"
                elif s:
                    ata["serie_turma"] = s
                elif hasattr(aluno, "serie_turma"):
                    ata["serie_turma"] = getattr(aluno, "serie_turma", "")
            if not ata.get("responsavel"):
                for k in ("responsavel", "responsavel_nome", "nome_responsavel"):
                    if hasattr(aluno, k) and getattr(aluno, k):
                        ata["responsavel"] = getattr(aluno, k)
                        break
    
        # Buscar nome da escola do cabecalho
        escola_nome = None
        cabecalho = db.query(Cabecalho).order_by(Cabecalho.id.desc()).first()
        if cabecalho and getattr(cabecalho, "escola", None):
            escola_nome = cabecalho.escola

        # Calcular data por extenso e adicionar ao objeto ata
        try:
            if ata.get("created_at"):
                dt = datetime.strptime(ata["created_at"], "%Y-%m-%d %H:%M:%S")
                months = ["janeiro","fevereiro","março","abril","maio","junho","julho",
                        "agosto","setembro","outubro","novembro","dezembro"]
                def int_to_words_pt(n):
                    unidades = {0:"zero",1:"um",2:"dois",3:"três",4:"quatro",5:"cinco",6:"seis",7:"sete",8:"oito",9:"nove",
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
                day_words = int_to_words_pt(dt.day)
                year_words = int_to_words_pt(dt.year)
                ata["data_extenso"] = f"{day_words} dias do mês de {months[dt.month-1]} do ano de {year_words}"
        except Exception:
            ata["data_extenso"] = ata.get("created_at")

        # Buscar nome do diretor do cabeçalho/dados_escola
        diretor_nome = None
        cabecalho = db.query(Cabecalho).order_by(Cabecalho.id.desc()).first()
        if cabecalho and getattr(cabecalho, "diretor_nome", None):
            diretor_nome = cabecalho.diretor_nome
        # Se não encontrar no cabecalho, tente DadosEscola
        if not diretor_nome:
            try:
                from models_sqlalchemy import DadosEscola
                dados_escola = db.query(DadosEscola).order_by(DadosEscola.id.desc()).first()
                if dados_escola and getattr(dados_escola, "diretor_nome", None):
                    diretor_nome = dados_escola.diretor_nome
            except Exception:
                pass

        # Garantir participants como lista de dict
        participants = []
        try:
            pj = ata.get("participants_json")
            if isinstance(pj, str) and pj.strip():
                participants = json.loads(pj)
                if not isinstance(participants, list):
                    participants = []
        except Exception:
            participants = []

        ata["participants_json"] = participants  # <-- ESSA LINHA É ESSENCIAL

    return render_template('visualizacoes/ata_print.html', ata=ata, participants=participants, escola_nome=escola_nome, diretor_nome=diretor_nome)

@formularios_ata_bp.route('/<int:ata_id>/editar', methods=['GET','POST'])
@admin_secundario_required
def edit_ata(ata_id):
    db = get_db()
    ata_obj = db.query(Ata).filter_by(id=ata_id).first()
    if not ata_obj:
        flash('ATA não encontrada.', 'danger')
        return redirect(url_for('formularios_ata_bp.list_atas'))

    # TRANSFORMA a lista de Alunos em lista de dicionários:
    alunos_query = db.query(Aluno).order_by(Aluno.nome).all()
    alunos = [
        {
            'id': a.id,
            'nome': getattr(a, 'nome', ''),
            'serie': getattr(a, 'serie', ''),
            'turma': getattr(a, 'turma', ''),
            'responsavel': getattr(a, 'responsavel', ''),
        } for a in alunos_query
    ]

    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id') or None
        aluno_nome = request.form.get('aluno_nome', '').strip()
        serie_turma = request.form.get('serie_turma', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        participants_json = request.form.get('participants_json', '[]').strip()
        responsavel = request.form.get('responsavel', '').strip()
        ata_obj.responsavel = responsavel

        if aluno_id and not aluno_nome:
            a = db.query(Aluno).filter_by(id=aluno_id).first()
            if a:
                aluno_nome = a.nome

        try:
            ata_obj.aluno_id = aluno_id
            ata_obj.aluno_nome = aluno_nome
            ata_obj.serie_turma = serie_turma
            ata_obj.conteudo = conteudo
            ata_obj.participants_json = participants_json
            ata_obj.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.commit()
            flash('ATA atualizada com sucesso.', 'success')
            return redirect(url_for('formularios_ata_bp.list_atas'))
        except Exception as e:
            db.rollback()
            flash(f'Erro ao atualizar ATA: {e}', 'danger')

    ata = ata_obj.__dict__.copy()

    # GARANTA que participants_json_val seja SEMPRE uma string JSON válida!
    participants_json_val = ata.get('participants_json') or '[]'
    # Corrige caso venha um dict/lista (não string)
    if not isinstance(participants_json_val, str):
        try:
            participants_json_val = json.dumps(participants_json_val)
        except Exception:
            participants_json_val = '[]'

    # Busca o responsável do aluno, se houver um aluno_id definido
    responsavel = ''
    if ata.get('aluno_id'):
        aluno = db.query(Aluno).filter_by(id=ata['aluno_id']).first()
        if aluno and hasattr(aluno, 'responsavel'):
            responsavel = aluno.responsavel or ''
    # Se já existe na ata (caso de salvamento antigo), use ele
    if not responsavel and ata.get('responsavel'):
        responsavel = ata['responsavel']

    ata['responsavel'] = responsavel  # agora sempre preenche

    return render_template(
        'formularios/ata_form.html',
        ata=ata,
        alunos=alunos,
        aluno_info=None,
        participants_json_val=participants_json_val
    )

@formularios_ata_bp.route('/<int:ata_id>/excluir', methods=['POST'])
@admin_secundario_required
def delete_ata(ata_id):
    db = get_db()
    ata = db.query(Ata).filter_by(id=ata_id).first()
    if not ata:
        flash('ATA não encontrada.', 'danger')
        return redirect(url_for('formularios_ata_bp.list_atas'))
    try:
        db.delete(ata)
        db.commit()
        flash(f'ATA {ata.numero}/{ata.ano} excluída.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir ATA: {e}', 'danger')
    return redirect(url_for('formularios_ata_bp.list_atas'))

@formularios_ata_bp.route("/api/student/<int:student_id>")
def api_student(student_id):
    db = get_db()
    a = db.query(Aluno).filter_by(id=student_id).first()
    if not a:
        return jsonify({}), 404
    data = a.__dict__.copy()
    # Normalizações
    normalized = {}
    normalized['id'] = a.id
    normalized['nome'] = getattr(a, 'nome', None)
    for k in ('serie','serie_turma','turma','turma_nome','responsavel','responsavel_nome','nome_responsavel'):
        val = getattr(a, k, None)
        if val is not None:
            normalized[k] = val
    data.update(normalized)
    return jsonify(data)

@formularios_ata_bp.route("/api/ata/<int:ata_id>")
def api_ata(ata_id):
    db = get_db()
    ata = db.query(Ata).filter_by(id=ata_id).first()
    if not ata:
        return "Not found", 404
    data = ata.__dict__.copy()

    # garantir participants_json como lista
    try:
        if "participants_json" in data and isinstance(data["participants_json"], str):
            data["participants_json"] = json.loads(data["participants_json"])
        else:
            data["participants_json"] = data.get("participants_json") or []
    except Exception:
        data["participants_json"] = []

    # incluir dados do aluno se possível
    try:
        aluno_id = data.get("aluno_id") or data.get("aluno")
        if aluno_id:
            a = db.query(Aluno).filter_by(id=aluno_id).first()
            if a:
                data["aluno"] = a.__dict__.copy()
    except Exception:
        pass

    # construir data por extenso (dia e ano por extenso em palavras)
    try:
        if data.get("created_at"):
            dt = datetime.strptime(data["created_at"], "%Y-%m-%d %H:%M:%S")
            months = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
            day_words = int_to_words_pt(dt.day)
            year_words = int_to_words_pt(dt.year)
            data["data_extenso"] = f"{day_words} dias do mês de {months[dt.month-1]} do ano de {year_words}"
    except Exception:
        data["data_extenso"] = data.get("created_at")

    # normalizar/de-duplicar participants_json, sempre incluindo o responsável
    try:
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

        # buscar responsável
        resp = ""
        if data.get("responsavel"):
            resp = data.get("responsavel")
        elif data.get("aluno") and data["aluno"].get("responsavel"):
            resp = data["aluno"].get("responsavel")
        if resp:
            if norm(resp) not in seen:
                parts.append({"name": resp, "cargo": "Responsável"})
        data["participants_json"] = parts
    except Exception:
        pass

    return jsonify(data)








