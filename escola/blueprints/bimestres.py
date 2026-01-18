from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database import get_db
from .utils import admin_required
from datetime import datetime
from sqlalchemy import func, and_
from models_sqlalchemy import Bimestre

bimestres_bp = Blueprint('bimestres_bp', __name__, url_prefix='/cadastros/bimestres')


@bimestres_bp.route('/')
@admin_required
def listar_bimestres():
    """Lista anos para os quais existem bimestres configurados."""
    db = get_db()
    anos = [
        row[0]
        for row in db.query(Bimestre.ano)
                     .distinct()
                     .order_by(Bimestre.ano.desc())
    ]

    # Se solicitado via iframe, pode-se optar por renderizar um fragmento
    if request.args.get('iframe') == '1':
        try:
            return render_template('cadastros/bimestres_list_fragment.html', anos=anos)
        except Exception:
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
                if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                    return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano, iframe=1))
                return redirect(url_for('bimestres_bp.gerenciar_bimestres', ano=ano))

            ano = int(ano)
            dados = []
            for n in range(1, 5):
                inicio = request.form.get(f'inicio_{n}', '').strip() or None
                fim = request.form.get(f'fim_{n}', '').strip() or None
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

            # Excluir bimestres antigos do ano antes de adicionar novos
            db.query(Bimestre).filter(Bimestre.ano == str(ano)).delete()
            db.commit()

            # Adiciona/insere os novos bimestres
            for numero, inicio, fim in dados:
                bimestre = Bimestre(
                    ano=ano,
                    numero=numero,
                    inicio=inicio,
                    fim=fim,
                    responsavel_id=session.get('user_id'),
                )
                db.add(bimestre)
            db.commit()
            flash(f'Bimestres do ano {ano} salvos com sucesso.', 'success')

            if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                return redirect(url_for('bimestres_bp.listar_bimestres', iframe=1))
            return redirect(url_for('bimestres_bp.listar_bimestres'))
        except Exception as e:
            db.rollback()
            current_app.logger.exception('Erro ao salvar bimestres')
            flash(f'Erro ao salvar: {e}', 'danger')
            if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
                return redirect(url_for('bimestres_bp.listar_bimestres', iframe=1))
            return redirect(url_for('bimestres_bp.listar_bimestres'))

    # GET
    ano_q = request.args.get('ano', '').strip()
    ano = int(ano_q) if ano_q.isdigit() else None
    bimestres = {n: {'inicio': '', 'fim': ''} for n in range(1, 5)}
    if ano:
        registros = (
            db.query(Bimestre)
              .filter(Bimestre.ano == ano)
              .order_by(Bimestre.numero.asc())
              .all()
        )
        for r in registros:
            bimestres[r.numero] = {
                'inicio': r.inicio or '',
                'fim': r.fim or ''
            }
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
        db.query(Bimestre).filter(Bimestre.ano == str(ano)).delete()
        db.commit()
        flash(f'Bimestres do ano {ano} excluídos.', 'success')
    except Exception as e:
        db.rollback()
        current_app.logger.exception('Erro ao excluir bimestres')
        flash(f'Erro ao excluir: {e}', 'danger')
    if request.form.get('iframe') == '1' or request.args.get('iframe') == '1':
        return redirect(url_for('bimestres_bp.listar_bimestres', iframe=1))
    return redirect(url_for('bimestres_bp.listar_bimestres'))
