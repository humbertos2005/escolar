# Trecho para integrar em blueprints/disciplinar.py
# Substitua a função registrar_fmd atual por esta implementação (ela usa os novos campos)
# Também adiciona três novos endpoints de autocomplete:
#  - /disciplinar/api/comportamentos_busca?q=...
#  - /disciplinar/api/pontuacoes_busca?q=...
#  - /disciplinar/api/usuarios_busca?q=...
#
# Observação: adapte nomes de tabelas se seu schema usar outras convenções.

from flask import current_app

@disciplinar_bp.route('/registrar_fmd', methods=['GET', 'POST'])
@admin_secundario_required
def registrar_fmd():
    """Registra uma nova Ficha de Medida Disciplinar com novos campos solicitados."""
    db = get_db()
    fmd_id_gerado = get_proximo_fmd_id()
    faltas = get_faltas_disciplinares()
    
    # opcional: carregar lista de comportamentos / pontuações para o frontend se quiser
    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id')
        rfo_id = request.form.get('rfo_id', '').strip()
        data_fmd = request.form.get('data_fmd')
        # tipos agora podem vir via campo oculto tipo_falta_list (CSV) ou checkboxes tipo_falta[]
        tipos_raw = request.form.get('tipo_falta_list', '').strip()
        if tipos_raw:
            tipos_list = [t.strip() for t in tipos_raw.split(',') if t.strip()]
            tipo_falta = ','.join(tipos_list)
        else:
            tipo_falta = ','.join([t for t in request.form.getlist('tipo_falta[]') if t.strip()])

        medida_aplicada = request.form.get('medida_aplicada')
        descricao_falta = request.form.get('descricao_falta', '').strip()
        # novos campos:
        data_falta = request.form.get('data_falta', '').strip()
        relato_faltas = request.form.get('relato_faltas', '').strip()
        itens_faltas_ids = request.form.get('itens_faltas_ids', '').strip()  # CSV
        comportamento_id = request.form.get('comportamento_id')  # id opcional
        pontuacao_id = request.form.get('pontuacao_id')  # id opcional
        comparecimento_responsavel = request.form.get('comparecimento_responsavel', '0')
        try:
            comparecimento_responsavel = 1 if str(comparecimento_responsavel) in ['1', 'true', 'True', 'on'] else 0
        except Exception:
            comparecimento_responsavel = 0
        prazo_comparecimento = request.form.get('prazo_comparecimento', '').strip()
        atenuantes = request.form.get('atenuantes', '').strip() or 'Não há'
        agravantes = request.form.get('agravantes', '').strip() or 'Não há'
        gestor_id = request.form.get('gestor_id') or session.get('user_id')

        observacoes = request.form.get('observacoes', '').strip()

        error = None
        if not aluno_id:
            error = 'Aluno é obrigatório.'
        elif not data_fmd:
            error = 'Data é obrigatória.'
        elif not tipo_falta:
            error = 'Tipo de falta é obrigatório.'
        elif not medida_aplicada:
            error = 'Medida aplicada é obrigatória.'
        # descrição_falta não é mais obrigatória aqui; pode usar relato_faltas

        if error is None:
            try:
                fmd_id_final = get_proximo_fmd_id(incrementar=True)

                db.execute('''
                    INSERT INTO ficha_medida_disciplinar 
                    (fmd_id, aluno_id, rfo_id, data_fmd, tipo_falta, medida_aplicada, 
                     descricao_falta, observacoes, responsavel_id, status,
                     data_falta, relato_faltas, itens_faltas_ids,
                     comportamento_id, pontuacao_id, comparecimento_responsavel,
                     prazo_comparecimento, atenuantes, agravantes, gestor_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATIVA', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fmd_id_final,
                    aluno_id,
                    rfo_id if rfo_id else None,
                    data_fmd,
                    tipo_falta,
                    medida_aplicada,
                    descricao_falta,
                    observacoes,
                    session.get('user_id'),
                    # novos campos
                    data_falta if data_falta else None,
                    relato_faltas if relato_faltas else None,
                    itens_faltas_ids if itens_faltas_ids else None,
                    int(comportamento_id) if comportamento_id and str(comportamento_id).isdigit() else None,
                    int(pontuacao_id) if pontuacao_id and str(pontuacao_id).isdigit() else None,
                    comparecimento_responsavel,
                    prazo_comparecimento if prazo_comparecimento else None,
                    atenuantes,
                    agravantes,
                    int(gestor_id) if gestor_id and str(gestor_id).isdigit() else session.get('user_id')
                ))

                db.commit()
                flash(f'FMD {fmd_id_final} registrada com sucesso!', 'success')
                return redirect(url_for('visualizacoes_bp.listar_fmd'))
            except sqlite3.Error as e:
                db.rollback()
                current_app.logger.exception("Erro ao registrar FMD")
                flash(f'Erro ao registrar FMD: {e}', 'danger')
        else:
            flash(error, 'danger')

    # GET -> render form
    return render_template('disciplinar/registrar_fmd.html',
                         fmd_id_gerado=fmd_id_gerado,
                         faltas=faltas,
                         medidas_map=MEDIDAS_MAP,
                         g=g)


# Autocomplete para comportamentos
@disciplinar_bp.route('/api/comportamentos_busca')
def api_comportamentos_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        rows = db.execute('''
            SELECT DISTINCT id, nome
            FROM comportamentos
            WHERE nome LIKE ? COLLATE NOCASE
            ORDER BY nome
            LIMIT 50
        ''', (q_like,)).fetchall()
    except sqlite3.Error:
        # tabela pode não existir; retorna vazio
        return jsonify([])
    result = [{'id': r['id'], 'nome': r['nome']} for r in rows]
    return jsonify(result)

# Autocomplete para pontuações
@disciplinar_bp.route('/api/pontuacoes_busca')
def api_pontuacoes_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    try:
        rows = db.execute('''
            SELECT DISTINCT id, descricao
            FROM pontuacoes
            WHERE descricao LIKE ? COLLATE NOCASE
            ORDER BY descricao
            LIMIT 50
        ''', (q_like,)).fetchall()
    except sqlite3.Error:
        return jsonify([])
    result = [{'id': r['id'], 'descricao': r['descricao']} for r in rows]
    return jsonify(result)

# Autocomplete para usuários (gestor)
@disciplinar_bp.route('/api/usuarios_busca')
def api_usuarios_busca():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    db = get_db()
    q_like = f'%{q}%'
    rows = db.execute('''
        SELECT id, username, full_name
        FROM usuarios
        WHERE username LIKE ? OR full_name LIKE ?
        ORDER BY username
        LIMIT 50
    ''', (q_like, q_like)).fetchall()
    result = [{'id': r['id'], 'username': r['username'], 'full_name': r['full_name']} for r in rows]
    return jsonify(result)