from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_file
from database import get_db
from .tac_utils import get_next_tac_number
from .utils import login_required, admin_secundario_required
from datetime import datetime
import sqlite3
import time
import os

# Optional imports for DOCX export (requires python-docx)
from docx import Document
import io

formularios_tac_bp = Blueprint('formularios_tac_bp', __name__)

# LISTAR TACS
@formularios_tac_bp.route('/tacs')
@admin_secundario_required
def listar_tacs():
    db = get_db()
    show_deleted = request.args.get('show_deleted') == '1'
    try:
        if show_deleted:
            rows = db.execute("SELECT * FROM tacs ORDER BY created_at DESC").fetchall()
        else:
            rows = db.execute("SELECT * FROM tacs WHERE deleted = 0 ORDER BY created_at DESC").fetchall()
        tacs = []
        for r in rows:
            t = dict(r)
            # Provide a normalized display number: if stored as old format, keep as-is;
            # if stored as long timestamp-style, keep as-is too.
            # New TACs will be stored as TAC-XXXX/ANO.
            t['numero_display'] = t.get('numero') or ''
            # tentar resolver nome do aluno e serie/turma (se houver aluno_id)
            t['aluno_nome'] = None
            t['serie_turma'] = None
            if t.get('aluno_id'):
                a = db.execute("SELECT nome, serie, turma FROM alunos WHERE id = ?", (t['aluno_id'],)).fetchone()
                if a:
                    try:
                        t['aluno_nome'] = a['nome']
                    except Exception:
                        t['aluno_nome'] = None
                    try:
                        serie_val = a['serie'] if 'serie' in a.keys() else None
                        turma_val = a['turma'] if 'turma' in a.keys() else None
                        t['serie_turma'] = f"{serie_val or ''} {turma_val or ''}".strip()
                    except Exception:
                        t['serie_turma'] = None
            # fallback para escola_text se necessário
            if not t.get('aluno_nombre') and not t.get('aluno_nome'):
                t['aluno_nome'] = t.get('escola_text') or '-'
            tacs.append(t)
        return render_template('formularios/listar_tacs.html', tacs=tacs, show_deleted=show_deleted)
    except Exception:
        current_app.logger.exception("Erro ao listar TACS")
        flash('Erro ao listar TACS', 'danger')
        return render_template('formularios/listar_tacs.html', tacs=[], show_deleted=show_deleted)

# NOVO / EDITAR - FORM
@formularios_tac_bp.route('/tac/novo', methods=['GET', 'POST'])
@admin_secundario_required
def tac_novo():
    db = get_db()
    if request.method == 'POST':
        # campos principais
        aluno_id = request.form.get('aluno_id') or None
        try:
            aluno_id = int(aluno_id) if aluno_id else None
        except Exception:
            aluno_id = None
        cabecalho_id = request.form.get('cabecalho_id') or None
        escola_text = request.form.get('escola','').strip()
        serie = request.form.get('serie','').strip()
        turma = request.form.get('turma','').strip()
        responsavel = request.form.get('responsavel','').strip()
        diretor = request.form.get('diretor','').strip()
        fato = request.form.get('fato','').strip()
        prazo = request.form.get('prazo','').strip()

        # obrigações e participantes (arrays)
        obrigacoes = request.form.getlist('obrigacao[]')
        participantes_nomes = request.form.getlist('participante_nome[]')
        participantes_cargos = request.form.getlist('participante_cargo[]')

        # Gerar número no formato TAC-XXXX/ANO (ex: TAC-0001/2025)
        # Use uma tentativa com base na contagem de TACS do ano atual e trate IntegrityError caso haja colisão.
        max_attempts = 8
        attempt = 0
        tac_id = None
        while attempt < max_attempts:
            attempt += 1
            try:
                # compute next sequence for current year (simple, robust approach)
                year = datetime.utcnow().strftime('%Y')
                row = db.execute("SELECT COUNT(*) as c FROM tacs WHERE strftime('%Y', created_at) = ?", (year,)).fetchone()
                base_count = int(row['c']) if row and row['c'] is not None else 0
                seq = base_count + attempt  # add attempt to avoid races
                numero = f"TAC-{seq:04d}/{year}"

                db.execute('''
                    INSERT INTO tacs (numero, aluno_id, cabecalho_id, escola_text, serie, turma, responsavel, diretor_nome, fato, prazo, created_at, updated_at, deleted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ''', (numero, aluno_id, cabecalho_id, escola_text, serie, turma, responsavel, diretor, fato, prazo, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                tac_id = db.execute("SELECT last_insert_rowid() as id").fetchone()['id']
                # inserir obrigações
                for idx, ob in enumerate([o for o in obrigacoes if o and o.strip()]):
                    db.execute("INSERT INTO tac_obrigacoes (tac_id, descricao, ordem) VALUES (?, ?, ?)", (tac_id, ob.strip(), idx))
                # inserir participantes
                for idx, (pn, pc) in enumerate(zip(participantes_nomes, participantes_cargos)):
                    if pn and pn.strip():
                        db.execute("INSERT INTO tac_participantes (tac_id, nome, cargo, ordem) VALUES (?, ?, ?, ?)",
                                   (tac_id, pn.strip(), (pc or '').strip(), idx))
                db.commit()
                flash('TAC criado com sucesso.', 'success')
                return redirect(url_for('formularios_tac_bp.listar_tacs'))
            except sqlite3.IntegrityError as e:
                db.rollback()
                # se for conflito no numero, tentar gerar outro e re-tentar
                current_app.logger.warning(f"Conflito numero TAC gerado (tentativa {attempt}/{max_attempts}): {e}")
                time.sleep(0.05)
                continue
            except Exception:
                db.rollback()
                current_app.logger.exception("Erro ao salvar TAC.")
                flash('Erro ao salvar TAC.', 'danger')
                return redirect(url_for('formularios_tac_bp.tac_novo'))

        # Fallback: após várias tentativas, gerar um número baseado em timestamp (garante unicidade)
        try:
            fallback_seq = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[-8:]
            fallback_num = f"TAC-{fallback_seq}/{datetime.utcnow().year}"
            current_app.logger.info(f"Usando número-fallback para TAC: {fallback_num}")
            db.execute('''
                INSERT INTO tacs (numero, aluno_id, cabecalho_id, escola_text, serie, turma, responsavel, diretor_nome, fato, prazo, created_at, updated_at, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (fallback_num, aluno_id, cabecalho_id, escola_text, serie, turma, responsavel, diretor, fato, prazo, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            tac_id = db.execute("SELECT last_insert_rowid() as id").fetchone()['id']
            for idx, ob in enumerate([o for o in obrigacoes if o and o.strip()]):
                db.execute("INSERT INTO tac_obrigacoes (tac_id, descricao, ordem) VALUES (?, ?, ?)", (tac_id, ob.strip(), idx))
            for idx, (pn, pc) in enumerate(zip(participantes_nomes, participantes_cargos)):
                if pn and pn.strip():
                    db.execute("INSERT INTO tac_participantes (tac_id, nome, cargo, ordem) VALUES (?, ?, ?, ?)",
                               (tac_id, pn.strip(), (pc or '').strip(), idx))
            db.commit()
            flash('TAC criado com sucesso.', 'success')
            return redirect(url_for('formularios_tac_bp.listar_tacs'))
        except sqlite3.IntegrityError:
            db.rollback()
            current_app.logger.exception("Falha ao inserir TAC mesmo com numero-fallback (integrity).")
            flash('Erro ao salvar TAC. Falha ao gerar número único.', 'danger')
            return redirect(url_for('formularios_tac_bp.tac_novo'))
        except Exception:
            db.rollback()
            current_app.logger.exception("Falha ao inserir TAC com número-fallback.")
            flash('Erro ao salvar TAC.', 'danger')
            return redirect(url_for('formularios_tac_bp.tac_novo'))

    # GET: render form vazio
    return render_template('formularios/tac_form.html', tac=None)

@formularios_tac_bp.route('/tac/editar/<int:id>', methods=['GET', 'POST'])
@admin_secundario_required
def tac_editar(id):
    db = get_db()
    row = db.execute("SELECT * FROM tacs WHERE id = ?", (id,)).fetchone()
    if not row:
        flash('TAC não encontrado.', 'warning')
        return redirect(url_for('formularios_tac_bp.listar_tacs'))
    tac = dict(row)
    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id') or None
        try:
            aluno_id = int(aluno_id) if aluno_id else None
        except Exception:
            aluno_id = None
        cabecalho_id = request.form.get('cabecalho_id') or None
        escola_text = request.form.get('escola','').strip()
        serie = request.form.get('serie','').strip()
        turma = request.form.get('turma','').strip()
        responsavel = request.form.get('responsavel','').strip()
        diretor = request.form.get('diretor','').strip()
        fato = request.form.get('fato','').strip()
        prazo = request.form.get('prazo','').strip()

        obrigacoes = request.form.getlist('obrigacao[]')
        participantes_nomes = request.form.getlist('participante_nome[]')
        participantes_cargos = request.form.getlist('participante_cargo[]')

        try:
            db.execute('''
                UPDATE tacs SET aluno_id=?, cabecalho_id=?, escola_text=?, serie=?, turma=?, responsavel=?, diretor_nome=?, fato=?, prazo=?, updated_at=?
                WHERE id = ?
            ''', (aluno_id, cabecalho_id, escola_text, serie, turma, responsavel, diretor, fato, prazo, datetime.utcnow().isoformat(), id))
            # remover obrigações/participantes antigos e inserir novos (simples)
            db.execute("DELETE FROM tac_obrigacoes WHERE tac_id = ?", (id,))
            for idx, ob in enumerate([o for o in obrigacoes if o and o.strip()]):
                db.execute("INSERT INTO tac_obrigacoes (tac_id, descricao, ordem) VALUES (?, ?, ?)", (id, ob.strip(), idx))
            db.execute("DELETE FROM tac_participantes WHERE tac_id = ?", (id,))
            for idx, (pn, pc) in enumerate(zip(participantes_nomes, participantes_cargos)):
                if pn and pn.strip():
                    db.execute("INSERT INTO tac_participantes (tac_id, nome, cargo, ordem) VALUES (?, ?, ?, ?)",
                               (id, pn.strip(), (pc or '').strip(), idx))
            db.commit()
            flash('TAC atualizado com sucesso.', 'success')
            return redirect(url_for('formularios_tac_bp.listar_tacs'))
        except Exception:
            current_app.logger.exception("Erro ao atualizar TAC")
            db.rollback()
            flash('Erro ao atualizar TAC.', 'danger')
            return redirect(url_for('formularios_tac_bp.tac_editar', id=id))

    # GET: carregar obrigações e participantes
    obrig = db.execute("SELECT * FROM tac_obrigacoes WHERE tac_id = ? ORDER BY ordem ASC", (id,)).fetchall()
    part = db.execute("SELECT * FROM tac_participantes WHERE tac_id = ? ORDER BY ordem ASC", (id,)).fetchall()
    tac['obrigacoes'] = [o['descricao'] for o in obrig]
    tac['participantes'] = [{'nome': p['nome'], 'cargo': p['cargo']} for p in part]
    return render_template('formularios/tac_form.html', tac=tac)

@formularios_tac_bp.route('/tac/visualizar/<int:id>')
@admin_secundario_required
def tac_visualizar(id):
    db = get_db()
    row = db.execute("SELECT * FROM tacs WHERE id = ?", (id,)).fetchone()
    if not row:
        flash('TAC não encontrado.', 'warning')
        return redirect(url_for('formularios_tac_bp.listar_tacs'))
    tac = dict(row)
    # carregar aluno, obrigações, participantes
    tac['aluno'] = None
    if tac.get('aluno_id'):
        a = db.execute("SELECT * FROM alunos WHERE id = ?", (tac['aluno_id'],)).fetchone()
        tac['aluno'] = dict(a) if a else None
    tac['obrigacoes'] = [r['descricao'] for r in db.execute("SELECT * FROM tac_obrigacoes WHERE tac_id = ? ORDER BY ordem", (id,)).fetchall()]
    tac['participantes'] = [dict(r) for r in db.execute("SELECT * FROM tac_participantes WHERE tac_id = ? ORDER BY ordem", (id,)).fetchall()]

    # garantir campos derivado para template (serie/turma completo, nome em uppercase)
    try:
        serie = tac.get('serie') or ''
        turma = tac.get('turma') or ''
        if serie and turma:
            tac['serie_turma_full'] = f"{serie} / {turma}"
        elif serie:
            tac['serie_turma_full'] = serie
        else:
            tac['serie_turma_full'] = tac.get('serie_turma') or ''
    except Exception:
        tac['serie_turma_full'] = tac.get('serie_turma') or ''

    try:
        aluno_nome = ''
        if tac.get('aluno'):
            aluno_nome = tac['aluno'].get('nome') or ''
        aluno_nome = aluno_nome or tac.get('aluno_nome') or ''
        tac['aluno_nome_upper'] = aluno_nome.upper() if aluno_nome else ''
    except Exception:
        tac['aluno_nome_upper'] = (tac.get('aluno_nome') or '').upper()

    # Buscar dados de cabeçalho (se houver) para exibir logotipos e linhas do cabeçalho
    cabecalho = None
    try:
        cab_id = tac.get('cabecalho_id') or None
        if cab_id:
            ch = db.execute("SELECT * FROM cabecalhos WHERE id = ?", (cab_id,)).fetchone()
            if ch:
                cabecalho = dict(ch)

                # construir URLs seguros para as imagens (basename) com fallback para arquivos existentes
                def _logo_url_from_field(field):
                    try:
                        v = cabecalho.get(field)
                        if not v:
                            return None
                        fn = os.path.basename(str(v).replace('\\', '/'))
                        p = os.path.join(current_app.root_path, 'static', 'uploads', 'cabecalhos', fn)
                        if os.path.exists(p):
                            return url_for('static', filename=f'uploads/cabecalhos/{fn}')
                    except Exception:
                        pass
                    return None

                def _logo_url_from_files(candidates):
                    for fn in candidates:
                        p = os.path.join(current_app.root_path, 'static', 'uploads', 'cabecalhos', fn)
                        if os.path.exists(p):
                            return url_for('static', filename=f'uploads/cabecalhos/{fn}')
                    return None

                # school logo: prefer explicit field, fallback to common filename 'logo_left.png'
                cabecalho['logo_escola_url'] = _logo_url_from_field('logo_escola') or _logo_url_from_files(['logo_left.png', 'logo_escola.png', 'escola_1764363775.jpg'])

                # top/logo prefeitura: prefer explicit logo_prefeitura, then logo_topo, then known files (Logotipo SEDUC.png, logo_topo.png)
                cabecalho['logo_prefeitura_url'] = _logo_url_from_field('logo_prefeitura') or _logo_url_from_field('logo_topo') or _logo_url_from_files(['Logotipo SEDUC.png', 'logo_topo.png', 'estado_1764363775.jpg'])

                # keep logo_estado_url (but template will not show the second right logo per requirement)
                cabecalho['logo_estado_url'] = _logo_url_from_field('logo_estado') or _logo_url_from_files(['logo_estado.png', 'estado_1764363775.jpg'])

                # tentar buscar dados adicionais da escola em dados_escola (CNPJ, cidade, estado, diretor_nome etc.)
                try:
                    de = db.execute("SELECT * FROM dados_escola WHERE cabecalho_id = ? LIMIT 1", (cab_id,)).fetchone()
                    if de:
                        cabecalho['dados_escola'] = dict(de)
                    else:
                        cabecalho['dados_escola'] = None
                except Exception:
                    cabecalho['dados_escola'] = None
    except Exception:
        current_app.logger.exception("Erro ao buscar cabecalho para TAC visualizar")
        cabecalho = None

    return render_template('formularios/tac_view.html', tac=tac, cabecalho=cabecalho)

@formularios_tac_bp.route('/tac/excluir/<int:id>', methods=['POST'])
@admin_secundario_required
def tac_excluir(id):
    db = get_db()
    try:
        db.execute("UPDATE tacs SET deleted=1, updated_at=? WHERE id = ?", (datetime.utcnow().isoformat(), id))
        db.commit()
        flash('TAC excluído (soft-delete).', 'success')
    except Exception:
        current_app.logger.exception("Erro ao excluir TAC")
        db.rollback()
        flash('Erro ao excluir TAC.', 'danger')
    return redirect(url_for('formularios_tac_bp.listar_tacs'))

# API: autocomplete de alunos (uso interno)
@formularios_tac_bp.route('/api/alunos_autocomplete')
def alunos_autocomplete():
    q = request.args.get('q','').strip()
    db = get_db()
    if not q or len(q) < 1:
        rows = db.execute("SELECT id, nome FROM alunos ORDER BY id DESC LIMIT 30").fetchall()
    else:
        like = f"%{q.upper()}%"
        rows = db.execute("SELECT id, nome FROM alunos WHERE UPPER(nome) LIKE ? ORDER BY nome LIMIT 30", (like,)).fetchall()
    return jsonify([{'id': r['id'], 'nome': r['nome']} for r in rows])

# API: obter aluno por id (para popular serie/turma/responsavel)
@formularios_tac_bp.route('/api/aluno')
def api_aluno():
    aid = request.args.get('id')
    if not aid:
        return jsonify({'error':'missing id'}), 400
    db = get_db()
    try:
        row = db.execute("SELECT * FROM alunos WHERE id = ?", (aid,)).fetchone()
        if not row:
            return jsonify({'error':'not found'}), 404
        return jsonify(dict(row))
    except Exception as e:
        current_app.logger.exception('Erro ao buscar aluno por id')
        return jsonify({'error': 'internal', 'detail': str(e)}), 500

# -------------------------
# EXPORT DOCX (OPCIONAL)
# -------------------------
# Para usar esta rota é necessário instalar python-docx:
#   pip install python-docx
@formularios_tac_bp.route('/tac/<int:id>/export_docx')
@login_required
def export_docx(id):
    """
    Gera um .docx simples do TAC com os campos preenchidos e retorna como attachment.
    Requer python-docx (pip install python-docx).
    """
    db = get_db()
    row = db.execute("SELECT * FROM tacs WHERE id = ?", (id,)).fetchone()
    if not row:
        flash('TAC não encontrado.', 'warning')
        return redirect(url_for('formularios_tac_bp.listar_tacs'))
    tac = dict(row)
    # carregar aluno, obrigações, participantes como em tac_visualizar
    tac['aluno'] = None
    if tac.get('aluno_id'):
        a = db.execute("SELECT * FROM alunos WHERE id = ?", (tac['aluno_id'],)).fetchone()
        tac['aluno'] = dict(a) if a else None
    tac['obrigacoes'] = [r['descricao'] for r in db.execute("SELECT * FROM tac_obrigacoes WHERE tac_id = ? ORDER BY ordem", (id,)).fetchall()]
    tac['participantes'] = [dict(r) for r in db.execute("SELECT * FROM tac_participantes WHERE tac_id = ? ORDER BY ordem", (id,)).fetchall()]

    # montar documento
    doc = Document()
    doc.add_heading('TERMO DE ADEQUAÇÃO DE CONDUTA (TAC)', level=1)
    doc.add_paragraph(f'Número: {tac.get("numero","-")}')
    doc.add_paragraph(f'Escola: {tac.get("escola_text","-")}')
    aluno_nome = tac.get('aluno',{}).get('nome') if tac.get('aluno') else tac.get('aluno_nome')
    doc.add_paragraph(f'Aluno: {aluno_nome or "-"}')
    doc.add_paragraph(f'Série / Turma: {tac.get("serie","-")} / {tac.get("turma","-")}')
    doc.add_paragraph(f'Responsável: {tac.get("responsavel","-")}')
    doc.add_paragraph(f'Diretor: {tac.get("diretor_nome","-")}')
    doc.add_paragraph('---')
    doc.add_heading('Do Fato', level=2)
    doc.add_paragraph(tac.get('fato',''))
    doc.add_heading('Das Obrigações e Prazo', level=2)
    if tac.get('obrigacoes'):
        for ob in tac['obrigacoes']:
            doc.add_paragraph(ob, style='List Number')
    else:
        doc.add_paragraph('Sem obrigações registradas.')
    doc.add_heading('Participantes', level=2)
    if tac.get('participantes'):
        for p in tac['participantes']:
            doc.add_paragraph(f"{p.get('nome','-')} — {p.get('cargo','')}")
    else:
        doc.add_paragraph('Sem participantes registrados.')

    # assinar: adicionar linhas em branco - agora inclui Diretor e TODOS os participantes
    # Primeiro, director
    diretor_text = tac.get('diretor_nome') or 'Diretor(a) da Escola'
    doc.add_paragraph('\n\n\n__________________________\n' + f"Diretor(a): {diretor_text}")

    # Em seguida, uma linha de assinaturas para cada participante cadastrado (mantendo responsável entre eles)
    if tac.get('participantes'):
        for p in tac['participantes']:
            nome = p.get('nome') or '-'
            cargo = p.get('cargo') or ''
            # adiciona linha de assinatura + identificação do participante
            doc.add_paragraph('\n\n\n__________________________\n' + f"{nome} — {cargo}")
    else:
        # fallback: manter responsável caso não haja participantes
        resp = tac.get('responsavel') or '-'
        doc.add_paragraph('\n\n\n__________________________\n' + f"Responsável: {resp}")

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    filename = f"TAC-{tac.get('numero','id'+str(id))}.docx"
    return send_file(bio, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

from docxtpl import DocxTemplate
import io
from flask import send_file, current_app, session, flash, redirect, url_for
from database import get_db

from docxtpl import DocxTemplate
import io
from flask import send_file, current_app, session, flash, redirect, url_for
from database import get_db

# Cole esta função no final de blueprints/formularios_tac.py
@formularios_tac_bp.route('/tac/<int:id>/export_docx_template')
@login_required
def export_docx_template_docxtpl(id):
    """
    Gera um .docx a partir de templates/docx/tac_template.docx usando docxtpl.
    Retorna o .docx preenchido como download.
    """
    db = get_db()
    row = db.execute("SELECT * FROM tacs WHERE id = ?", (id,)).fetchone()
    if not row:
        flash('TAC não encontrado.', 'warning')
        return redirect(url_for('formularios_tac_bp.listar_tacs'))

    tac = dict(row)
    tac['aluno'] = None
    if tac.get('aluno_id'):
        a = db.execute("SELECT * FROM alunos WHERE id = ?", (tac['aluno_id'],)).fetchone()
        tac['aluno'] = dict(a) if a else None

    obrigacoes = [r['descricao'] for r in db.execute("SELECT * FROM tac_obrigacoes WHERE tac_id = ? ORDER BY ordem", (id,)).fetchall()]
    participantes = [dict(r) for r in db.execute("SELECT * FROM tac_participantes WHERE tac_id = ? ORDER BY ordem", (id,)).fetchall()]

    # caminho do template .docx (você salvou em templates/docx/tac_template.docx)
    template_path = current_app.config.get('TAC_DOCX_TEMPLATE_PATH', 'templates/docx/tac_template.docx')

    try:
        doc = DocxTemplate(template_path)
        context = {
            'numero': tac.get('numero', ''),
            'escola': tac.get('escola_text') or tac.get('cabecalho_nome', ''),
            'aluno_nome': (tac.get('aluno') and tac['aluno'].get('nome')) or tac.get('aluno_nome',''),
            'serie': tac.get('serie',''),
            'turma': tac.get('turma',''),
            'responsavel': tac.get('responsavel',''),
            'diretor': tac.get('diretor_nome',''),
            'fato': tac.get('fato',''),
            'prazo': tac.get('prazo',''),
            'obrigacoes': obrigacoes,            # lista de strings
            'participantes': participantes,      # lista de dicts with keys 'nome' and 'cargo'
            'data': (tac.get('updated_at') or tac.get('created_at') or '')[:10],
            'emitido_por': (session.get('username') or '')
        }

        bio = io.BytesIO()
        doc.render(context)
        doc.save(bio)
        bio.seek(0)

        filename = f"TAC-{tac.get('numero', 'id'+str(id))}.docx"
        return send_file(
            bio,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception:
        current_app.logger.exception("Erro ao gerar DOCX do TAC")
        flash('Erro ao gerar DOCX do TAC. Verifique o template e os placeholders.', 'danger')
        return redirect(url_for('formularios_tac_bp.tac_visualizar', id=id))