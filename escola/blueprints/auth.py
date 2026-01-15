from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from database import get_db
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import datetime

from .utils import login_required, admin_required, NIVEL_MAP
from datetime import datetime, timedelta
from .utils import gerar_token_seguro  # Se colocou lá a função acima

# Definição da Blueprint
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM usuarios WHERE email = ?', (email,)
        ).fetchone()
        if not email:
            error = 'E-mail institucional é obrigatório.'
        elif user is None:
            error = 'E-mail não encontrado ou não cadastrado.'
        else:
            # 1. Gera e salva token
            token = gerar_token_seguro()
            expiracao = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            db.execute("""
                INSERT INTO recuperacao_senha_tokens (user_id, email, token, expiracao)
                VALUES (?, ?, ?, ?)
            """, (user['id'], email, token, expiracao))
            db.commit()
            
            # 2. Buscar remetente, dom��nio e nome do sistema nos dados da escola
            dados_escola = db.execute(
                "SELECT email_remetente, senha_email_app, dominio_sistema, nome_sistema FROM dados_escola LIMIT 1"
            ).fetchone()

            remetente    = dados_escola['email_remetente']
            senha_app    = dados_escola['senha_email_app']
            dominio      = dados_escola['dominio_sistema']
            nome_sistema = dados_escola['nome_sistema']

            reset_link = f"{dominio}/auth/resetar_senha?token={token}"
            corpo_email = (
                f"Prezado(a),\n\n"
                f"Recebemos uma solicitação de redefinição de senha para seu acesso ao sistema {nome_sistema}.\n"
                f"Para redefinir, acesse o seguinte link (válido por 1 hora):\n\n"
                f"{reset_link}\n\n"
                f"Se não foi você, ignore este e-mail."
            )
            # Versão HTML para clientes modernos (Gmail, Outlook, etc)
            corpo_email_html = (
                f"<p>Prezado(a),</p>"
                f"<p>Recebemos uma solicitação de redefinição de senha para seu acesso ao sistema <b>{nome_sistema}</b>.<br>"
                f"Para redefinir, <a href=\"{reset_link}\">clique aqui</a> (válido por 1 hora).</p>"
                f"<p style='color: #555;'>Se não foi você, ignore este e-mail.</p>"
            )

            # Envio do e-mail – enviar ambos (texto puro + HTML)
            try:
                from .utils import enviar_email  # ajuste se necessário
                enviar_email(
                    destinatario=email,
                    assunto=f"Recuperação de senha - {nome_sistema}",
                    corpo=corpo_email,
                    corpo_html=corpo_email_html,
                    remetente=remetente,
                    senha=senha_app
                )
                flash('Se o e-mail informado estiver cadastrado, você receberá as instruções para redefinir sua senha.', 'info')
            except Exception as e:
                print("Erro detalhado ao enviar email:", e)
                flash('Houve um erro ao enviar o e-mail. Tente novamente mais tarde.', 'danger')

            return redirect(url_for('auth_bp.login'))
        flash(error, 'danger')
    return render_template('recuperar_senha.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Lógica de login e autenticação de usuário."""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        error = None

        if not username:
            error = 'Nome de usuário é obrigatório.'
        elif not password:
            error = 'Senha é obrigatória.'
        else:
            user = db.execute(
                'SELECT * FROM usuarios WHERE username = ?', (username,)
            ).fetchone()

            if user is None:
                error = 'Nome de usuário incorreto ou não cadastrado.'
            elif not check_password_hash(user['password'], password):
                error = 'Senha incorreta.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nivel'] = user['nivel']
            session['nivel_nome'] = NIVEL_MAP.get(user['nivel'], 'Desconhecido')
            session['logged_in'] = True
            flash(f'Bem-vindo(a), {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        
        flash(error, 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Lógica de logout."""
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/cadastro_usuario', methods=['GET', 'POST'])
@admin_required
def cadastro_usuario():
    """Permite o Admin Geral cadastrar novos usuários."""
    db = get_db()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        nivel = request.form.get('nivel', type=int)
        cargo = request.form.get('cargo', '').strip()
        error = None

        if not username or len(username) < 3:
            error = 'Nome de usuário inválido (mínimo 3 caracteres).'
        elif not password or len(password) < 6:
            error = 'Senha inválida (mínimo 6 caracteres).'
        elif not email or '@' not in email:
            error = 'E-mail institucional válido é obrigatório.'
        elif nivel not in NIVEL_MAP:
            error = 'Nível de acesso inválido.'
        elif not cargo:
            error = 'Cargo é obrigatório.'
        if error is None:
            try:
                # 1. Checa se o usuário já existe
                if db.execute('SELECT id FROM usuarios WHERE username = ?', (username,)).fetchone() is not None:
                    error = f'O nome de usuário "{username}" já está em uso.'
                else:
                    # 2. Insere novo usuário com a data de criação
                    db.execute(
                        'INSERT INTO usuarios (username, password, email, nivel, data_criacao, cargo) VALUES (?, ?, ?, ?, ?, ?)',
                        (username, generate_password_hash(password), email, nivel, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cargo)
                    )
                    db.commit()
                    flash(f'Usuário "{username}" cadastrado com sucesso!', 'success')
                    return redirect(url_for('auth_bp.gerenciar_usuarios'))
            except sqlite3.Error as e:
                db.rollback()
                error = f'Erro ao cadastrar usuário: {e}'
        
        flash(error, 'danger')
        
    return render_template('cadastro_usuario.html', nivel_map=NIVEL_MAP)

@auth_bp.route('/resetar_senha', methods=['GET', 'POST'])
def resetar_senha():
    token = request.args.get('token', '').strip()
    db = get_db()

    dados_token = db.execute(
        "SELECT * FROM recuperacao_senha_tokens WHERE token = ? AND usado = 0",
        (token,)
    ).fetchone()

    # Verifica se o token existe e não foi usado
    if not dados_token:
        flash('Token inválido, expirado ou já utilizado.', 'danger')
        return redirect(url_for('auth_bp.login'))

    # Verifica se expirou
    from datetime import datetime
    expiracao = datetime.strptime(dados_token['expiracao'], '%Y-%m-%d %H:%M:%S')
    if datetime.now() > expiracao:
        flash('Token expirado! Por favor, solicite nova recuperação.', 'danger')
        return redirect(url_for('auth_bp.recuperar_senha'))

    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha', '').strip()
        confirma_senha = request.form.get('confirma_senha', '').strip()
        if not nova_senha or len(nova_senha) < 6:
            flash('A nova senha deve ter ao menos 6 caracteres.', 'danger')
        elif nova_senha != confirma_senha:
            flash('Senhas não coincidem.', 'danger')
        else:
            # Troca a senha do usuário
            from werkzeug.security import generate_password_hash
            db.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (generate_password_hash(nova_senha), dados_token['user_id'])
            )
            db.execute(
                "UPDATE recuperacao_senha_tokens SET usado = 1, data_uso = CURRENT_TIMESTAMP WHERE id = ?",
                (dados_token['id'],)
            )
            db.commit()
            flash('Senha redefinida com sucesso! Faça login com a nova senha.', 'success')
            return redirect(url_for('auth_bp.login'))

    return render_template('resetar_senha.html')

@auth_bp.route('/gerenciar_usuarios')
@admin_required
def gerenciar_usuarios():
    """Lista todos os usuários e permite gerenciamento pelo Admin Geral (TI)."""
    db = get_db()
    
    # CORREÇÃO: Selecionar a coluna 'data_criacao'
    try:
        usuarios = db.execute('''
            SELECT id, username, nivel, cargo, data_criacao 
            FROM usuarios 
            ORDER BY nivel, username
        ''').fetchall()
    except sqlite3.OperationalError as e:
        # Fallback para o caso de a coluna data_criacao ainda não ter sido migrada
        # Isso não deve ocorrer após rodar o servidor, pois models.py cuida da migração
        # mas adiciona robustez.
        if "no such column: data_criacao" in str(e):
             usuarios = db.execute('''
                SELECT id, username, nivel, cargo
                FROM usuarios 
                ORDER BY nivel, username
            ''').fetchall()
        else:
            raise

    # Transforma os resultados em lista de dicionários para facilitar o uso no template
    usuarios_list = [dict(u) for u in usuarios]
    
    return render_template('gerenciar_usuarios.html', 
                           usuarios=usuarios_list,
                           nivel_map=NIVEL_MAP)


@auth_bp.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(user_id):
    """Permite a edição de um usuário pelo Admin Geral (TI)."""
    db = get_db()
    
    user = db.execute('SELECT id, username, nivel, cargo, email FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('auth_bp.gerenciar_usuarios'))
        
    user_dict = dict(user)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        nivel = request.form.get('nivel_acesso', type=int)
        cargo = request.form.get('cargo', '').strip()
        error = None

        if not username or len(username) < 3:
            error = 'Nome de usuário inválido (mínimo 3 caracteres).'
        elif not email or '@' not in email:
            error = 'E-mail institucional válido é obrigatório.'
        elif nivel not in NIVEL_MAP:
            error = 'Nível de acesso inválido.'
        elif not cargo:
            error = 'Cargo é obrigatório.'
        if error is None:
            try:
                # Verifica se o novo username já está em uso por outro usuário
                check_user = db.execute(
                    'SELECT id FROM usuarios WHERE username = ? AND id != ?', 
                    (username, user_id)
                ).fetchone()
                
                if check_user is not None:
                    error = f'O nome de usuário "{username}" já está em uso por outro usuário.'
                else:
                    # Monta a query de atualização
                    params = [username, email, nivel]
                    set_clauses = ['username = ?', 'email = ?', 'nivel = ?']
                    set_clauses.append('cargo = ?')
                    params.append(cargo)
                    
                    if password and len(password) >= 6:
                        set_clauses.append('password = ?')
                        params.append(generate_password_hash(password))
                    
                    params.append(user_id)
                    
                    db.execute(
                        f'UPDATE usuarios SET {", ".join(set_clauses)} WHERE id = ?',
                        params
                    )
                    db.commit()
                    
                    # Se o usuário editado for o logado, atualiza a sessão
                    if user_id == session.get('user_id'):
                        session['username'] = username
                        session['nivel'] = nivel
                        session['nivel_nome'] = NIVEL_MAP.get(nivel, 'Desconhecido')
                    
                    flash(f'Usuário "{username}" atualizado com sucesso!', 'success')
                    return redirect(url_for('auth_bp.gerenciar_usuarios'))

            except sqlite3.Error as e:
                db.rollback()
                error = f'Erro ao atualizar usuário: {e}'

        flash(error, 'danger')

    acessos = [{'id': k, 'nome': v} for k, v in NIVEL_MAP.items()]
    return render_template('editar_usuario.html', user=user_dict, acessos=acessos)


@auth_bp.route('/excluir_usuario/<int:user_id>', methods=['POST'])
@admin_required
def excluir_usuario(user_id):
    """Permite a exclusão de um usuário pelo Admin Geral (TI)."""
    db = get_db()
    
    user = db.execute('SELECT nivel, username FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('auth_bp.gerenciar_usuarios'))

    # Proteção: Não permite excluir a si mesmo
    if user_id == session.get('user_id'):
        flash('Você não pode excluir a si mesmo.', 'danger')
        return redirect(url_for('auth_bp.gerenciar_usuarios'))
    
    # Proteção: Não permite excluir outro Admin Geral (Nível 1)
    if user['nivel'] == 1:
        flash('Você não pode excluir outro Admin Geral (TI).', 'danger')
        return redirect(url_for('auth_bp.gerenciar_usuarios'))
        
    try:
        db.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
        db.commit()
        flash(f'Usuário "{user["username"]}" excluído com sucesso.', 'success')
    except sqlite3.Error as e:
        db.rollback()
        flash(f'Erro ao excluir usuário: {e}', 'danger')
        
    return redirect(url_for('auth_bp.gerenciar_usuarios'))

