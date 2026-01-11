from flask import Blueprint, render_template

documentos_bp = Blueprint('documentos_bp', __name__, url_prefix='/documentos')

@documentos_bp.route('/gerenciar_rfos')
def gerenciar_rfos():
    return render_template('documentos/gerenciar_rfos.html')