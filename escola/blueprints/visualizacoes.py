from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from database import get_db
from .utils import login_required, admin_secundario_required, NIVEL_MAP
from flask_login import current_user
from flask import g
import os
import base64
from werkzeug.utils import secure_filename
from datetime import datetime
import typing
import json
import atexit
import asyncio as _asyncio

visualizacoes_bp = Blueprint('visualizacoes_bp', __name__)

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif'}

def _get_logo_data_and_file(cabecalho):
    """
    Retorna (logo_data, logo_file):
    - logo_data: data URI (string) ou None
    - logo_file: caminho file://... ou None
    Prioriza static/uploads/cabecalhos (plural) e nomes comuns.
    """
    import os, base64, urllib.parse
    logo_data = None
    logo_file = cabecalho.get("logo_file") if cabecalho else None

    try:
        file_path = None
        if isinstance(logo_file, str) and logo_file.startswith("file://"):
            file_path = logo_file[7:]
        else:
            logo_url = (cabecalho.get("logo_url") if cabecalho else "") or ""
            if logo_url:
                try:
                    parsed = urllib.parse.urlparse(logo_url)
                    fname = os.path.basename(parsed.path) if parsed.path else ""
                    if fname:
                        candidate = os.path.join(current_app.root_path, "static", "uploads", "cabecalhos", fname)
                        if os.path.exists(candidate):
                            file_path = candidate
                except Exception:
                    file_path = None

        preferred = os.path.join(current_app.root_path, "static", "uploads", "cabecalhos", "logo_topo.png")
        if (not file_path or not os.path.exists(file_path)) and os.path.exists(preferred):
            file_path = preferred

        if (not file_path or not os.path.exists(file_path)):
            updir = os.path.join(current_app.root_path, "static", "uploads", "cabecalhos")
            try:
                if os.path.isdir(updir):
                    for f in os.listdir(updir):
                        if f.lower().startswith("logo") and f.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                            cand = os.path.join(updir, f)
                            if os.path.exists(cand):
                                file_path = cand
                                break
            except Exception:
                pass

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as _f:
                b = _f.read()
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            mime = "image/png"
            if ext in ("jpg", "jpeg"):
                mime = "image/jpeg"
            elif ext == "gif":
                mime = "image/gif"
            logo_data = "data:" + mime + ";base64," + base64.b64encode(b).decode("ascii")
            logo_file = "file://" + file_path.replace("\\", "/")
    except Exception:
        logo_data = None
    return logo_data, logo_file

def _get_logo_data_and_file(cabecalho):
    """
    Retorna (logo_data, logo_file) onde:
    - logo_data é a data URI (ou None)
    - logo_file é o caminho file://... atualizado (ou o valor existente)
    A função prioriza static/uploads/cabecalhos (plural) e nomes comuns.
    """
    import os, base64, urllib.parse
    logo_data = None
    logo_file = cabecalho.get("logo_file") if cabecalho else None

    try:
        file_path = None
        if isinstance(logo_file, str) and logo_file.startswith("file://"):
            file_path = logo_file[7:]
        else:
            logo_url = (cabecalho.get("logo_url") if cabecalho else "") or ""
            if logo_url:
                try:
                    parsed = urllib.parse.urlparse(logo_url)
                    fname = os.path.basename(parsed.path) if parsed.path else ""
                    if fname:
                        candidate = os.path.join(current_app.root_path, "static", "uploads", "cabecalhos", fname)
                        if os.path.exists(candidate):
                            file_path = candidate
                except Exception:
                    file_path = None

        preferred = os.path.join(current_app.root_path, "static", "uploads", "cabecalhos", "logo_topo.png")
        if (not file_path or not os.path.exists(file_path)) and os.path.exists(preferred):
            file_path = preferred

        if (not file_path or not os.path.exists(file_path)):
            updir = os.path.join(current_app.root_path, "static", "uploads", "cabecalhos")
            try:
                if os.path.isdir(updir):
                    for f in os.listdir(updir):
                        if f.lower().startswith("logo") and f.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                            cand = os.path.join(updir, f)
                            if os.path.exists(cand):
                                file_path = cand
                                break
            except Exception:
                pass

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as _f:
                b = _f.read()
            ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            mime = "image/png"
            if ext in ("jpg", "jpeg"):
                mime = "image/jpeg"
            elif ext == "gif":
                mime = "image/gif"
            logo_data = "data:" + mime + ";base64," + base64.b64encode(b).decode("ascii")
            logo_file = "file://" + file_path.replace("\\", "/")
    except Exception:
        logo_data = None
    return logo_data, logo_file

# ... (todas as demais funções auxiliares do bloco, inclusive a gestão de browsers e o _allowed_file, is_admin) ...

from models_sqlalchemy import Usuario, Aluno
from sqlalchemy import or_

@visualizacoes_bp.route('/usuarios')
@admin_secundario_required
def listar_usuarios():
    """Lista todos os usuários cadastrados."""
    db = get_db()
    usuarios = (
        db.query(Usuario)
        .order_by(Usuario.nivel, Usuario.username)
        .all()
    )
    # monta lista de dicts padronizada
    usuarios_list = [u.__dict__.copy() for u in usuarios]
    return render_template('visualizacoes/listar_usuarios.html', usuarios=usuarios_list)

@visualizacoes_bp.route('/alunos')
@login_required
def listar_alunos():
    """Lista todos os alunos cadastrados."""
    db = get_db()

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    search = request.args.get('search', '').strip()

    query = db.query(Aluno)
    if search:
        query = query.filter(or_(
            Aluno.nome.ilike(f'%{search}%'),
            Aluno.matricula.ilike(f'%{search}%')
        ))
    total = query.count()
    alunos = (
        query.order_by(Aluno.nome.asc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    total_pages = (total + per_page - 1) // per_page

    alunos_processados = []
    for a in alunos:
        aluno_dict = {c.name: getattr(a, c.name) for c in a.__table__.columns}
        telefones = aluno_dict.get('telefone', '').split(',') if aluno_dict.get('telefone') else []
        aluno_dict['telefone_1'] = telefones[0].strip() if len(telefones) > 0 else '-'
        aluno_dict['telefone_2'] = telefones[1].strip() if len(telefones) > 1 else '-'
        aluno_dict['telefone_3'] = telefones[2].strip() if len(telefones) > 2 else '-'
        alunos_processados.append(aluno_dict)

    return render_template('visualizacoes/listar_alunos.html',
       alunos=alunos_processados,
       page=page,
       total_pages=total_pages,
       search=search,
       is_admin=(str(session.get("nivel")) in ['1', '2'])
    )

@visualizacoes_bp.route('/visualizar_aluno/<int:aluno_id>')
@login_required
def visualizar_aluno(aluno_id):
    """Retorna JSON com dados do aluno (para modal/view)."""
    db = get_db()
    a = db.query(Aluno).filter_by(id=aluno_id).first()
    if a is None:
        return jsonify({'error': 'Aluno não encontrado'}), 404

    # Só pega campos primitivos, evita InstanceState e outros incompatíveis com JSON
    aluno_d = {}
    for k, v in a.__dict__.items():
        if k != '_sa_instance_state':
            aluno_d[k] = v
    
    # montar URL da foto se existir
    photo = aluno_d.get('photo') or aluno_d.get('foto') or aluno_d.get('arquivo_foto') or aluno_d.get('foto_filename') or None
    if photo:
        filename = os.path.basename(str(photo).replace('\\', '/'))
        aluno_d['photo_url'] = url_for('static', filename=f'uploads/alunos/{filename}')
    else:
        aluno_d['photo_url'] = None
    return jsonify({'aluno': aluno_d})


def _allowed_file(filename):
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@visualizacoes_bp.route('/upload_foto/<int:aluno_id>', methods=['POST'])
@login_required
def upload_foto(aluno_id):
    """
    Recebe upload de foto, salva no static/uploads/alunos e atualiza campo Aluno.photo.
    Nomeia como <matricula>_<slug_nome>.<ext>
    """
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado.'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Arquivo sem nome.'}), 400
    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Formato de arquivo não permitido.'}), 400

    import unicodedata, re
    def slugify(text, max_len=80):
        if not text:
            return 'aluno'
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
        if len(text) > max_len:
            text = text[:max_len].rstrip('_')
        return text or 'aluno'

    def gerar_nome_foto(matricula_or_id, nome, original_filename):
        ext = os.path.splitext(original_filename)[1].lower() or '.jpg'
        slug = slugify(nome)
        base = f"{matricula_or_id}_{slug}"
        from werkzeug.utils import secure_filename
        filename = f"{base}{ext}"
        return secure_filename(filename)

    db = get_db()
    a = db.query(Aluno).filter_by(id=aluno_id).first()
    if not a:
        return jsonify({'success': False, 'error': 'Aluno não encontrado.'}), 404
    matricula_or_id = str(getattr(a, 'matricula', None) or a.id)
    nome_para_slug = getattr(a, 'nome', '') or ''

    filename = gerar_nome_foto(matricula_or_id, nome_para_slug, file.filename)
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'alunos')
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, filename)

    try:
        file.save(save_path)
    except Exception:
        current_app.logger.exception('Falha ao salvar arquivo de foto')
        return jsonify({'success': False, 'error': 'Falha ao salvar arquivo.'}), 500

    try:
        a.photo = filename
        db.commit()
        return jsonify({'success': True, 'filename': filename})
    except Exception:
        db.rollback()
        current_app.logger.exception('Erro ao salvar referência de foto no banco')
        return jsonify({'success': False, 'error': 'Erro ao atualizar banco.'}), 500

@visualizacoes_bp.route('/excluir_aluno/<int:aluno_id>', methods=['POST'])
@admin_secundario_required
def excluir_aluno(aluno_id):
    """Exclui o aluno do banco (atenção: operação irreversível)."""
    db = get_db()
    try:
        aluno = db.query(Aluno).filter_by(id=aluno_id).first()
        if not aluno:
            flash(f'Aluno ID {aluno_id} não encontrado.', 'danger')
            return redirect(url_for('visualizacoes_bp.listar_alunos'))
        db.delete(aluno)
        db.commit()
        flash(f'Aluno ID {aluno_id} excluído com sucesso.', 'success')
    except Exception as e:
        db.rollback()
        current_app.logger.exception('Erro ao excluir aluno')
        flash(f'Erro ao excluir aluno: {e}', 'danger')
    return redirect(url_for('visualizacoes_bp.listar_alunos'))

@visualizacoes_bp.route('/alunos/excluir_selecionados', methods=['POST'])
@admin_secundario_required
def excluir_alunos_selecionados():
    """
    Endpoint AJAX para excluir vários alunos de uma só vez.
    Recebe JSON: { "ids": [1,2,3] }
    Retorna JSON: { "deleted": [ids], "errors": { "<id>": "mensagem" } }
    """
    db = get_db()
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or []
    deleted = []
    errors = {}

    if not isinstance(ids, (list, tuple)):
        return jsonify({"deleted": [], "errors": {"request": "Formato inválido para 'ids', deve ser lista"}}), 400

    norm_ids = []
    for v in ids:
        try:
            iv = int(v)
            if iv not in norm_ids:
                norm_ids.append(iv)
        except Exception:
            errors[str(v)] = "ID inválido"

    if not norm_ids:
        return jsonify({"deleted": [], "errors": errors}), 400

    try:
        for i in norm_ids:
            aluno = db.query(Aluno).filter_by(id=i).first()
            if not aluno:
                errors[str(i)] = "Registro não encontrado"
                continue
            try:
                db.delete(aluno)
                deleted.append(i)
            except Exception as e:
                db.rollback()
                current_app.logger.exception("Erro ao tentar excluir aluno %r", i)
                errors[str(i)] = str(e)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            current_app.logger.exception("Erro no commit da exclusão em massa")
            return jsonify({"deleted": deleted, "errors": {"commit": "Erro ao gravar alterações no banco: " + str(e)}}), 500

        return jsonify({"deleted": deleted, "errors": errors})
    except Exception as e:
        db.rollback()
        current_app.logger.exception("Erro inesperado em excluir_alunos_selecionados")
        return jsonify({"deleted": deleted, "errors": {"internal": str(e)}}), 500

# -------------- RFOs --------------

def _pick_field_from_obj(obj, candidates, default=''):
    """
    Retorna o primeiro campo presente no objeto (dict/model) entre os candidatos.
    """
    for c in candidates:
        val = getattr(obj, c, None)
        if val is not None:
            return val
        if isinstance(obj, dict) and c in obj and obj[c] is not None:
            return obj[c]
    return default

@visualizacoes_bp.route('/rfos')
@login_required
def listar_rfos():
    """
    Lista RFOs para visualização.
    """
    db = get_db()
    q_status = (request.args.get('status') or 'TRATADO').strip().upper()

    # Monta query ORM com os joins necessários para os campos nomeados
    query = (
        db.query(
            Ocorrencia,
            Aluno.matricula.label('matricula'),
            Aluno.nome.label('nome_aluno'),
            Aluno.serie.label('serie'),
            Aluno.turma.label('turma'),
            Usuario.username.label('registrado_por')
        )
        .outerjoin(Aluno, Aluno.id == Ocorrencia.aluno_id)
        .outerjoin(Usuario, Usuario.id == Ocorrencia.responsavel_registro_id)
    )

    if q_status in ['TRATADO', 'AGUARDANDO TRATAMENTO']:
        query = query.filter(Ocorrencia.status == q_status)
    elif q_status == 'TODOS' or not q_status:
        query = query.filter(Ocorrencia.status.in_(['TRATADO', 'AGUARDANDO TRATAMENTO']))
    else:
        query = query.filter(Ocorrencia.status == q_status)

    rows = query.order_by(Ocorrencia.data_ocorrencia.desc(), Ocorrencia.id.desc()).all()

    rfos = []
    for r in rows:
        # r = (Ocorrencia, matricula, nome_aluno, serie, turma, registrado_por)
        o = r[0]
        as_dict = o.__dict__.copy()
        # "falta_descricao": preferencialmente descricao_detalhada > relato_observador > ''
        falta_descricao = getattr(o, 'descricao_detalhada', None) or getattr(o, 'relato_observador', None) or ''
        rfos.append({
            'id': o.id,
            'rfo_id': getattr(o, 'rfo_id', None) or getattr(o, 'rfo', None) or getattr(o, 'codigo', None) or getattr(o, 'codigo_rfo', None) or f"RFO-{o.id}",
            'data_ocorrencia': getattr(o, 'data_ocorrencia', None) or getattr(o, 'data', None) or getattr(o, 'created_at', None),
            'matricula': r[1],
            'nome_aluno': r[2],
            'serie': r[3],
            'turma': r[4],
            'tipo_ocorrencia_nome': getattr(o, 'tipo_ocorrencia', None) or getattr(o, 'tipo', None) or getattr(o, 'natureza', None),
            'tipo_falta': getattr(o, 'tipo_falta', None) or getattr(o, 'gravidade', None) or getattr(o, 'nivel', None),
            'falta_descricao': falta_descricao,
            'responsavel_registro_username': r[5],
            'status': getattr(o, 'status', '') or '',
        })

    return render_template('visualizacoes/listar_rfos.html', rfos=rfos, status_filter=q_status)

from models_sqlalchemy import Ocorrencia, TAC, Aluno
from sqlalchemy import or_

@visualizacoes_bp.route('/rfo/<int:rfo_id>/cancel', methods=['POST'])
@admin_secundario_required
def cancelar_rfo(rfo_id):
    """Marca um RFO como CANCELADO. Fica visível na listagem com status CANCELADO."""
    db = get_db()
    try:
        rfo = db.query(Ocorrencia).filter_by(id=rfo_id).first()
        if rfo:
            rfo.status = 'CANCELADO'
            db.commit()
            return jsonify({'success': True, 'rfo_id': rfo_id})
        else:
            return jsonify({'success': False, 'message': 'RFO não encontrado'}), 404
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao cancelar RFO")
        return jsonify({'success': False, 'message': 'Erro ao cancelar RFO'}), 500

# Modelo auxiliar SQLAlchemy para removidos
from sqlalchemy import Column, Integer, Text, String, DateTime
from database import Base

class OcorrenciaRemovida(Base):
    __tablename__ = "ocorrencias_removidas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_id = Column(Integer)
    data = Column(Text)
    removed_at = Column(String(32))

@visualizacoes_bp.route('/limpar_lista', methods=['POST'])
@admin_secundario_required
def limpar_lista_rfos():
    """
    Move todas as ocorrências para ocorrencias_removidas (usando modelo),
    limpa a tabela ocorrencias (visualização) e reinicia sequência de autoincremento.
    """
    db = get_db()
    try:
        # criar tabela removida se ainda não existe (migrations recomendadas!)
        Base.metadata.create_all(db.get_bind(), tables=[OcorrenciaRemovida.__table__])
        rows = db.query(Ocorrencia).all()
        for r in rows:
            db.add(OcorrenciaRemovida(
                original_id=r.id,
                data=json.dumps(r.__dict__, default=str),
                removed_at=datetime.utcnow().isoformat()
            ))
        db.query(Ocorrencia).delete()
        db.commit()
        return jsonify({'success': True, 'moved': len(rows)})
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao limpar lista de RFOs")
        return jsonify({'success': False, 'message': 'Erro ao limpar lista'}), 500

@visualizacoes_bp.route('/removidos')
@admin_secundario_required
def listar_rfos_removidos():
    """
    Exibe os RFOs que foram removidos via 'Limpar Lista'.
    """
    db = get_db()
    try:
        Base.metadata.create_all(db.get_bind(), tables=[OcorrenciaRemovida.__table__])
        rows = db.query(OcorrenciaRemovida).order_by(OcorrenciaRemovida.removed_at.desc()).all()
        removed = []
        for r in rows:
            try:
                payload = json.loads(r.data)
            except Exception:
                payload = {'raw': r.data}
            removed.append({
                'id': r.id,
                'original_id': r.original_id,
                'removed_at': r.removed_at,
                'payload': payload
            })
        return render_template('visualizacoes/listar_rfos_removidos.html', removed=removed)
    except Exception:
        current_app.logger.exception("Erro ao listar RFOs removidos")
        return render_template('visualizacoes/listar_rfos_removidos.html', removed=[])

# ========================
# Listagem TAC no módulo Visualizações (com suporte a 'baixa' administrativo)
# ========================
@visualizacoes_bp.route('/tac')
@login_required
def tac_command():
    """
    Listagem de TACs dentro do módulo Visualizações.
    - Usuários veem apenas registros com baixa=0.
    - Admins podem ver também os baixados usando ?show_baixados=1
    """
    db = get_db()
    show_deleted = request.args.get('show_deleted') == '1'
    show_baixados = request.args.get('show_baixados') == '1' and is_admin()
    try:
        if show_deleted:
            tacs = db.query(TAC).order_by(TAC.created_at.desc()).all()
        elif show_baixados:
            tacs = db.query(TAC).order_by(TAC.created_at.desc()).all()
        else:
            tacs = db.query(TAC).filter(or_(TAC.baixa == 0, TAC.baixa == None), TAC.deleted == 0).order_by(TAC.created_at.desc()).all()

        tacs_lista = []
        for t in tacs:
            tdict = t.__dict__.copy()
            tdict['aluno_nome'] = None
            tdict['serie_turma'] = None
            if t.aluno_id:
                a = db.query(Aluno).filter_by(id=t.aluno_id).first()
                if a:
                    tdict['aluno_nome'] = a.nome
                    s = getattr(a, 'serie', None)
                    tur = getattr(a, 'turma', None)
                    tdict['serie_turma'] = f"{s or ''} {tur or ''}".strip()
            if not tdict.get('aluno_nome'):
                tdict['aluno_nome'] = tdict.get('escola_text') or '-'
            tacs_lista.append(tdict)

        return render_template('visualizacoes/listar_tacs.html', tacs=tacs_lista, show_deleted=show_deleted, show_baixados=show_baixados, is_admin=is_admin())
    except Exception:
        current_app.logger.exception("Erro ao listar TACS em visualizacoes/tac")
        return render_template('visualizacoes/listar_tacs.html', tacs=[], show_deleted=show_deleted, show_baixados=show_baixados, is_admin=is_admin())


@visualizacoes_bp.route('/tac/<int:id>/baixar', methods=['POST'])
@admin_secundario_required
def baixar_tac(id):
    db = get_db()
    try:
        tac = db.query(TAC).filter_by(id=id).first()
        if tac:
            tac.baixa = 1
            tac.updated_at = datetime.utcnow().isoformat()
            db.commit()
            flash('TAC baixado com sucesso.', 'success')
        else:
            flash('TAC não encontrado.', 'danger')
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao baixar TAC")
        flash('Erro ao baixar TAC.', 'danger')
    return redirect(request.referrer or url_for('visualizacoes_bp.tac_command'))

from models_sqlalchemy import TAC, FichaMedidaDisciplinar, Aluno

@visualizacoes_bp.route('/tac/<int:id>/reativar', methods=['POST'])
@admin_secundario_required
def reativar_tac(id):
    db = get_db()
    try:
        tac = db.query(TAC).filter_by(id=id).first()
        if tac:
            tac.baixa = 0
            tac.updated_at = datetime.utcnow().isoformat()
            db.commit()
            flash('TAC reativado com sucesso.', 'success')
        else:
            flash('TAC não encontrado.', 'danger')
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao reativar TAC")
        flash('Erro ao reativar TAC.', 'danger')
    return redirect(request.referrer or url_for('visualizacoes_bp.tac_command'))

def is_admin():
    return str(session.get("nivel")) in ["1", "2"]

@visualizacoes_bp.route('/fmds')
def listar_fmds():
    """
    Lista FMDs para visualização. Usuários veem por padrão apenas FMDs não baixadas (baixa='0').
    Se show_baixados=1 nos args, mostra todas.
    """
    db = get_db()
    show_baixados = request.args.get('show_baixados') == '1'
    try:
        fmd_query = db.query(
            FichaMedidaDisciplinar,
            Aluno.matricula.label('aluno_matricula'),
            Aluno.nome.label('aluno_nome'),
            Aluno.serie,
            Aluno.turma
        ).outerjoin(Aluno, Aluno.id == FichaMedidaDisciplinar.aluno_id)
        if not show_baixados:
            # Corrigi comparação, agora verifica como string
            fmd_query = fmd_query.filter((FichaMedidaDisciplinar.baixa == '0') | (FichaMedidaDisciplinar.baixa == None))
        rows = fmd_query.order_by(
            FichaMedidaDisciplinar.data_fmd.desc().nullslast(),
            FichaMedidaDisciplinar.created_at.desc()
        ).all()
        fmds = []
        for r in rows:
            f, matricula, nome, serie, turma = r
            d = f.__dict__.copy()
            d['aluno_matricula'] = matricula
            d['aluno_nome'] = nome
            d['serie'] = serie
            d['turma'] = turma
            fmds.append(d)
        return render_template('visualizacoes/listar_fmd.html', fmds=fmds, show_baixados=show_baixados, is_admin=is_admin())
    except Exception:
        current_app.logger.exception("Erro ao listar FMDs")
        return render_template('visualizacoes/listar_fmd.html', fmds=[], show_baixados=show_baixados, is_admin=is_admin())

@visualizacoes_bp.route('/fmd/<int:id>/baixar', methods=['POST'])
@admin_secundario_required
def baixar_fmd(id):
    db = get_db()
    try:
        fmd = db.query(FichaMedidaDisciplinar).filter_by(id=id).first()
        if fmd:
            fmd.baixa = 1
            fmd.updated_at = datetime.utcnow().isoformat()
            db.commit()
            flash('FMD baixada com sucesso.', 'success')
        else:
            flash('FMD não encontrada.', 'danger')
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao baixar FMD")
        flash('Erro ao baixar FMD.', 'danger')
    return redirect(request.referrer or url_for('visualizacoes_bp.listar_fmds'))

@visualizacoes_bp.route('/fmd/<int:id>/reativar', methods=['POST'])
@admin_secundario_required
def reativar_fmd(id):
    db = get_db()
    try:
        fmd = db.query(FichaMedidaDisciplinar).filter_by(id=id).first()
        if fmd:
            fmd.baixa = 0
            fmd.updated_at = datetime.utcnow().isoformat()
            db.commit()
            flash('FMD reativada com sucesso.', 'success')
        else:
            flash('FMD não encontrada.', 'danger')
    except Exception:
        db.rollback()
        current_app.logger.exception("Erro ao reativar FMD")
        flash('Erro ao reativar FMD.', 'danger')
    return redirect(request.referrer or url_for('visualizacoes_bp.listar_fmds'))

from models_sqlalchemy import Ata, Aluno, Cabecalho
from database import get_db

@visualizacoes_bp.route("/ata/<int:ata_id>/pdf")
def ata_pdf(ata_id):
    """
    Gera PDF da ATA usando o template visualizacoes/ata_print.html.
    Monta todos os detalhes relevantes da ata e cabeçalho!
    """
    import io
    import re
    import json
    from flask import render_template, send_file, jsonify, request, url_for
    from datetime import datetime, date
    # Se possível, deixe essas funções auxiliares fora da view em versão final!
    import pdfkit

    def generate_pdf_bytes(html):
        # O pdfkit precisa do wkhtmltopdf instalado
        # Adapte conforme configuração local/desejada
        return pdfkit.from_string(html, False)

    def num_to_words_pt(n):
        units = {0:"zero",1:"um",2:"dois",3:"três",4:"quatro",5:"cinco",6:"seis",7:"sete",8:"oito",9:"nove",
                10:"dez",11:"onze",12:"doze",13:"treze",14:"quatorze",15:"quinze",16:"dezesseis",17:"dezessete",18:"dezoito",19:"dezenove"}
        tens = {20:"vinte",30:"trinta",40:"quarenta",50:"cinquenta",60:"sessenta",70:"setenta",80:"oitenta",90:"noventa"}
        hundreds = {100:"cem",200:"duzentos",300:"trezentos",400:"quatrocentos",500:"quinhentos",600:"seiscentos",700:"setecentos",800:"oitocentos",900:"novecentos"}
        if n < 0:
            return "menos " + num_to_words_pt(-n)
        if n < 20:
            return units[n]
        if n < 100:
            t = (n // 10) * 10
            r = n % 10
            if r == 0:
                return tens[t]
            return tens[t] + " e " + units[r]
        if n < 1000:
            h = (n // 100) * 100
            r = n % 100
            if n == 100:
                return "cem"
            prefix = hundreds.get(h, "")
            if r == 0:
                return prefix
            return prefix + " e " + num_to_words_pt(r)
        if n < 10000:
            mil = n // 1000
            r = n % 1000
            if mil == 1:
                prefix = "mil"
            else:
                prefix = num_to_words_pt(mil) + " mil"
            if r == 0:
                return prefix
            if r < 100:
                return prefix + " e " + num_to_words_pt(r)
            return prefix + " " + num_to_words_pt(r)
        return str(n)

    def date_to_extenso(dt):
        if not dt:
            return ""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                try:
                    from dateutil import parser as _parser
                    dt = _parser.parse(dt)
                except Exception:
                    return dt
        if isinstance(dt, datetime):
            dt = dt.date()
        meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
        dia = dt.day
        mes = meses[dt.month - 1]
        ano_words = num_to_words_pt(dt.year)
        dia_words = num_to_words_pt(dia)
        dia_label = "dia" if dia == 1 else "dias"
        return f"{dia_words} {dia_label} do mês de {mes} do ano de {ano_words}"

    try:
        db = get_db()
        ata_obj = db.query(Ata).filter_by(id=ata_id).first()
        if not ata_obj:
            return jsonify({"error": "ATA não encontrada."}), 404
        ata = ata_obj.__dict__.copy()

        # desserializar participants_json se for string
        participants = []
        try:
            val = ata.get("participants_json")
            if isinstance(val, str) and val.strip():
                participants = json.loads(val)
                ata["participants_json"] = participants
            elif isinstance(val, list):
                participants = val
        except Exception:
            ata["participants_json"] = participants

        # Aluno/reponsável
        aluno_id = ata.get("aluno_id")
        if aluno_id:
            a = db.query(Aluno).filter_by(id=aluno_id).first()
            if a:
                ata["aluno"] = a.__dict__.copy()
                if not ata.get("responsavel"):
                    for k in ("responsavel", "responsavel_nome", "nome_responsavel"):
                        val = getattr(a, k, None)
                        if val:
                            ata["responsavel"] = val
                            break

        # Cabeçalho da escola
        cabecalho = {"estado":"", "secretaria":"", "coordenacao":"", "escola":"", "logo_url":""}
        cab_obj = None
        try:
            cab_obj = db.query(Cabecalho).order_by(Cabecalho.id.desc()).first()
        except Exception:
            cab_obj = None
        if cab_obj:
            cabd = cab_obj.__dict__.copy()
            for k in ("estado", "secretaria", "coordenacao", "escola"):
                if cabd.get(k): cabecalho[k] = cabd[k]
            logo_fn = cabd.get('logo_estado') or cabd.get('logo')
            if logo_fn:
                try:
                    cabecalho['logo_url'] = url_for('static', filename=f'uploads/cabecalhos/{logo_fn}')
                except Exception:
                    cabecalho['logo_url'] = f'/static/uploads/cabecalhos/{logo_fn}'

        # Garante responsável na participants_json sem duplicidade
        try:
            parts = ata.get("participants_json") or []
            resp = ata.get("responsavel")
            if resp:
                resp = resp.strip()
                found = False
                for p in parts:
                    pname = (p.get('name') or p.get('nome') or "") if isinstance(p, dict) else ""
                    if pname and pname.strip() == resp:
                        found = True
                        break
                if not found:
                    if len(parts) >= 3:
                        parts.insert(3, {"nome": resp, "cargo": "Responsável"})
                    else:
                        parts.append({"nome": resp, "cargo": "Responsável"})
                ata["participants_json"] = parts
        except Exception:
            pass

        # Data por extenso: pega campo ou calcula via fallback
        ata_date = None
        if ata.get("data_extenso") and isinstance(ata.get("data_extenso"), str) and ata.get("data_extenso").strip():
            ata["data_extenso_extenso"] = ata.get("data_extenso")
        else:
            for k in ("data", "data_ata", "data_reuniao", "created_at"):
                if ata.get(k):
                    ata_date = ata.get(k)
                    break
            if not ata_date and all(ata.get(f) for f in ("ano", "mes", "dia")):
                try:
                    ata_date = date(int(ata.get("ano")), int(ata.get("mes")), int(ata.get("dia")))
                except Exception:
                    ata_date = None
            ata["data_extenso_extenso"] = date_to_extenso(ata_date) if ata_date else (ata.get("data_extenso") or "")

        # Diretor em dados_escola ou cabecalho
        diretor_nome = None
        try:
            diretor_nome = cabecalho.get("diretor")
        except Exception:
            pass

        # logo_data/arquivo via helper
        logo_data, logo_file = _get_logo_data_and_file(cabecalho)
        cabecalho["logo_file"] = cabecalho.get("logo_file") or logo_file

        # build assinaturas (deduplicando)
        def _normalize_participant(p):
            if isinstance(p, dict):
                name = p.get('nome') or p.get('name') or p.get('nome_completo') or ""
                role = p.get('cargo') or p.get('role') or ""
                return {'nome': (name or "").strip(), 'cargo': (role or "").strip()}
            else:
                return {'nome': str(p).strip(), 'cargo': ''}
        parts = ata.get("participants_json") or []
        assinaturas = []
        try:
            for p in parts:
                np = _normalize_participant(p)
                if np['nome']:
                    assinaturas.append(np)
        except Exception:
            assinaturas = []

        if diretor_nome and not any(a['nome'].strip().lower() == diretor_nome.strip().lower() for a in assinaturas):
            assinaturas.append({'nome': diretor_nome, 'cargo': 'Diretor'})
        resp = ata.get("responsavel")
        if resp and not any(a['nome'].strip().lower() == resp.strip().lower() for a in assinaturas):
            assinaturas.append({'nome': resp, 'cargo': 'Responsável'})

        html = render_template("visualizacoes/ata_print.html",
            ata=ata, ata_id=ata_id, cabecalho=cabecalho,
            diretor_nome=diretor_nome,
            logo_file=cabecalho.get("logo_file"), logo_data=logo_data
        )

        base = request.url_root.rstrip('/')
        if re.search(r'(?i)<head\b', html):
            html = re.sub(r'(?i)(<head\b[^>]*>)', r'\1<base href="' + base + '">', html, count=1)
        else:
            html = '<base href="' + base + '">' + html

        pdfbytes = generate_pdf_bytes(html)
    except Exception as e:
        return jsonify({"error": "Erro ao gerar PDF: " + str(e)}), 500

    return send_file(io.BytesIO(pdfbytes),
                     mimetype="application/pdf",
                     as_attachment=False,
                     download_name=f"ata_{ata_id}.pdf")