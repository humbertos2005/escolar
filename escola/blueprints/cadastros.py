from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database import get_db
import sqlite3
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
    faltas = db.execute('''
    SELECT id, natureza, descricao, data_criacao 
    FROM faltas_disciplinares 
    ORDER BY id ASC
''').fetchall()
    
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
                db.execute('''
                    INSERT INTO faltas_disciplinares (natureza, descricao)
                    VALUES (?, ?)
                ''', (natureza, descricao))
                db.commit()
                flash(f'Falta disciplinar cadastrada com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_faltas'))
            except sqlite3.Error as e:
                error = f'Erro ao cadastrar falta: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/adicionar_falta.html')

@cadastros_bp.route('/faltas/editar/<int:falta_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_falta(falta_id):
    """Edita uma falta disciplinar."""
    db = get_db()
    falta = db.execute('SELECT * FROM faltas_disciplinares WHERE id = ?', (falta_id,)).fetchone()
    
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
                db.execute('''
                    UPDATE faltas_disciplinares 
                    SET natureza = ?, descricao = ?
                    WHERE id = ?
                ''', (natureza, descricao, falta_id))
                db.commit()
                flash('Falta disciplinar atualizada com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_faltas'))
            except sqlite3.Error as e:
                error = f'Erro ao atualizar falta: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/editar_falta.html', falta=dict(falta))

@cadastros_bp.route('/faltas/excluir/<int:falta_id>', methods=['POST'])
@admin_secundario_required
def excluir_falta(falta_id):
    """Exclui uma falta disciplinar."""
    db = get_db()
    try:
        db.execute('DELETE FROM faltas_disciplinares WHERE id = ?', (falta_id,))
        db.commit()
        flash('Falta disciplinar excluída com sucesso.', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao excluir falta: {e}', 'danger')
    
    return redirect(url_for('cadastros_bp.listar_faltas'))

@cadastros_bp.route('/elogios')
@admin_secundario_required
def listar_elogios():
    """Lista todos os elogios cadastrados."""
    db = get_db()
    elogios = db.execute('''
        SELECT id, tipo, descricao, data_criacao 
        FROM elogios 
        ORDER BY tipo, descricao
    ''').fetchall()
    
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
                db.execute('''
                    INSERT INTO elogios (tipo, descricao)
                    VALUES (?, ?)
                ''', (tipo, descricao))
                db.commit()
                flash(f'Elogio cadastrado com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_elogios'))
            except sqlite3.Error as e:
                error = f'Erro ao cadastrar elogio: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/adicionar_elogio.html')

@cadastros_bp.route('/elogios/editar/<int:elogio_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_elogio(elogio_id):
    """Edita um elogio."""
    db = get_db()
    elogio = db.execute('SELECT * FROM elogios WHERE id = ?', (elogio_id,)).fetchone()
    
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
                db.execute('''
                    UPDATE elogios 
                    SET tipo = ?, descricao = ?
                    WHERE id = ?
                ''', (tipo, descricao, elogio_id))
                db.commit()
                flash('Elogio atualizado com sucesso!', 'success')
                return redirect(url_for('cadastros_bp.listar_elogios'))
            except sqlite3.Error as e:
                error = f'Erro ao atualizar elogio: {e}'
        
        flash(error, 'danger')
    
    return render_template('cadastros/editar_elogio.html', elogio=dict(elogio))

@cadastros_bp.route('/elogios/excluir/<int:elogio_id>', methods=['POST'])
@admin_secundario_required
def excluir_elogio(elogio_id):
    """Exclui um elogio.""" 
    db = get_db()
    try:
        db.execute('DELETE FROM elogios WHERE id = ?', (elogio_id,))
        db.commit()
        flash('Elogio excluído com sucesso.', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao excluir elogio: {e}', 'danger')
    
    return redirect(url_for('cadastros_bp.listar_elogios'))

# BLOCO A SER INSERIDO NO FINAL DE blueprints/cadastros.py
from flask import current_app, request, redirect, url_for, flash, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from database import get_db
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
    rows = db.execute('SELECT * FROM cabecalhos ORDER BY id DESC').fetchall()
    cabecalhos = [dict(r) for r in rows]
    # montar url completo para imagens
    for c in cabecalhos:
        if c.get('logo_estado'):
            c['logo_estado_url'] = url_for('static', filename=f'uploads/cabecalhos/{c["logo_estado"]}')
        else:
            c['logo_estado_url'] = None
        if c.get('logo_escola'):
            c['logo_escola_url'] = url_for('static', filename=f'uploads/cabecalhos/{c["logo_escola"]}')
        else:
            c['logo_escola_url'] = None
        # novo campo logo_prefeitura (pode não existir na tabela até você executar a migração)
        if c.get('logo_prefeitura'):
            c['logo_prefeitura_url'] = url_for('static', filename=f'uploads/cabecalhos/{c["logo_prefeitura"]}')
        else:
            c['logo_prefeitura_url'] = None
    # NOTE: usar o nome do template que já existe no projeto (listar_cabecalho.html)
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

        # processar logo_prefeitura (novo)
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
            db.execute('''
                INSERT INTO cabecalhos (estado, secretaria, coordenacao, escola, logo_estado, logo_escola, logo_prefeitura, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (estado, secretaria, coordenacao, escola, logo_estado_filename, logo_escola_filename, logo_prefeitura_filename, datetime.utcnow().isoformat()))
            db.commit()
            flash('Cabeçalho salvo com sucesso.', 'success')
            return redirect(url_for('cadastros_bp.listar_cabecalhos'))
        except Exception as e:
            current_app.logger.exception('Erro ao salvar cabeçalho')
            flash('Erro ao salvar cabeçalho.', 'danger')
            return redirect(url_for('cadastros_bp.cabecalho_novo'))

    # GET
    return render_template('cadastros/cabecalho_form.html', cabecalho=None)

@cadastros_bp.route('/cabecalho/editar/<int:id>', methods=['GET', 'POST'])
def cabecalho_editar(id):
    db = get_db()
    row = db.execute('SELECT * FROM cabecalhos WHERE id = ?', (id,)).fetchone()
    if row is None:
        flash('Cabeçalho não encontrado.', 'danger')
        return redirect(url_for('cadastros_bp.listar_cabecalhos'))
    cabecalho = dict(row)

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
                if cabecalho.get('logo_estado'):
                    try:
                        os.remove(os.path.join(upload_dir, cabecalho['logo_estado']))
                    except Exception:
                        pass
                cabecalho['logo_estado'] = logo_estado_filename

        # processar logo_prefeitura (novo)
        if 'logo_prefeitura' in request.files:
            f = request.files['logo_prefeitura']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_prefeitura_filename = f"prefeitura_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_prefeitura_filename))
                # remover anterior se existir
                if cabecalho.get('logo_prefeitura'):
                    try:
                        os.remove(os.path.join(upload_dir, cabecalho['logo_prefeitura']))
                    except Exception:
                        pass
                cabecalho['logo_prefeitura'] = logo_prefeitura_filename

        # processar logo_escola
        if 'logo_escola' in request.files:
            f = request.files['logo_escola']
            if f and f.filename and _allowed_file(f.filename):
                raw = secure_filename(f.filename)
                ext = raw.rsplit('.', 1)[1].lower()
                logo_escola_filename = f"escola_{int(datetime.utcnow().timestamp())}.{ext}"
                f.save(os.path.join(upload_dir, logo_escola_filename))
                # remover anterior se existir
                if cabecalho.get('logo_escola'):
                    try:
                        os.remove(os.path.join(upload_dir, cabecalho['logo_escola']))
                    except Exception:
                        pass
                cabecalho['logo_escola'] = logo_escola_filename

        try:
            # atualizar incluindo logo_prefeitura
            db.execute('''
                UPDATE cabecalhos SET estado=?, secretaria=?, coordenacao=?, escola=?, logo_estado=?, logo_escola=?, logo_prefeitura=?
                WHERE id = ?
            ''', (estado, secretaria, coordenacao, escola, cabecalho.get('logo_estado'), cabecalho.get('logo_escola'), cabecalho.get('logo_prefeitura'), id))
            db.commit()
            flash('Cabeçalho atualizado com sucesso.', 'success')
            return redirect(url_for('cadastros_bp.listar_cabecalhos'))
        except Exception as e:
            current_app.logger.exception('Erro ao atualizar cabeçalho')
            flash('Erro ao atualizar cabeçalho.', 'danger')
            return redirect(url_for('cadastros_bp.cabecalho_editar', id=id))

    # GET: montar urls de imagens
    if cabecalho.get('logo_estado'):
        cabecalho['logo_estado_url'] = url_for('static', filename=f'uploads/cabecalhos/{cabecalho["logo_estado"]}')
    else:
        cabecalho['logo_estado_url'] = None
    if cabecalho.get('logo_escola'):
        cabecalho['logo_escola_url'] = url_for('static', filename=f'uploads/cabecalhos/{cabecalho["logo_escola"]}')
    else:
        cabecalho['logo_escola_url'] = None
    # novo campo logo_prefeitura (pode não existir na tabela)
    if cabecalho.get('logo_prefeitura'):
        cabecalho['logo_prefeitura_url'] = url_for('static', filename=f'uploads/cabecalhos/{cabecalho["logo_prefeitura"]}')
    else:
        cabecalho['logo_prefeitura_url'] = None

    return render_template('cadastros/cabecalho_form.html', cabecalho=cabecalho)

@cadastros_bp.route('/cabecalho/excluir/<int:id>', methods=['POST'])
def cabecalho_excluir(id):
    db = get_db()
    row = db.execute('SELECT * FROM cabecalhos WHERE id = ?', (id,)).fetchone()
    if row:
        try:
            # remover arquivos associados
            upload_dir = _ensure_upload_dir()
            if row.get('logo_estado'):
                try:
                    os.remove(os.path.join(upload_dir, row['logo_estado']))
                except Exception:
                    pass
            if row.get('logo_escola'):
                try:
                    os.remove(os.path.join(upload_dir, row['logo_escola']))
                except Exception:
                    pass
            if row.get('logo_prefeitura'):
                try:
                    os.remove(os.path.join(upload_dir, row['logo_prefeitura']))
                except Exception:
                    pass
            db.execute('DELETE FROM cabecalhos WHERE id = ?', (id,))
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

    # carregar cabecalhos (mesma lógica de listar_cabecalhos)
    rows = db.execute('SELECT * FROM cabecalhos ORDER BY id DESC').fetchall()
    cabecalhos = [dict(r) for r in rows]
    for c in cabecalhos:
        if c.get('logo_estado'):
            c['logo_estado_url'] = url_for('static', filename=f'uploads/cabecalhos/{c["logo_estado"]}')
        else:
            c['logo_estado_url'] = None
        if c.get('logo_escola'):
            c['logo_escola_url'] = url_for('static', filename=f'uploads/cabecalhos/{c["logo_escola"]}')
        else:
            c['logo_escola_url'] = None
        if c.get('logo_prefeitura'):
            c['logo_prefeitura_url'] = url_for('static', filename=f'uploads/cabecalhos/{c["logo_prefeitura"]}')
        else:
            c['logo_prefeitura_url'] = None

    # carregar dados da escola (mesma lógica de listar_dados_escola)
    rows2 = db.execute("SELECT * FROM dados_escola ORDER BY id DESC").fetchall()
    dados = [dict(r) for r in rows2]
    for d in dados:
        if d.get('cabecalho_id'):
            ch = db.execute("SELECT escola FROM cabecalhos WHERE id = ?", (d['cabecalho_id'],)).fetchone()
            d['escola_origem'] = ch['escola'] if ch else None
        else:
            d['escola_origem'] = None

    # Renderizar o novo template (a seguir eu entrego o arquivo templates/cadastros/dados_documentos.html)
    # Passamos cabecalhos e dados. Passamos cabecalho/dados None para os formulários "novo".
    return render_template('cadastros/dados_documentos.html',
                           cabecalhos=cabecalhos,
                           dados=dados,
                           cabecalho=None)

@cadastros_bp.route('/dados_escola')
@admin_secundario_required
def listar_dados_escola():
    """Listagem de Dados da Escola"""
    db = get_db()
    rows = db.execute("SELECT * FROM dados_escola ORDER BY id DESC").fetchall()
    dados = [dict(r) for r in rows]
    # opcional: buscar nome do cabecalho relacionado
    for d in dados:
        if d.get('cabecalho_id'):
            ch = db.execute("SELECT escola FROM cabecalhos WHERE id = ?", (d['cabecalho_id'],)).fetchone()
            d['escola_origem'] = ch['escola'] if ch else None
        else:
            d['escola_origem'] = None
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

        # >>>>>>>>> NOVOS CAMPOS ADICIONADOS <<<<<<<<<<
        email_remetente = request.form.get('email_remetente','').strip()
        senha_email_app = request.form.get('senha_email_app','').strip()
        # <<<<<<<< FIM DOS NOVOS CAMPOS <<<<<<<<<<

        try:
            db.execute('''
            INSERT INTO dados_escola (cabecalho_id, escola, rua, numero, complemento, bairro, cidade, estado, cep, cnpj, diretor_nome, diretor_cpf, email_remetente, senha_email_app, telefone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cabecalho_id, escola, rua, numero, complemento, bairro, cidade, estado, cep, cnpj, diretor_nome, diretor_cpf, email_remetente, senha_email_app, telefone))
            db.commit()
            flash('Dados da Escola salvos.', 'success')
            return redirect(url_for('cadastros_bp.listar_dados_escola'))
        except Exception:
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
    row = db.execute("SELECT * FROM dados_escola WHERE id = ?", (id,)).fetchone()
    if not row:
        flash('Registro não encontrado.', 'warning')
        return redirect(url_for('cadastros_bp.listar_dados_escola'))
    dados = dict(row)
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
            return redirect(url_for('cadastros_bp.dados_escola_editar', id=id))
        estado = estado_norm

        cep = request.form.get('cep','').strip()
        cnpj = request.form.get('cnpj','').strip()
        diretor_nome = request.form.get('diretor_nome','').strip()
        diretor_cpf = request.form.get('diretor_cpf','').strip()

        # NOVOS CAMPOS
        email_remetente = request.form.get('email_remetente','').strip()
        senha_email_app = request.form.get('senha_email_app','').strip()

        try:
            db.execute('''
                UPDATE dados_escola SET cabecalho_id=?, escola=?, rua=?, numero=?, complemento=?, bairro=?, cidade=?, estado=?, cep=?, cnpj=?, diretor_nome=?, diretor_cpf=?, email_remetente=?, senha_email_app=?, telefone=? WHERE id=?
            ''', (
                cabecalho_id, escola, rua, numero, complemento, bairro, cidade, estado, cep, cnpj,
                diretor_nome, diretor_cpf, email_remetente, senha_email_app, telefone, id
            ))
            db.commit()
            flash('Dados da Escola atualizados.', 'success')
            return redirect(url_for('cadastros_bp.listar_dados_escola'))
        except Exception:
            current_app.logger.exception('Erro ao atualizar dados da escola')
            flash('Erro ao atualizar dados da escola.', 'danger')
            return redirect(url_for('cadastros_bp.dados_escola_editar', id=id))

    # GET: renderizar com dados preenchidos
    # adicionar URLs ou nomes de origem se desejar
    return render_template('cadastros/dados_escola_form.html', dados=dados)

@cadastros_bp.route('/dados_escola/excluir/<int:id>', methods=['POST'])
@admin_secundario_required
def dados_escola_excluir(id):
    db = get_db()
    try:
        db.execute("DELETE FROM dados_escola WHERE id = ?", (id,))
        db.commit()
        flash('Registro excluído.', 'success')
    except Exception:
        current_app.logger.exception('Erro ao excluir dados da escola')
        flash('Erro ao excluir registro.', 'danger')
    return redirect(url_for('cadastros_bp.listar_dados_escola'))

# API: autocomplete puxando da tabela cabecalhos (campo escola)
@cadastros_bp.route('/api/cabecalhos_autocomplete')
def cabecalhos_autocomplete():
    q = request.args.get('q','').strip()
    db = get_db()
    if not q:
        rows = db.execute("SELECT id, escola FROM cabecalhos ORDER BY id DESC LIMIT 30").fetchall()
    else:
        qlike = f"%{q.upper()}%"
        rows = db.execute("SELECT id, escola FROM cabecalhos WHERE UPPER(escola) LIKE ? ORDER BY escola LIMIT 30", (qlike,)).fetchall()
    results = [{'id': r['id'], 'escola': r['escola']} for r in rows]
    return jsonify(results)

# API: obter cabecalho por id (para popular endereço quando usuário escolher)
@cadastros_bp.route('/api/cabecalho')
def cabecalho_by_id():
    cid = request.args.get('id')
    db = get_db()
    if not cid:
        return jsonify({'error':'missing id'}), 400
    row = db.execute("SELECT * FROM cabecalhos WHERE id = ?", (cid,)).fetchone()
    if not row:
        return jsonify({'error':'not found'}), 404
    rd = dict(row)
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
        row = db.execute("SELECT * FROM dados_escola WHERE cabecalho_id = ? LIMIT 1", (cid,)).fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        return jsonify(dict(row))
    except Exception:
        current_app.logger.exception('Erro ao buscar dados_escola por cabecalho_id')
        return jsonify({'error': 'internal'}), 500