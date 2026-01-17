from flask import Blueprint, render_template, request, jsonify, current_app, url_for, send_file, redirect, session
from database import get_db
from datetime import datetime
import os
import typing
from urllib.parse import unquote
import json

# Tenta usar flask-login se disponível
try:
    from flask_login import current_user
except Exception:
    current_user = None

# helper para formatar created_at
def _format_created_at(prontuario_obj):
    """Retorna (date_str, time_str) ou (None, None). date_str='DD/MM/AAAA', time_str='HH:MM'"""
    if not prontuario_obj:
        return None, None

    created_raw = None
    if isinstance(prontuario_obj, dict):
        created_raw = prontuario_obj.get('created_at') or prontuario_obj.get('createdAt') or prontuario_obj.get('created')
    else:
        created_raw = getattr(prontuario_obj, 'created_at', None) or getattr(prontuario_obj, 'createdAt', None) or getattr(prontuario_obj, 'created', None)

    if not created_raw:
        return None, None

    created_dt = None
    if isinstance(created_raw, (int, float)):
        try:
            created_dt = datetime.fromtimestamp(created_raw)
        except Exception:
            created_dt = None
    elif isinstance(created_raw, str):
        try:
            created_dt = datetime.fromisoformat(created_raw)
        except Exception:
            try:
                created_dt = datetime.strptime(created_raw[:19], '%Y-%m-%dT%H:%M:%S')
            except Exception:
                try:
                    created_dt = datetime.strptime(created_raw[:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S')
                except Exception:
                    created_dt = None
    if created_dt:
        return created_dt.strftime('%d/%m/%Y'), created_dt.strftime('%H:%M')
    return created_raw, None

# Nova versão do get_prontuario_extras com SQLAlchemy
def get_prontuario_extras(db, prontuario_id):
    """
    Retorna dict com:
      - prontuario_rfos: lista de dicts {created_at, added_date_br, added_time, rfo_formatted, data_rfo_br, relato, medida_aplicada, gestor_username}
      - prontuario_comportamento: string ou None
      - prontuario_pontuacao: number or None
    """
    # SQLAlchemy imports dos modelos necessários:
    from models_sqlalchemy import (
        ProntuarioRFO, Ocorrencia, FichaMedidaDisciplinar, Usuario, Comportamento
    )
    extras = {
        "prontuario_rfos": [],
        "prontuario_comportamento": None,
        "prontuario_pontuacao": None
    }

    registros = (
        db.query(ProntuarioRFO, Ocorrencia, FichaMedidaDisciplinar)
          .join(Ocorrencia, ProntuarioRFO.ocorrencia_id == Ocorrencia.id)
          .outerjoin(FichaMedidaDisciplinar, FichaMedidaDisciplinar.rfo_id == Ocorrencia.rfo_id)
          .filter(ProntuarioRFO.prontuario_id == prontuario_id)
          .order_by(ProntuarioRFO.created_at)
          .all()
    )

    for pr, o, fmd in registros:
        # created/added date/time
        raw_created = (pr.created_at or "").replace("T", " ")
        added_date_br = ""
        added_time = ""
        try:
            if len(raw_created) >= 10:
                added_date_br = f"{raw_created[8:10]}/{raw_created[5:7]}/{raw_created[0:4]}"
            if len(raw_created) >= 16:
                added_time = raw_created[11:16]
        except Exception:
            pass

        # RFO number formats
        rfo_raw = o.rfo_id or ""
        rfo_num = ""
        rfo_year = ""
        try:
            if "RFO-" in rfo_raw:
                parts = rfo_raw.split("-")
                if len(parts) >= 3:
                    rfo_year = parts[1]
                    rfo_num = parts[2]
            elif "-" in rfo_raw:
                parts = rfo_raw.split("-")
                if len(parts) >= 2:
                    rfo_year = parts[0]
                    rfo_num = parts[1]
            else:
                rfo_num = rfo_raw[-4:]
                rfo_year = rfo_raw[:4]
            rfo_formatted = f"{str(rfo_num).zfill(4)}/{rfo_year}" if (rfo_num and rfo_year) else rfo_raw
        except Exception:
            rfo_formatted = rfo_raw

        # data_rfo_br
        data_rfo = o.data_ocorrencia or ""
        data_rfo_br = ""
        try:
            data_rfo_norm = data_rfo.replace("T", " ")
            if len(data_rfo_norm) >= 10:
                data_rfo_br = f"{data_rfo_norm[8:10]}/{data_rfo_norm[5:7]}/{data_rfo_norm[0:4]}"
        except Exception:
            data_rfo_br = data_rfo

        relato = o.relato_observador or ""
        medida = (fmd.medida_aplicada if fmd else "") or o.medida_aplicada or ""

        gestor_username = None
        try:
            gid = fmd.gestor_id if fmd else None
            if gid:
                u = db.query(Usuario).filter_by(id=gid).first()
                gestor_username = u.username if u else None
        except Exception:
            gestor_username = None

        extras["prontuario_rfos"].append({
            "created_at": raw_created,
            "added_date_br": added_date_br,
            "added_time": added_time,
            "rfo_formatted": rfo_formatted,
            "data_rfo_br": data_rfo_br,
            "relato": relato,
            "medida_aplicada": medida,
            "gestor_username": gestor_username,
            "author_name": gestor_username
        })

        try:
            if fmd and fmd.comportamento_id:
                comp = db.query(Comportamento).filter_by(id=fmd.comportamento_id).first()
                if comp:
                    extras["prontuario_comportamento"] = comp.descricao
                    extras["prontuario_pontuacao"] = comp.pontuacao
            if extras["prontuario_pontuacao"] is None and fmd and fmd.pontos_aplicados is not None:
                extras["prontuario_pontuacao"] = fmd.pontos_aplicados
        except Exception:
            pass

    return extras

from flask import Blueprint, render_template, request, jsonify, current_app, url_for, send_file, redirect, session
from database import get_db
from urllib.parse import unquote
import os

formularios_prontuario_bp = Blueprint(
    'formularios_prontuario',
    __name__,
    template_folder='templates',
)

def pick_field(obj, candidates, default=''):
    """
    Retorna o primeiro campo existente no objeto (objeto SQLAlchemy ou dict) a partir da lista candidates.
    Se nenhuma das candidates existir retorna default.
    """
    if not obj:
        return default
    for k in candidates:
        val = None
        if isinstance(obj, dict):
            val = obj.get(k, None)
        elif hasattr(obj, k):
            val = getattr(obj, k, None)
        if val is not None:
            return val
    return default

def build_photo_url_from_row(obj) -> str:
    """
    Obtém URL pública da foto do aluno a partir dos dados do objeto SQLAlchemy ou dict.
    Retorna:
      - URL absoluta (http/https) ou path iniciando por /static/
      - url_for() para endpoint api_aluno_foto se não for arquivo físico
      - '' se não conseguir determinar
    """
    if not obj:
        return ''
    filename_candidates = [
        'foto_url', 'foto_path', 'foto_file', 'foto_filename', 'arquivo_foto',
        'photo', 'foto', 'imagem', 'foto_nome', 'caminho_foto'
    ]
    for c in filename_candidates:
        val = None
        if isinstance(obj, dict):
            val = obj.get(c, None)
        elif hasattr(obj, c):
            val = getattr(obj, c, None)
        if val:
            raw = str(val)
            raw = unquote(raw).strip()
            raw_norm = raw.replace('\\', '/')
            if raw_norm.startswith('http://') or raw_norm.startswith('https://'):
                return raw_norm
            if raw_norm.startswith('/static/'):
                return raw_norm
            filename = os.path.basename(raw_norm)
            if filename:
                try:
                    return url_for('static', filename=f"uploads/alunos/{filename}")
                except Exception:
                    return f"/static/uploads/alunos/{filename}"
    # se houver id, tentar deduzir por arquivos em static/uploads/alunos
    aluno_id = obj.get('id') if isinstance(obj, dict) else getattr(obj, 'id', None)
    if aluno_id:
        uploads_dir = os.path.join(current_app.static_folder, 'uploads', 'alunos')
        if os.path.isdir(uploads_dir):
            for fname in sorted(os.listdir(uploads_dir), reverse=True):
                if fname.startswith(f"{aluno_id}_") or fname.startswith(f"{aluno_id}.") or fname == f"{aluno_id}.jpg":
                    try:
                        return url_for('static', filename=f"uploads/alunos/{fname}")
                    except Exception:
                        return f"/static/uploads/alunos/{fname}"
    # fallback: rota dinâmica
    if aluno_id:
        try:
            return url_for('formularios_prontuario.api_aluno_foto', aluno_id=aluno_id)
        except Exception:
            return ''
    return ''

# REMOVIDO: ensure_prontuarios_schema – não necessário para SQLAlchemy com migrations/Alembic!
# Assegure que seu banco já tem os modelos via migrations (não é boa prática criar tabela com SQL ao vivo).

# Não é necessário garantir coluna deleted em SQLAlchemy+Migrations.
# Em projetos modernos, a existência da coluna é garantida pela migration/DDL gerada pelas models.
# Você pode REMOVER a função ensure_deleted_column.

def insert_prontuario_history(db, prontuario_obj, action='update', changed_by=None):
    """
    Insere snapshot do prontuário em prontuarios_history (usando SQLAlchemy).
    prontuario_obj pode ser um modelo ORM ou dict.
    """
    from models_sqlalchemy import ProntuarioHistory
    try:
        if hasattr(prontuario_obj, '__dict__'):
            payload = {k: v for k, v in prontuario_obj.__dict__.items() if not k.startswith('_')}
            prontuario_id = payload.get('id')
        elif isinstance(prontuario_obj, dict):
            payload = dict(prontuario_obj)
            prontuario_id = payload.get('id')
        else:
            payload = {}
            prontuario_id = None

        history = ProntuarioHistory(
            prontuario_id=prontuario_id,
            action=action,
            changed_by=changed_by or (session.get('username') if session else None),
            changed_at=datetime.utcnow().isoformat(),
            payload_json=json.dumps(payload, default=str)
        )
        db.add(history)
        db.commit()
    except Exception:
        db.rollback()
        current_app.logger.exception("Falha ao inserir prontuario_history")

def load_document_header(db):
    """
    Recupera o cabeçalho (estado, secretaria, coordenacao, escola) e logo,
    lendo da tabela ORM Cabecalho (de models_sqlalchemy).
    """
    from models_sqlalchemy import Cabecalho
    try:
        ch = db.query(Cabecalho).order_by(Cabecalho.id.desc()).first()
        if ch:
            rd = ch.__dict__.copy()
            header = {'logo_url': None, 'lines': [], 'school_name': None}
            for key in ('estado', 'secretaria', 'coordenacao'):
                if key in rd and rd[key]:
                    header['lines'].append(str(rd[key]).strip())
            if 'escola' in rd and rd['escola']:
                escola_txt = str(rd['escola']).strip()
                header['lines'].append(escola_txt)
                header['school_name'] = escola_txt
            logo_field = None
            if 'logo_estado' in rd and rd['logo_estado']:
                logo_field = rd['logo_estado']
            elif 'logo_escola' in rd and rd['logo_escola']:
                logo_field = rd['logo_escola']
            if logo_field:
                val = str(logo_field).strip()
                if val.lower().startswith('http://') or val.lower().startswith('https://') or val.startswith('/static/'):
                    header['logo_url'] = val
                else:
                    filename = os.path.basename(val)
                    if filename:
                        try:
                            header['logo_url'] = url_for('static', filename=f"uploads/cabecalhos/{filename}")
                        except Exception:
                            header['logo_url'] = f"/static/uploads/cabecalhos/{filename}"
            return header
    except Exception:
        current_app.logger.exception("Erro ao carregar cabecalho (Cabecalho ORM)")
    return None

from models_sqlalchemy import Prontuario, Aluno

@formularios_prontuario_bp.route('/prontuario', methods=['GET'])
def prontuario():
    """Renderiza formulário de novo prontuário."""
    return render_template('formularios/prontuario.html')

@formularios_prontuario_bp.route('/prontuarios', methods=['GET'])
def listar_prontuarios():
    """
    Lista prontuários cadastrados.
    """
    db = get_db()
    try:
        show_deleted = request.args.get('show_deleted') == '1' and session.get('nivel') == 1
        prontuario_query = db.query(Prontuario)
        if not show_deleted:
            prontuario_query = prontuario_query.filter((Prontuario.deleted == None) | (Prontuario.deleted == 0))
        rows = prontuario_query.order_by(Prontuario.created_at.desc(), Prontuario.id.desc()).all()
        pronts = []
        for p in rows:
            aluno_nome = None
            if p.aluno_id:
                aluno_obj = db.query(Aluno).filter_by(id=p.aluno_id).first()
                if aluno_obj:
                    aluno_nome = aluno_obj.nome
            pronts.append({
                'id': p.id,
                'numero': p.numero,
                'aluno_id': p.aluno_id,
                'aluno_nome': aluno_nome,
                'responsavel': p.responsavel,
                'serie': p.serie,
                'turma': p.turma,
                'created_at': p.created_at,
                'deleted': getattr(p, 'deleted', 0)
            })
        return render_template('formularios/listar_prontuarios.html', prontuarios=pronts, show_deleted=show_deleted)
    except Exception:
        current_app.logger.exception("Erro ao listar prontuários")
        return render_template('formularios/listar_prontuarios.html', prontuarios=[], show_deleted=False), 500

@formularios_prontuario_bp.route('/api/alunos', methods=['GET'])
def api_alunos_autocomplete():
    """
    Autocomplete para alunos.
    """
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    try:
        like_q = f"%{q}%"
        alunos = (
            db.query(Aluno)
            .filter((Aluno.nome.ilike(like_q)) | (Aluno.matricula.ilike(like_q)))
            .order_by(Aluno.nome)
            .limit(50)
            .all()
        )
        out = []
        for a in alunos:
            out.append({
                'id': a.id,
                'nome': a.nome,
                'matricula': a.matricula,
                'serie': getattr(a, 'serie', ''),
                'turma': getattr(a, 'turma', ''),
                'email': getattr(a, 'email', ''),
                'telefone1': getattr(a, 'telefone', '') or getattr(a, 'telefone1', ''),
                'telefone2': getattr(a, 'telefone2', ''),
                'turno': getattr(a, 'turno', ''),
                'responsavel': getattr(a, 'responsavel', ''),
                'foto_url': build_photo_url_from_row(a)
            })
        return jsonify(out)
    except Exception:
        current_app.logger.exception("Erro no endpoint /formularios/api/alunos")
        return jsonify([]), 500

from models_sqlalchemy import Aluno, Ocorrencia
import io

@formularios_prontuario_bp.route('/api/aluno/<int:aluno_id>/rfos', methods=['GET'])
def api_rfos_por_aluno(aluno_id):
    """
    Retorna os RFOs do aluno.
    """
    db = get_db()
    try:
        rows = (
            db.query(Ocorrencia)
            .filter(Ocorrencia.aluno_id == aluno_id)
            .order_by(Ocorrencia.data_ocorrencia.desc(), Ocorrencia.id.desc())
            .limit(500)
            .all()
        )
        out = []
        for r in rows:
            rfo_numero = (
                getattr(r, 'rfo_id', None) or 
                getattr(r, 'rfo', None) or
                getattr(r, 'codigo', None) or
                getattr(r, 'codigo_rfo', None) or
                f"RFO-{r.id}"
            )
            data_ocorrencia = getattr(r, 'data_ocorrencia', None) or getattr(r, 'data', None) or getattr(r, 'created_at', None)
            relato_observador = getattr(r, 'relato_observador', None) or getattr(r, 'relato', None) or getattr(r, 'descricao', None) or getattr(r, 'observacao', None)
            tipo_falta = getattr(r, 'tipo_ocorrencia_nome', None) or getattr(r, 'tipo_ocorrencia', None) or getattr(r, 'tipo', None) or getattr(r, 'natureza', None) or getattr(r, 'tipo_nome', None)
            item_descricao = getattr(r, 'item_descricao', None) or getattr(r, 'descricao_item', None) or getattr(r, 'material_recolhido', None) or getattr(r, 'infracao', None) or getattr(r, 'falta_descricao', None) or getattr(r, 'descricao', None)
            reincidencia = getattr(r, 'reincidencia', 0) or getattr(r, 'eh_reincidencia', 0) or getattr(r, 'reincidente', 0)
            medida_aplicada = getattr(r, 'medida_aplicada', None) or getattr(r, 'medida', None) or getattr(r, 'acao', None) or getattr(r, 'medida_nome', None)
            despacho_gestor = getattr(r, 'despacho_gestor', None) or getattr(r, 'despacho', None) or getattr(r, 'decisao_gestor', None)
            data_despacho = getattr(r, 'data_despacho', None) or getattr(r, 'data_despacho_gestor', None) or getattr(r, 'data_despacho_registro', None)
            out.append({
                'id': r.id,
                'rfo_numero': rfo_numero,
                'data_ocorrencia': data_ocorrencia,
                'relato_observador': relato_observador,
                'tipo_falta': tipo_falta,
                'item_descricao': item_descricao,
                'reincidencia': int(reincidencia) if str(reincidencia).isdigit() else (1 if reincidencia in [True, 'True', 'true', 'SIM', 'S'] else 0),
                'medida_aplicada': medida_aplicada,
                'despacho_gestor': despacho_gestor,
                'data_despacho': data_despacho,
            })
        return jsonify(out)
    except Exception:
        current_app.logger.exception("Erro no endpoint /formularios/api/aluno/<id>/rfos")
        return jsonify([]), 500

@formularios_prontuario_bp.route('/api/aluno/<int:aluno_id>', methods=['GET'])
def api_aluno_get(aluno_id):
    """
    Retorna dados detalhados do aluno.
    """
    db = get_db()
    try:
        a = db.query(Aluno).filter_by(id=aluno_id).first()
        if not a:
            return jsonify({}), 404
        return jsonify({
            'id': a.id,
            'nome': getattr(a, 'nome', ''),
            'matricula': getattr(a, 'matricula', ''),
            'serie': getattr(a, 'serie', ''),
            'turma': getattr(a, 'turma', ''),
            'email': getattr(a, 'email', ''),
            'telefone1': getattr(a, 'telefone', '') or getattr(a, 'telefone1', ''),
            'telefone2': getattr(a, 'telefone2', ''),
            'turno': getattr(a, 'turno', ''),
            'responsavel': getattr(a, 'responsavel', ''),
            'foto_url': build_photo_url_from_row(a),
        })
    except Exception:
        current_app.logger.exception("Erro no endpoint /formularios/api/aluno/<id>")
        return jsonify({}), 500

@formularios_prontuario_bp.route('/api/aluno/<int:aluno_id>/foto', methods=['GET'])
def api_aluno_foto(aluno_id):
    """
    Serve foto do aluno (blob ou arquivo estático).
    """
    db = get_db()
    try:
        aluno = db.query(Aluno).filter_by(id=aluno_id).first()
        if not aluno:
            return '', 404

        # Tenta construir uma URL com as heurísticas existentes
        try:
            photo_url = build_photo_url_from_row(aluno)
        except Exception:
            photo_url = None

        if photo_url and isinstance(photo_url, str):
            if photo_url.startswith('http://') or photo_url.startswith('https://') or photo_url.startswith('/static/') or photo_url.startswith('static/'):
                return redirect(photo_url)

        # Se for foto Blob no campo, servir blob
        for blob_attr in ['foto', 'foto_blob', 'imagem', 'foto_bytes']:
            if hasattr(aluno, blob_attr):
                blob = getattr(aluno, blob_attr)
                if blob:
                    mimetype = getattr(aluno, 'foto_mimetype', 'image/jpeg') or 'image/jpeg'
                    return send_file(io.BytesIO(blob), mimetype=mimetype, as_attachment=False,
                                    download_name=f"aluno_{aluno_id}.jpg")

        # Procurar nomes de arquivo em campos comuns e servir arquivo se encontrado
        filename_candidates = ['foto_filename', 'foto_file', 'foto_path', 'photo', 'foto', 'imagem', 'arquivo_foto', 'foto_nome']
        uploads_dir = os.path.join(current_app.static_folder, 'uploads', 'alunos')
        for c in filename_candidates:
            val = getattr(aluno, c, None)
            if val:
                fname_raw = str(val)
                fname_norm = unquote(fname_raw).replace('\\', '/').strip()
                filename = os.path.basename(fname_norm)
                if not filename:
                    continue
                static_path = os.path.join(uploads_dir, filename)
                if os.path.exists(static_path):
                    return send_file(static_path, mimetype='image/jpeg', as_attachment=False, download_name=filename)

        # Nada encontrado
        return '', 404
    except Exception:
        current_app.logger.exception("Erro ao servir foto do aluno")
        return '', 500

from models_sqlalchemy import Prontuario, Aluno

@formularios_prontuario_bp.route('/prontuario/<int:prontuario_id>', methods=['GET'])
def visualizar_prontuario(prontuario_id):
    """
    Visualização do prontuário (apenas leitura).
    Também carrega o cabeçalho de documentos (Cadastros/Cabeçalho Documentos) e o passa ao template.
    """
    db = get_db()
    try:
        p = db.query(Prontuario).filter_by(id=prontuario_id).first()
        if not p:
            return render_template(
                'formularios/prontuario_view.html',
                prontuario=None,
                aluno=None,
                header=None,
                created_date=None,
                created_time=None,
                viewer_name=None,
            ), 404

        rd = p.__dict__.copy()
        created_date, created_time = _format_created_at(p)

        viewer_name = None
        try:
            if current_user and getattr(current_user, 'is_authenticated', False):
                viewer_name = getattr(current_user, 'nome', None) or getattr(current_user, 'name', None) or getattr(current_user, 'username', None)
        except Exception:
            viewer_name = None
        if not viewer_name:
            viewer_name = session.get('user_nome') or session.get('nome') or session.get('username') or session.get('user')

        aluno = None
        if p.aluno_id:
            a = db.query(Aluno).filter_by(id=p.aluno_id).first()
            if a:
                aluno = a.__dict__.copy()

        # comportamento e pontuação (compatível, removendo dependência do models.py)
        comportamento = rd.get('comportamento') or (aluno and aluno.get('comportamento'))
        pontuacao = rd.get('pontuacao') or (aluno and aluno.get('pontuacao'))

        # Buscar extras (prontuario_rfos, comportamento e pontuacao) - se disponíveis
        extras = get_prontuario_extras(db, p.id)
        if not comportamento:
            comportamento = extras.get("prontuario_comportamento")
        if not pontuacao:
            pontuacao = extras.get("prontuario_pontuacao")

        try:
            header = load_document_header(db)
        except Exception:
            header = None
            current_app.logger.debug("visualizar_prontuario: falha ao carregar header", exc_info=True)

        return render_template(
            'formularios/prontuario_view.html',
            prontuario=rd,
            aluno=aluno,
            header=header,
            prontuario_rfos=extras.get("prontuario_rfos"),
            prontuario_comportamento=extras.get("prontuario_comportamento"),
            prontuario_pontuacao=extras.get("prontuario_pontuacao"),
            created_date=created_date,
            created_time=created_time,
            viewer_name=viewer_name,
            comportamento=comportamento,
            pontuacao=pontuacao,
        )
    except Exception:
        current_app.logger.exception("Erro ao carregar prontuário")
        return render_template(
            'formularios/prontuario_view.html',
            prontuario=None,
            aluno=None,
            header=None,
            created_date=None,
            created_time=None,
            viewer_name=None,
        ), 500

@formularios_prontuario_bp.route('/prontuario/<int:prontuario_id>/edit', methods=['GET', 'POST'])
def editar_prontuario(prontuario_id):
    """
    Edita o prontuário. Em POST atualiza os campos (usado pelo formulário).
    """
    db = get_db()
    from models_sqlalchemy import ProntuarioHistory
    if request.method == 'GET':
        p = db.query(Prontuario).filter_by(id=prontuario_id).first()
        if not p:
            return redirect(url_for('formularios_prontuario.prontuario'))
        rd = p.__dict__.copy()
        aluno = None
        if p.aluno_id:
            a = db.query(Aluno).filter_by(id=p.aluno_id).first()
            if a:
                aluno = a.__dict__.copy()
        return render_template('formularios/prontuario.html', prontuario=rd, aluno=aluno)
    else:
        form = request.form.to_dict(flat=True)
        try:
            p = db.query(Prontuario).filter_by(id=prontuario_id).first()
            if p:
                insert_prontuario_history(db, p, action='edit', changed_by=session.get('username'))
                p.aluno_id = int(form.get('aluno_id')) if form.get('aluno_id') else None
                p.responsavel = form.get('responsavel')
                p.serie = form.get('serie')
                p.turma = form.get('turma')
                p.email = form.get('email')
                p.telefone1 = form.get('telefone1')
                p.telefone2 = form.get('telefone2')
                p.turno = form.get('turno')
                p.registros_fatos = form.get('registros_fatos')
                p.circunstancias_atenuantes = form.get('circ_atenuantes') or form.get('circunstancias_atenuantes')
                p.circunstancias_agravantes = form.get('circ_agravantes') or form.get('circunstancias_agravantes')
                p.deleted = 0
                db.commit()
            else:
                return jsonify({"success": False, "message": "Prontuário não encontrado."}), 404
        except Exception:
            db.rollback()
            current_app.logger.exception("Erro ao atualizar prontuário")
            return jsonify({"success": False, "message": "Erro ao atualizar prontuário."}), 500

        return jsonify({"success": True, "message": "Prontuário atualizado com sucesso."})

from models_sqlalchemy import Prontuario, Aluno

@formularios_prontuario_bp.route('/prontuario/<int:prontuario_id>/delete', methods=['POST'])
def excluir_prontuario(prontuario_id):
    """
    Soft delete: marca deleted=1 e grava snapshot para auditoria.
    """
    db = get_db()
    try:
        p = db.query(Prontuario).filter_by(id=prontuario_id).first()
        if p:
            insert_prontuario_history(db, p, action='delete', changed_by=session.get('username'))
            p.deleted = 1
            db.commit()
        return jsonify({'success': True})
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao excluir prontuário")
        return jsonify({'success': False}), 500

@formularios_prontuario_bp.route('/prontuario/<int:prontuario_id>/print', methods=['GET'])
def imprimir_prontuario(prontuario_id):
    """
    Imprimir (mantido apenas para compatibilidade). Agora calcula um
    suggested_filename (prontuario_<nome_do_aluno>) e passa para o template.
    """
    import re

    db = get_db()
    try:
        p = db.query(Prontuario).filter_by(id=prontuario_id).first()
        if not p:
            return "Prontuário não encontrado", 404
        rd = p.__dict__.copy()

        created_date, created_time = _format_created_at(p)

        viewer_name = None
        try:
            if current_user and getattr(current_user, 'is_authenticated', False):
                viewer_name = getattr(current_user, 'nome', None) or getattr(current_user, 'name', None) or getattr(current_user, 'username', None)
        except Exception:
            viewer_name = None

        if not viewer_name:
            viewer_name = session.get('user_nome') or session.get('nome') or session.get('username') or session.get('user')

        aluno = None
        if p.aluno_id:
            a = db.query(Aluno).filter_by(id=p.aluno_id).first()
            if a:
                aluno = a.__dict__.copy()

        comportamento = rd.get('comportamento') or (aluno and aluno.get('comportamento'))
        pontuacao = rd.get('pontuacao') or (aluno and aluno.get('pontuacao'))

        try:
            extras = get_prontuario_extras(db, p.id) or {}
        except Exception:
            extras = {}
            current_app.logger.debug("imprimir_prontuario: falha ao carregar extras", exc_info=True)

        if not comportamento:
            comportamento = extras.get("prontuario_comportamento")
        if not pontuacao:
            pontuacao = extras.get("prontuario_pontuacao")

        try:
            header = load_document_header(db)
        except Exception:
            header = None
            current_app.logger.debug("imprimir_prontuario: falha ao carregar header", exc_info=True)

        name_candidate = aluno.get('nome') if aluno else None
        if not name_candidate:
            name_candidate = rd.get('aluno_nome') or rd.get('nome') or f"id{rd.get('id')}"
        if not name_candidate:
            name_candidate = f"id{rd.get('id')}"
        raw = str(name_candidate).strip()
        safe = re.sub(r'[^A-Za-z0-9 _\-]', '_', raw)
        safe = re.sub(r'\s+', '_', safe)
        if not safe:
            safe = str(rd.get('id') or 'prontuario')
        suggested_filename = f"prontuario_{safe}"

        auto_print_raw = request.args.get('auto_print', None)
        auto_print = False
        if auto_print_raw is not None:
            try:
                if str(auto_print_raw).lower() in ('1', 'true', 'yes', 'on'):
                    auto_print = True
            except Exception:
                auto_print = bool(auto_print_raw)

        return render_template(
            'formularios/prontuario_impressao.html',
            prontuario=rd,
            aluno=aluno,
            header=header,
            prontuario_rfos=extras.get("prontuario_rfos"),
            prontuario_comportamento=extras.get("prontuario_comportamento"),
            prontuario_pontuacao=extras.get("prontuario_pontuacao"),
            created_date=created_date,
            created_time=created_time,
            viewer_name=viewer_name,
            comportamento=comportamento,
            pontuacao=pontuacao,
            auto_print=auto_print,
            suggested_filename=suggested_filename,
        )
    except Exception:
        current_app.logger.exception("Erro ao imprimir prontuário")
        return "Erro ao imprimir", 500

@formularios_prontuario_bp.route('/visualizacoes/prontuario/<int:prontuario_id>')
def visualizar_prontuario_visualizacao(prontuario_id):
    """
    Rota compatível para Visualizações -> Prontuário.
    Agora reutiliza exatamente a mesma renderização e contexto que a view principal
    (formularios/prontuario_view.html) para que os dois caminhos exibam o mesmo conteúdo.
    """
    db = get_db()
    try:
        p = db.query(Prontuario).filter_by(id=prontuario_id).first()
        if not p:
            return render_template(
                'formularios/prontuario_view.html',
                prontuario=None,
                aluno=None,
                header=None,
                created_date=None,
                created_time=None,
                viewer_name=None,
            ), 404
        rd = p.__dict__.copy()
        created_date, created_time = _format_created_at(p)

        viewer_name = None
        try:
            if current_user and getattr(current_user, 'is_authenticated', False):
                viewer_name = getattr(current_user, 'nome', None) or getattr(current_user, 'name', None) or getattr(current_user, 'username', None)
        except Exception:
            viewer_name = None

        if not viewer_name:
            viewer_name = session.get('user_nome') or session.get('nome') or session.get('username') or session.get('user')

        aluno = None
        if p.aluno_id:
            a = db.query(Aluno).filter_by(id=p.aluno_id).first()
            if a:
                aluno = a.__dict__.copy()

        try:
            header = load_document_header(db)
        except Exception:
            header = None
        extras = get_prontuario_extras(db, p.id)
        return render_template(
            'formularios/prontuario_view.html',
            prontuario=rd,
            aluno=aluno,
            header=header,
            prontuario_rfos=extras["prontuario_rfos"],
            prontuario_comportamento=extras["prontuario_comportamento"],
            prontuario_pontuacao=extras["prontuario_pontuacao"],
            created_date=created_date,
            created_time=created_time,
            viewer_name=viewer_name,
        )
    except Exception:
        current_app.logger.exception("Erro ao renderizar visualização do prontuário")
        return render_template(
            'formularios/prontuario_view.html',
            prontuario=None,
            aluno=None,
            header=None,
            created_date=None,
            created_time=None,
            viewer_name=None,
        ), 500
    
from models_sqlalchemy import Prontuario

@formularios_prontuario_bp.route('/prontuario/save', methods=['POST'])
def salvar_prontuario():
    """
    Salva prontuário:
    - se existir prontuário para o aluno, faz append em registros_fatos (restaurando deleted=0);
    - se não existir, cria registro e gera número;
    - retorna JSON {success, action, id, numero?}
    """
    form = request.form.to_dict(flat=True)
    aluno_id = form.get('aluno_id') or None
    db = get_db()
    try:
        existing = None
        if aluno_id:
            # preferir prontuário não-excluído; se não houver, pegar o primeiro qualquer (incluindo excluídos)
            query = db.query(Prontuario).filter(Prontuario.aluno_id == int(aluno_id))
            query = query.order_by((Prontuario.deleted == None).desc(), Prontuario.deleted.asc())
            existing = query.first()

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        novo_registros = form.get('registros_fatos') or ''
        if existing:
            insert_prontuario_history(db, existing, action='update_before_append', changed_by=session.get('username'))
            existing_rf = existing.registros_fatos or ''
            if existing_rf and novo_registros:
                combined = f"{existing_rf}\n\n--- Adicionado em {timestamp} ---\n{novo_registros}"
            elif novo_registros:
                combined = f"--- Adicionado em {timestamp} ---\n{novo_registros}"
            else:
                combined = existing_rf
            existing.responsavel = form.get('responsavel')
            existing.serie = form.get('serie')
            existing.turma = form.get('turma')
            existing.email = form.get('email')
            existing.telefone1 = form.get('telefone1')
            existing.telefone2 = form.get('telefone2')
            existing.turno = form.get('turno')
            existing.registros_fatos = combined
            existing.circunstancias_atenuantes = form.get('circ_atenuantes') or form.get('circunstancias_atenuantes')
            existing.circunstancias_agravantes = form.get('circ_agravantes') or form.get('circunstancias_agravantes')
            existing.deleted = 0
            db.commit()
            return jsonify({"success": True, "message": "Prontuário atualizado (append) com sucesso.", "action": "updated", "id": existing.id})
        else:
            novo = Prontuario(
                aluno_id=int(aluno_id) if aluno_id else None,
                responsavel=form.get('responsavel'),
                serie=form.get('serie'),
                turma=form.get('turma'),
                email=form.get('email'),
                telefone1=form.get('telefone1'),
                telefone2=form.get('telefone2'),
                turno=form.get('turno'),
                registros_fatos=novo_registros,
                circunstancias_atenuantes=form.get('circ_atenuantes') or form.get('circunstancias_atenuantes'),
                circunstancias_agravantes=form.get('circ_agravantes') or form.get('circunstancias_agravantes'),
                created_at=datetime.utcnow().isoformat(),
                deleted=0
            )
            db.add(novo)
            db.commit()
            new_id = novo.id
            numero = f"PR-{datetime.utcnow().year}-{int(new_id):04d}" if new_id else None
            if numero and new_id:
                try:
                    novo.numero = numero
                    db.commit()
                except Exception:
                    current_app.logger.exception("Falha ao atualizar numero do prontuário")
            return jsonify({"success": True, "message": "Prontuário criado com sucesso.", "action": "created", "id": new_id, "numero": numero})
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao salvar prontuário")
        return jsonify({"success": False, "message": "Erro ao salvar prontuário."}), 500

# Alias: expor também nome plural para importações que o código possa tentar usar.
# Mantemos também o nome singular (formularios_prontuario_bp) para importações que o esperam.
formularios_prontuarios_bp = formularios_prontuario_bp
__all__ = ['formularios_prontuario_bp', 'formularios_prontuarios_bp']
