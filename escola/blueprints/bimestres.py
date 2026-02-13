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

@bimestres_bp.route('/fechar/<int:ano>', methods=['POST'])
@admin_required
def fechar_ano(ano):
    try:
        from services.escolar_helper import fechamento_ano_letivo_em_lote
        fechamento_ano_letivo_em_lote(ano)
        flash(f'Ano letivo {ano} fechado com sucesso! Saldos transferidos para {ano + 1}.', 'success')
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Erro ao fechar ano letivo: {e}', 'danger')

    # Atualiza a página (mantém visualgação no modo iframe se necessário)
    return redirect(url_for('bimestres_bp.listar_bimestres'))

@bimestres_bp.route('/gestao')
@admin_required
def gestao_bimestres():
    """Página de gestão e fechamento de bimestres"""
    db = get_db()
    from sqlalchemy import text
    
    # Buscar todos os anos com bimestres
    anos = [
        row[0] for row in db.query(Bimestre.ano).distinct().order_by(Bimestre.ano.desc())
    ]
    
    # Ano selecionado (padrão: mais recente)
    ano_selecionado = request.args.get('ano', type=int)
    if not ano_selecionado and anos:
        ano_selecionado = anos[0]
    
    bimestres_info = []
    if ano_selecionado:
        # Buscar bimestres do ano
        bimestres = db.query(Bimestre).filter_by(ano=ano_selecionado).order_by(Bimestre.numero).all()
        
        for bim in bimestres:
            # Verificar se já foi fechado (se existe bônus no próximo bimestre)
            if bim.numero == 4:
                # 4º bimestre: verifica se tem bônus no 1º bim do próximo ano
                ano_prox = ano_selecionado + 1
                bim_prox = 1
            else:
                ano_prox = ano_selecionado
                bim_prox = bim.numero + 1
            
            bonus_aplicado = db.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM pontuacao_historico 
                    WHERE ano = :ano AND bimestre = :bim AND tipo_evento = 'BIMESTRE_BONUS'
                """),
                {"ano": ano_prox, "bim": bim_prox}
            ).scalar()
            
            # Contar alunos processados
            alunos_processados = db.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM medias_bimestrais 
                    WHERE ano = :ano AND bimestre = :bim
                """),
                {"ano": ano_selecionado, "bim": bim.numero}
            ).scalar()
            
            # Total de alunos elegíveis
            total_alunos = db.execute(
                text("""
                    SELECT COUNT(DISTINCT id) 
                    FROM alunos 
                    WHERE data_matricula IS NOT NULL 
                      AND data_matricula <= :data_fim
                """),
                {"data_fim": bim.fim}
            ).scalar()
            
            bimestres_info.append({
                'numero': bim.numero,
                'inicio': bim.inicio,
                'fim': bim.fim,
                'fechado': bonus_aplicado > 0,
                'alunos_processados': alunos_processados,
                'total_alunos': total_alunos
            })
    
    return render_template('cadastros/gestao_bimestres.html', 
                          anos=anos, 
                          ano_selecionado=ano_selecionado,
                          bimestres=bimestres_info)

@bimestres_bp.route('/fechar_bimestre/<int:ano>/<int:bimestre>', methods=['POST'])
@admin_required
def fechar_bimestre(ano, bimestre):
    """Fecha um bimestre específico"""
    try:
        from scripts.pontuacao_rotinas import (
            calcular_e_salvar_pontuacao_final_bimestre,
            apply_bimestral_bonus
        )
        
        # 1. Calcular pontuação final
        calcular_e_salvar_pontuacao_final_bimestre(ano, bimestre, force=True)
        
        # 2. Aplicar bônus bimestral
        apply_bimestral_bonus(ano, bimestre)
        
        flash(f'{bimestre}º Bimestre de {ano} fechado com sucesso!', 'success')
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Erro ao fechar bimestre: {e}', 'danger')
    
    return redirect(url_for('bimestres_bp.gestao_bimestres', ano=ano))
