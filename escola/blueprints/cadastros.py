from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database import get_db
from models_sqlalchemy import FaltaDisciplinar, Elogio, Cabecalho, DadosEscola  # use os modelos necessários em cada rota!
from .utils import login_required, admin_secundario_required
import re

cadastros_bp = Blueprint('cadastros_bp', __name__)

# Rota unificada: Dados Disciplinares (apenas renderiza o template com abas)
@cadastros_bp.route('/dados_disciplinares')
@admin_secundario_required
def dados_disciplinares():
    """
    Página que conterá 3 abas:
      - Faltas Disciplinares
      - Elogios
      - Bimestres
    O template carregará o conteúdo de cada aba via AJAX (partials) para reaproveitar
    exatamente as listagens existentes sem recarregar o layout principal.
    """
    return render_template('cadastros/dados_disciplinares.html')

@cadastros_bp.route('/faltas')
@admin_secundario_required
def listar_faltas():
    """Lista todas as faltas disciplinares cadastradas."""
    db = get_db()
    faltas = db.query(FaltaDisciplinar).order_by(FaltaDisciplinar.id.asc()).all()
    return render_template('cadastros/listar_faltas.html', faltas=faltas)

@cadastros_bp.route('/faltas/adicionar', methods=['GET', 'POST'])
@admin_secundario_required
def adicionar_falta():
    """Adiciona uma nova falta disciplinar."""
    if request.method == 'POST':
        natureza = request.form.get('natureza', '').strip()
        descricao = request.form.get('descricao', '').strip()
        
        error = None
        if not natureza:
            error = 'A natureza da falta é obrigatória.'
        elif not descricao:
            error = 'A descrição da falta é obrigatória.'
        
        if error is None:
            db = get_db()
            try:
                falta = FaltaDisciplinar(natureza=natureza, descricao=descricao)
                db.add(falta)
                db.commit()
                flash(f'Falta disciplinar cadastrada com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_faltas'))
            except Exception as e:
                db.rollback()
                error = f'Erro ao cadastrar falta: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/adicionar_falta.html')

@cadastros_bp.route('/faltas/editar/<int:falta_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_falta(falta_id):
    """Edita uma falta disciplinar."""
    db = get_db()
    falta = db.query(FaltaDisciplinar).filter_by(id=falta_id).first()

    if falta is None:
        flash('Falta não encontrada.', 'danger')
        return redirect(url_for('cadastros_bp.listar_faltas'))
    
    if request.method == 'POST':
        natureza = request.form.get('natureza', '').strip()
        descricao = request.form.get('descricao', '').strip()

        error = None
        if not natureza:
            error = 'A natureza da falta é obrigatória.'
        elif not descricao:
            error = 'A descrição da falta é obrigatória.'

        if error is None:
            try:
                falta.natureza = natureza
                falta.descricao = descricao
                db.commit()
                flash('Falta disciplinar atualizada com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_faltas'))
            except Exception as e:
                db.rollback()
                error = f'Erro ao atualizar falta: {e}'

        flash(error, 'danger')

    return render_template('cadastros/editar_falta.html', falta=falta)

@cadastros_bp.route('/faltas/excluir/<int:falta_id>', methods=['POST'])
@admin_secundario_required
def excluir_falta(falta_id):
    """Exclui uma falta disciplinar."""
    db = get_db()
    try:
        falta = db.query(FaltaDisciplinar).filter_by(id=falta_id).first()
        if falta:
            db.delete(falta)
            db.commit()
            flash('Falta disciplinar excluída com sucesso.', 'success')
        else:
            flash('Falta não encontrada.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir falta: {e}', 'danger')
    
    return redirect(url_for('cadastros_bp.listar_faltas'))

@cadastros_bp.route('/elogios')
@admin_secundario_required
def listar_elogios():
    """Lista todos os elogios cadastrados."""
    db = get_db()
    elogios = db.query(Elogio).order_by(Elogio.tipo, Elogio.descricao).all()
    return render_template('cadastros/listar_elogios.html', elogios=elogios)

@cadastros_bp.route('/elogios/adicionar', methods=['GET', 'POST'])
@admin_secundario_required
def adicionar_elogio():
    """Adiciona um novo elogio."""
    if request.method == 'POST':
        tipo = request.form.get('tipo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        
        error = None
        if not tipo:
            error = 'O tipo de elogio é obrigatório.'
        elif not descricao:
            error = 'A descrição do elogio é obrigatória.'
        
        if error is None:
            db = get_db()
            try:
                elogio = Elogio(tipo=tipo, descricao=descricao)
                db.add(elogio)
                db.commit()
                flash(f'Elogio cadastrado com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_elogios'))
            except Exception as e:
                db.rollback()
                error = f'Erro ao cadastrar elogio: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/adicionar_elogio.html')

@cadastros_bp.route('/elogios/editar/<int:elogio_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_elogio(elogio_id):
    """Edita um elogio."""
    db = get_db()
    elogio = db.query(Elogio).filter_by(id=elogio_id).first()
    
    if elogio is None:
        flash('Elogio não encontrado.', 'danger')
        return redirect(url_for('cadastros_bp.listar_elogios'))
    
    if request.method == 'POST':
        tipo = request.form.get('tipo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        
        error = None
        if not tipo:
            error = 'O tipo de elogio é obrigatório.'
        elif not descricao:
            error = 'A descrição do elogio é obrigatória.'
        
        if error is None:
            try:
                elogio.tipo = tipo
                elogio.descricao = descricao
                db.commit()
                flash('Elogio atualizado com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_elogios'))
            except Exception as e:
                db.rollback()
                error = f'Erro ao atualizar elogio: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/editar_elogio.html', elogio=elogio)

@cadastros_bp.route('/elogios/excluir/<int:elogio_id>', methods=['POST'])
@admin_secundario_required
def excluir_elogio(elogio_id):
    """Exclui um elogio.""" 
    db = get_db()
    try:
        elogio = db.query(Elogio).filter_by(id=elogio_id).first()
        if elogio:
            db.delete(elogio)
            db.commit()
            flash('Elogio excluído com sucesso.', 'success')
        else:
            flash('Elogio não encontrado.', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir elogio: {e}', 'danger')
    
    return redirect(url_for('cadastros_bp.listar_elogios'))

from flask import current_app
from werkzeug.utils import secure_filename
from database import get_db  # AJUSTAR IMPORT
from datetime import datetime
import os

# Configurações locais
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_SUBDIR = os.path.join('static', 'uploads', 'cabecalhos')

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def _ensure_upload_dir():
    upload_dir = os.path.join(current_app.root_path, UPLOAD_SUBDIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

# Substitua apenas a função listar_cabecalhos por esta versão no arquivo blueprints/cadastros.py

@cadastros_bp.route('/cabecalho/listar')
def listar_cabecalhos():
    db = get_db()
    cabecalhos = db.query(Cabecalho).order_by(Cabecalho.id.desc()).all()
    # montar url completo para imagens
    for c in cabecalhos:
        c.logo_estado_url = url_for('static', filename=f'uploads/cabecalhos/{c.logo_estado}') if c.logo_estado else None
        c.logo_escola_url = url_for('static', filename=f'uploads/cabecalhos/{c.logo_escola}') if c.logo_escola else None
        c.logo_prefeitura_url = url_for('static', filename=f'uploads/cabecalhos/{c.logo_prefeitura}') if getattr(c, "logo_prefeitura", None) else None
    return render_template('cadastros/listar_cabecalho.html', cabecalhos=cabecalhos)

@cadastros_bp.route('/cabecalho/novo', methods=['GET', 'POST'])
def cabecalho_novo():
    db = get_db()
    if request.method == 'POST':
        estado = request.form.get('estado', '').strip()
        secretaria = request.form.get('secretaria', '').strip()
        coordenacao = request.form.get('coordenacao', '').strip()
        escola = request.form.get('escola', '').strip()

        logo_estado_filename = None
        logo_escola_filename = None
        logo_prefeitura_filename = None

        upload_dir = _ensure_upload_dir()

        # processar logo_estado
        if 'logo_estado' in request.files:
            f = request.files['logo_estado']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_estado_filename = f"estado_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_estado_filename))

        # processar logo_prefeitura
        if 'logo_prefeitura' in request.files:
            f = request.files['logo_prefeitura']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_prefeitura_filename = f"prefeitura_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_prefeitura_filename))

        # processar logo_escola
        if 'logo_escola' in request.files:
            f = request.files['logo_escola']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_escola_filename = f"escola_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_escola_filename))

        try:
            cabecalho = Cabecalho(
                estado=estado,
                secretaria=secretaria,
                coordenacao=coordenacao,
                escola=escola,
                logo_estado=logo_estado_filename,
                logo_escola=logo_escola_filename,
                logo_prefeitura=logo_prefeitura_filename,
                created_at=datetime.utcnow().isoformat()
            )
            db.add(cabecalho)
            db.commit()
            flash('Cabeçalho salvo com sucesso.', 'success')
            return redirect(url_for('cadastros_bp.listar_cabecalhos'))
        except Exception as e:
            db.rollback()
            current_app.logger.exception('Erro ao salvar cabeçalho')
            flash('Erro ao salvar cabeçalho.', 'danger')
            return redirect(url_for('cadastros_bp.cabecalho_novo'))

    # GET
    return render_template('cadastros/cabecalho_form.html', cabecalho=None)

@cadastros_bp.route('/cabecalho/editar/<int:id>', methods=['GET', 'POST'])
def cabecalho_editar(id):
    db = get_db()
    cabecalho = db.query(Cabecalho).filter_by(id=id).first()
    if cabecalho is None:
        flash('Cabeçalho não encontrado.', 'danger')
        return redirect(url_for('cadastros_bp.listar_cabecalhos'))

    if request.method == 'POST':
        estado = request.form.get('estado', '').strip()
        secretaria = request.form.get('secretaria', '').strip()
        coordenacao = request.form.get('coordenacao', '').strip()
        escola = request.form.get('escola', '').strip()

        upload_dir = _ensure_upload_dir()

        # processar logo_estado
        if 'logo_estado' in request.files:
            f = request.files['logo_estado']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_estado_filename = f"estado_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_estado_filename))
                # remover anterior se existir
                if cabecalho.logo_estado:
                    try:
                        os.remove(os.path.join(upload_dir, cabecalho.logo_estado))
                    except Exception:
                        pass
                cabecalho.logo_estado = logo_estado_filename

        # processar logo_prefeitura
        if 'logo_prefeitura' in request.files:
            f = request.files['logo_prefeitura']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_prefeitura_filename = f"prefeitura_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_prefeitura_filename))
                # remover anterior se existir
                if cabecalho.logo_prefeitura:
                    try:
                        os.remove(os.path.join(upload_dir, cabecalho.logo_prefeitura))
                    except Exception:
                        pass
                cabecalho.logo_prefeitura = logo_prefeitura_filename

        # processar logo_escola
        if 'logo_escola' in request.files:
            f = request.files['logo_escola']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_escola_filename = f"escola_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_escola_filename))
                # remover anterior se existir
                if cabecalho.logo_escola:
                    try:
                        os.remove(os.path.join(upload_dir, cabecalho.logo_escola))
                    except Exception:
                        pass
                cabecalho.logo_escola = logo_escola_filename

        # Atualizar campos de texto
        cabecalho.estado = estado
        cabecalho.secretaria = secretaria
        cabecalho.coordenacao = coordenacao
        cabecalho.escola = escola

        try:
            db.commit()
            flash('Cabeçalho atualizado com sucesso.', 'success')
            return redirect(url_for('cadastros_bp.listar_cabecalhos'))
        except Exception as e:
            db.rollback()
            current_app.logger.exception('Erro ao atualizar cabeçalho')
            flash('Erro ao atualizar cabeçalho.', 'danger')
            return redirect(url_for('cadastros_bp.cabecalho_editar', id=id))

    # GET: montar urls de imagens
    cabecalho_dict = {
        "id": cabecalho.id,
        "estado": cabecalho.estado,
        "secretaria": cabecalho.secretaria,
        "coordenacao": cabecalho.coordenacao,
        "escola": cabecalho.escola,
        "logo_estado": cabecalho.logo_estado,
        "logo_escola": cabecalho.logo_escola,
        "logo_prefeitura": getattr(cabecalho, "logo_prefeitura", None),
        "logo_estado_url": url_for('static', filename=f'uploads/cabecalhos/{cabecalho.logo_estado}') if cabecalho.logo_estado else None,
        "logo_escola_url": url_for('static', filename=f'uploads/cabecalhos/{cabecalho.logo_escola}') if cabecalho.logo_escola else None,
        "logo_prefeitura_url": url_for('static', filename=f'uploads/cabecalhos/{cabecalho.logo_prefeitura}') if getattr(cabecalho, "logo_prefeitura", None) else None
    }

    return render_template('cadastros/cabecalho_form.html', cabecalho=cabecalho_dict)

@cadastros_bp.route('/cabecalho/excluir/<int:id>', methods=['POST'])
def cabecalho_excluir(id):
    db = get_db()
    cabecalho = db.query(Cabecalho).filter_by(id=id).first()
    if cabecalho:
        try:
            # remover arquivos associados
            upload_dir = _ensure_upload_dir()
            if cabecalho.logo_estado:
                try:
                    os.remove(os.path.join(upload_dir, cabecalho.logo_estado))
                except Exception:
                    pass
            if cabecalho.logo_escola:
                try:
                    os.remove(os.path.join(upload_dir, cabecalho.logo_escola))
                except Exception:
                    pass
            if getattr(cabecalho, 'logo_prefeitura', None):
                try:
                    os.remove(os.path.join(upload_dir, cabecalho.logo_prefeitura))
                except Exception:
                    pass
            db.delete(cabecalho)
            db.commit()
            flash('Cabeçalho excluído.', 'success')
        except Exception:
            db.rollback()
            current_app.logger.exception('Erro ao excluir cabeçalho')
            flash('Erro ao excluir cabeçalho.', 'danger')
    else:
        flash('Cabeçalho não encontrado.', 'warning')
    return redirect(url_for('cadastros_bp.listar_cabecalhos'))

# --- INÍCIO BLOCO DADOS_ESCOLA ---
from flask import jsonify
# endpoints para Dados da Escola

# Adicione esta função em blueprints/cadastros.py (por exemplo logo após listar_dados_escola / listar_cabecalhos)
@cadastros_bp.route('/dados_documentos')
@admin_secundario_required
def dados_documentos():
    """Página unificada Dados Escolar / Documentos com 3 abas (Dados Escola, Novo Cabeçalho, Cabeçalho Documentos)."""
    db = get_db()

    # carregar cabecalhos
    cabecalhos = db.query(Cabecalho).order_by(Cabecalho.id.desc()).all()
    for c in cabecalhos:
        c.logo_estado_url = url_for('static', filename=f'uploads/cabecalhos/{c.logo_estado}') if c.logo_estado else None
        c.logo_escola_url = url_for('static', filename=f'uploads/cabecalhos/{c.logo_escola}') if c.logo_escola else None
        c.logo_prefeitura_url = url_for('static', filename=f'uploads/cabecalhos/{c.logo_prefeitura}') if getattr(c, 'logo_prefeitura', None) else None

    # carregar dados da escola
    dados = db.query(DadosEscola).order_by(DadosEscola.id.desc()).all()
    for d in dados:
        if d.cabecalho_id:
            ch = db.query(Cabecalho).filter_by(id=d.cabecalho_id).first()
            d.escola_origem = ch.escola if ch else None
        else:
            d.escola_origem = None

    return render_template('cadastros/dados_documentos.html',
                           cabecalhos=cabecalhos,
                           dados=dados,
                           cabecalho=None)

@cadastros_bp.route('/dados_escola')
@admin_secundario_required
def listar_dados_escola():
    """Listagem de Dados da Escola"""
    db = get_db()
    dados = db.query(DadosEscola).order_by(DadosEscola.id.desc()).all()
    for d in dados:
        if d.cabecalho_id:
            ch = db.query(Cabecalho).filter_by(id=d.cabecalho_id).first()
            d.escola_origem = ch.escola if ch else None
        else:
            d.escola_origem = None
    return render_template('cadastros/listar_dados_escola.html', dados=dados)

@cadastros_bp.route('/dados_escola/novo', methods=['GET', 'POST'])
@admin_secundario_required
def dados_escola_novo():
    db = get_db()
    telefone = request.form.get('telefone', '').strip()
    if request.method == 'POST':
        cabecalho_id = request.form.get('cabecalho_id') or None
        escola = request.form.get('escola','').strip()
        rua = request.form.get('rua','').strip()
        numero = request.form.get('numero','').strip()
        complemento = request.form.get('complemento','').strip()
        bairro = request.form.get('bairro','').strip()
        cidade = request.form.get('cidade','').strip()
        # normalizar e validar estado (sigla)
        estado_raw = request.form.get('estado','').strip()
        estado_norm = re.sub(r'[^A-Za-z]', '', estado_raw).upper()[:2] if estado_raw else ''
        if estado_raw and len(estado_norm) != 2:
            flash('Informe a sigla do Estado com 2 letras (ex: MT).', 'danger')
            return redirect(url_for('cadastros_bp.dados_escola_novo'))
        estado = estado_norm

        cep = request.form.get('cep','').strip()
        cnpj = request.form.get('cnpj','').strip()
        diretor_nome = request.form.get('diretor_nome','').strip()
        diretor_cpf = request.form.get('diretor_cpf','').strip()
        email_remetente = request.form.get('email_remetente','').strip()
        senha_email_app = request.form.get('senha_email_app','').strip()
        dominio_sistema = request.form.get('dominio_sistema','').strip()

        try:
            dados_escola = DadosEscola(
                cabecalho_id=cabecalho_id,
                escola=escola,
                rua=rua,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                cidade=cidade,
                estado=estado,
                cep=cep,
                cnpj=cnpj,
                diretor_nome=diretor_nome,
                diretor_cpf=diretor_cpf,
                email_remetente=email_remetente,
                senha_email_app=senha_email_app,
                dominio_sistema=dominio_sistema,
                telefone=telefone
            )
            db.add(dados_escola)
            db.commit()
            flash('Dados da Escola salvos.', 'success')
            return redirect(url_for('cadastros_bp.listar_dados_escola'))
        except Exception:
            db.rollback()
            current_app.logger.exception('Erro ao salvar dados da escola')
            flash('Erro ao salvar dados da escola.', 'danger')
            return redirect(url_for('cadastros_bp.dados_escola_novo'))

    # GET: apenas renderizar formulário vazio
    return render_template('cadastros/dados_escola_form.html', dados=None)

@cadastros_bp.route('/dados_escola/editar/<int:id>', methods=['GET', 'POST'])
@admin_secundario_required
def dados_escola_editar(id):
    db = get_db()
    telefone = request.form.get('telefone', '').strip()
    dados = db.query(DadosEscola).filter_by(id=id).first()
    if not dados:
        flash('Registro não encontrado.', 'warning')
        return redirect(url_for('cadastros_bp.listar_dados_escola'))

    if request.method == 'POST':
        cabecalho_id = request.form.get('cabecalho_id') or None
        escola = request.form.get('escola', '').strip()
        rua = request.form.get('rua', '').strip()
        numero = request.form.get('numero', '').strip()
        complemento = request.form.get('complemento', '').strip()
        bairro = request.form.get('bairro', '').strip()
        cidade = request.form.get('cidade', '').strip()
        # normalizar e validar estado (sigla)
        estado_raw = request.form.get('estado','').strip()
        estado_norm = re.sub(r'[^A-Za-z]', '', estado_raw).upper()[:2] if estado_raw else ''
        if estado_raw and len(estado_norm) != 2:
            flash('Informe a sigla do Estado com 2 letras (ex: MT).', 'danger')
            return redirect(url_for('cadastros_bp.dados_escola_editar', id=id))
        estado = estado_norm

        cep = request.form.get('cep', '').strip()
        cnpj = request.form.get('cnpj', '').strip()
        diretor_nome = request.form.get('diretor_nome', '').strip()
        diretor_cpf = request.form.get('diretor_cpf', '').strip()
        email_remetente = request.form.get('email_remetente', '').strip()
        senha_email_app = request.form.get('senha_email_app', '').strip()
        dominio_sistema = request.form.get('dominio_sistema', '').strip()

        try:
            dados.cabecalho_id = cabecalho_id
            dados.escola = escola
            dados.rua = rua
            dados.numero = numero
            dados.complemento = complemento
            dados.bairro = bairro
            dados.cidade = cidade
            dados.estado = estado
            dados.cep = cep
            dados.cnpj = cnpj
            dados.diretor_nome = diretor_nome
            dados.diretor_cpf = diretor_cpf
            dados.email_remetente = email_remetente
            dados.senha_email_app = senha_email_app
            dados.dominio_sistema = dominio_sistema
            dados.telefone = telefone

            db.commit()
            flash('Dados da Escola atualizados.', 'success')
            return redirect(url_for('cadastros_bp.listar_dados_escola'))
        except Exception:
            db.rollback()
            current_app.logger.exception('Erro ao atualizar dados da escola')
            flash('Erro ao atualizar dados da escola.', 'danger')
            return redirect(url_for('cadastros_bp.dados_escola_editar', id=id))

    # GET: renderizar com dados preenchidos
    return render_template('cadastros/dados_escola_form.html', dados=dados)

@cadastros_bp.route('/dados_escola/excluir/<int:id>', methods=['POST'])
@admin_secundario_required
def dados_escola_excluir(id):
    db = get_db()
    try:
        dados = db.query(DadosEscola).filter_by(id=id).first()
        if dados:
            db.delete(dados)
            db.commit()
            flash('Registro excluído.', 'success')
        else:
            flash('Registro não encontrado.', 'danger')
    except Exception:
        db.rollback()
        current_app.logger.exception('Erro ao excluir dados da escola')
        flash('Erro ao excluir registro.', 'danger')
    return redirect(url_for('cadastros_bp.listar_dados_escola'))

# API: autocomplete puxando da tabela cabecalhos (campo escola)
@cadastros_bp.route('/api/cabecalhos_autocomplete')
def cabecalhos_autocomplete():
    q = request.args.get('q', '').strip()
    db = get_db()
    if not q:
        results_qs = db.query(Cabecalho).order_by(Cabecalho.id.desc()).limit(30).all()
    else:
        qlike = f"%{q.upper()}%"
        results_qs = db.query(Cabecalho).filter(Cabecalho.escola.ilike(qlike)).order_by(Cabecalho.escola).limit(30).all()
    results = [{'id': c.id, 'escola': c.escola} for c in results_qs]
    return jsonify(results)

# API: obter cabecalho por id (para popular endereço quando usuário escolher)
@cadastros_bp.route('/api/cabecalho')
def cabecalho_by_id():
    cid = request.args.get('id')
    db = get_db()
    if not cid:
        return jsonify({'error': 'missing id'}), 400
    cabecalho = db.query(Cabecalho).filter_by(id=cid).first()
    if not cabecalho:
        return jsonify({'error': 'not found'}), 404
    # Converte objeto SQLAlchemy para dict
    rd = {c.name: getattr(cabecalho, c.name) for c in Cabecalho.__table__.columns}
    return jsonify(rd)

# [adicione este trecho ao final do arquivo blueprints/cadastros.py]
from flask import jsonify, request
from database import get_db
# ... (se já tiver essas importações no topo do arquivo, ignore duplicates)

@cadastros_bp.route('/api/dados_escola_by_cabecalho')
def api_dados_escola_by_cabecalho():
    cid = request.args.get('cabecalho_id') or request.args.get('id')
    if not cid:
        return jsonify({'error': 'missing cabecalho_id'}), 400
    db = get_db()
    try:
        dados = db.query(DadosEscola).filter_by(cabecalho_id=cid).first()
        if not dados:
            return jsonify({'error': 'not found'}), 404
        result = {c.name: getattr(dados, c.name) for c in DadosEscola.__table__.columns}
        return jsonify(result)
    except Exception:
        current_app.logger.exception('Erro ao buscar dados_escola por cabecalho_id')
        return jsonify({'error': 'internal'}), 500
