from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app
from models import get_db
from .utils import login_required, admin_required  # ajuste se usar outro decorator
from datetime import datetime

bimestres_bp = Blueprint('bimestres_bp', __name__, url_prefix='/cadastros/bimestres')


# Cria tabela (apenas para uso manual ou inicialização)
def ensure_table(db_conn):
    try:
        db_conn.execute('''
            CREATE TABLE IF NOT EXISTS bimestres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ano INTEGER NOT NULL,
                numero INTEGER NOT NULL,
                inicio DATE,
                fim DATE,
                responsavel_id INTEGER,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ano, numero)
            );
        ''')
        db_conn.commit()
    except Exception:
        try:
            db_conn.rollback()
        except Exception:
            pass


# Garante a criação da tabela quando o blueprint é registrado no app.
# Usamos `record` para executar com o app disponível e abrir um app_context.
@bimestres_bp.record
def _create_table_on_register(state):
    try:
        # state.app é a aplicação que registrou o blueprint
        with state.app.app_context():
            db = get_db()
            ensure_table(db)
    except Exception:
        # registra no logger da app registrada
        try:
            state.app.logger.exception('Erro ao garantir tabela bimestres')
        except Exception:
            pass


@bimestres_bp.route('/')
@admin_required
def listar_bimestres():
    """Lista anos para os quais existem bimestres configurados."""
    db = get_db()
    rows = db.execute('SELECT DISTINCT ano FROM bimestres ORDER BY ano DESC').fetchall()
    anos = [r['ano'] for r in rows]

    # Se solicitado via iframe, pode-se optar por renderizar um fragmento (se existir).
    # Aqui deixamos o comportamento atual (render normal). Se você criar um fragmento,
    # troque o template por 'cadastros/bimestres_list_fragment.html' quando request.args.get('iframe') == '1'.
    if request.args.get('iframe') == '1':
        # tenta renderizar fragmento (caso tenha criado o arquivo fragment)
        try:
            return render_template('cadastros/bimestres_list_fragment.html', anos=anos)
        except Exception:
            # fallback para o template completo se fragment não existir
            pass

    return render_template('cadastros/bimestres_list.html', anos=anos)


@bimestres_bp.route('/gerenciar', methods=['GET', 'POST'])
@admin_required
def gerenciar_bimestres():
    """
    Form para criar/editar os 4 bimestres de um ano.
    Query param: ?ano=2025  ou POST com campo 'ano'
    """
    db = get_db()

    if request.method == 'POST':
        try:
            ano = request.form.get('ano', '').strip()
            if not ano or not ano.isdigit():
                flash('Informe um ano válido.', 'danger')
                # preservar iframe no redirect se vier do iframe
                if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                    return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano, iframe=1))
                return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano))

            ano = int(ano)

            # Ler os quatro pares (start/end)
            dados = []
            for n in range(1, 5):
                inicio = request.form.get(f'inicio_{n}', '').strip() or None
                fim = request.form.get(f'fim_{n}', '').strip() or None
                # Validação simples: se fornecido, deve ser AAAA-MM-DD
                if inicio:
                    try:
                        datetime.strptime(inicio, '%Y-%m-%d')
                    except Exception:
                        flash(f'Data de início inválida para {n}º Bimestre.', 'danger')
                        if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                            return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano, iframe=1))
                        return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano))
                if fim:
                    try:
                        datetime.strptime(fim, '%Y-%m-%d')
                    except Exception:
                        flash(f'Data de fim inválida para {n}º Bimestre.', 'danger')
                        if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                            return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano, iframe=1))
                        return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano))

                dados.append((n, inicio, fim))

            # Salvar: vamos substituir os registros do ano (DELETE + INSERT)
            db.execute('DELETE FROM bimestres WHERE ano = ?', (ano,))
            for numero, inicio, fim in dados:
                db.execute('''
                    INSERT INTO bimestres (ano, numero, inicio, fim, responsavel_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ano, numero, inicio, fim, session.get('user_id')))
            db.commit()
            flash(f'Bimestres do ano {ano} salvos com sucesso.', 'success')

            # Redirect: se a requisição veio do iframe, mantenha ?iframe=1 no redirect
            if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                return redirect(url_for('bimestres_bp.listar_bimestres', iframe=1))
            return redirect(url_for('bimestres_bp.listar_bimestres'))
        except Exception as e:
            db.rollback()
            current_app.logger.exception('Erro ao salvar bimestres')
            flash(f'Erro ao salvar: {e}', 'danger')
            # preservar iframe no redirect de erro também
            if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                return redirect(url_for('bimestres_bp.listar_bimestres', iframe=1))
            return redirect(url_for('bimestres_bp.listar_bimestres'))

    # GET
    ano_q = request.args.get('ano', '').strip()
    ano = int(ano_q) if ano_q.isdigit() else None
    bimestres = {n: {'inicio': '', 'fim': ''} for n in range(1, 5)}
    if ano:
        rows = db.execute('SELECT numero, inicio, fim FROM bimestres WHERE ano = ? ORDER BY numero', (ano,)).fetchall()
        for r in rows:
            num = int(r['numero'])
            bimestres[num] = {'inicio': r['inicio'] or '', 'fim': r['fim'] or ''}
    # se solicitado via iframe, renderizar o formulário de iframe (se existir)
    if request.args.get('iframe') == '1':
        try:
            return render_template('cadastros/bimestres_form_fragment.html', ano=ano, bimestres=bimestres)
        except Exception:
            pass
    return render_template('cadastros/bimestres_form.html', ano=ano, bimestres=bimestres)


@bimestres_bp.route('/excluir/<int:ano>', methods=['POST'])
@admin_required
def excluir_bimestres(ano):
    db = get_db()
    try:
        db.execute('DELETE FROM bimestres WHERE ano = ?', (ano,))
        db.commit()
        flash(f'Bimestres do ano {ano} excluídos.', 'success')
    except Exception as e:
        db.rollback()
        current_app.logger.exception('Erro ao excluir bimestres')
        flash(f'Erro ao excluir: {e}', 'danger')
    # preservar iframe se a requisição veio do iframe
    if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
        return redirect(url_for('bimestres_bp.listar_bimestres', iframe=1))
    return redirect(url_for('bimestres_bp.listar_bimestres'))