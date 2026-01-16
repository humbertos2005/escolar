# Trechos a integrar no blueprint disciplinar existente (blueprints/disciplinar.py).
# Este arquivo NÃO substitui seu blueprint, é um "patch" com funções a ser incorporado.
# Insira as funções abaixo no arquivo do blueprint disciplinar (importe get_db, jsonify, request, Blueprint, etc.)

from flask import request, jsonify, current_app
from escola.database import get_db

# 1) Endpoint para busca livre de faltas (autocomplete)
# URL sugerida: /api/faltas_busca?q=termo
# Retorna: [ { "id": 12, "descricao": "Faltar sem justificativa" }, ... ]

@disciplinar_bp.route('/api/faltas_busca')
def api_faltas_busca():
    q = request.args.get('q', '').strip()
    db = get_db()
    if not q:
        return jsonify([])

    q_like = f'%{q}%'
    rows = db.execute('''
        SELECT id, descricao
        FROM faltas_disciplinares
        WHERE descricao LIKE ?
        ORDER BY descricao
        LIMIT 50
    ''', (q_like,)).fetchall()

    result = [{'id': r['id'], 'descricao': r['descricao']} for r in rows]
    return jsonify(result)


# 2) Ajuste/Exemplo para o POST do tratamento (aceitar falta_disciplinar_ids CSV e tipo_falta[]).
# Se você já tem uma rota '/tratar_rfo/<id>' com POST, adapte a lógica de leitura abaixo.
# Exemplo de como ler esses campos no handler POST:

def processar_tratamento_post(ocorrencia_id):
    """
    Exemplo de trecho para ser usado dentro da view que trata o POST de tratamento do RFO.
    Deve ser integrado ao handler POST já existente.
    """
    db = get_db()
    # tipos de falta (lista)
    tipos = request.form.getlist('tipo_falta[]') or request.form.getlist('tipo_falta')  # compatibilidade
    tipos_csv = ','.join([t.strip() for t in tipos if t.strip()])

    # ids das faltas (campo hidden com CSV)
    falta_ids_csv = request.form.get('falta_disciplinar_ids', '').strip()
    falta_ids = [fid.strip() for fid in falta_ids_csv.split(',') if fid.strip()]

    # outros campos
    reincidencia = int(request.form.get('reincidencia', 0))
    medida_aplicada = request.form.get('medida_aplicada', '').strip()
    despacho_gestor = request.form.get('despacho_gestor', '').strip()
    data_despacho = request.form.get('data_despacho', '').strip() or None

    # Exemplo: atualizar a ocorrência
    db.execute('''
        UPDATE ocorrencias
        SET tipo_falta = ?, medida_aplicada = ?, reincidencia = ?, despacho_gestor = ?, data_despacho = ?, status = ?
        WHERE id = ?
    ''', (tipos_csv, medida_aplicada, reincidencia, despacho_gestor, data_despacho, 'TRATADO', ocorrencia_id))

    # Exemplo: salvar faltas relacionadas — recomendo criar tabela ocorrencias_faltas (ocorrencia_id, falta_id)
    # Primeiro, deletar vínculos antigos (se existir)
    try:
        db.execute('DELETE FROM ocorrencias_faltas WHERE ocorrencia_id = ?', (ocorrencia_id,))
    except Exception:
        # se tabela não existir, você pode optar por armazenar os ids em uma coluna 'falta_ids' na tabela ocorrencias
        pass

    for fid in falta_ids:
        try:
            db.execute('INSERT INTO ocorrencias_faltas (ocorrencia_id, falta_id) VALUES (?, ?)', (ocorrencia_id, fid))
        except Exception:
            # ignore erros individuais (p.ex. id inválido) - logue se necessário
            pass

    db.commit()
    return True

# NOTA: Integre processar_tratamento_post(ocorrencia_id) no handler POST real do seu blueprint.
