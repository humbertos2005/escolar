# -*- coding: utf-8 -*-
from flask import Flask, render_template, g, session, redirect, url_for, flash, jsonify, request
from flask_moment import Moment
from dotenv import load_dotenv
import os
import locale

from escola.blueprints.bimestres import bimestres_bp
from escola.blueprints.auth import auth_bp
from escola.blueprints.alunos import alunos_bp
from escola.blueprints.disciplinar import disciplinar_bp
from escola.blueprints.cadastros import cadastros_bp
from escola.blueprints.formularios import formularios_bp
from escola.blueprints.formularios_prontuario import formularios_prontuario_bp
from escola.blueprints.formularios_tac import formularios_tac_bp
from escola.blueprints.visualizacoes import visualizacoes_bp
from escola.blueprints.relatorios_disciplinares import relatorios_disciplinares_bp
from escola.blueprints.documentos import documentos_bp

# Se precisar utilit�rios globais:
from escola.blueprints import utils

# SQLAlchemy setup
from escola.database import init_db, close_db

load_dotenv()

# Configurar localiza��o brasileira
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except:
            print("   [AVISO] N�o foi poss�vel configurar localiza��o PT-BR")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave-secreta-gestao-escolar-2025-v2")

# Configura��es Flask
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MOMENT_DEFAULT_FORMAT'] = 'DD/MM/YYYY'
# Caso seu modelo de dados precise referenciar o caminho do banco, padronize para SQLAlchemy
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL") ou equivalente

# Inicializar o banco (migra��es/models)
init_db()  # Supondo que agora isso use SQLAlchemy

# Registrar blueprints (ordem importa para evitar colis�es de rota como observado)
app.register_blueprint(relatorios_disciplinares_bp, url_prefix='/relatorios_disciplinares')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(alunos_bp, url_prefix='/alunos')
app.register_blueprint(disciplinar_bp, url_prefix='/disciplinar')
app.register_blueprint(cadastros_bp, url_prefix='/cadastros')
app.register_blueprint(formularios_prontuario_bp, url_prefix='/formularios')
app.register_blueprint(formularios_tac_bp, url_prefix='/formularios')
app.register_blueprint(formularios_bp, url_prefix='/formularios')
app.register_blueprint(visualizacoes_bp, url_prefix='/visualizacoes')
app.register_blueprint(bimestres_bp)
app.register_blueprint(documentos_bp, url_prefix="/documentos")

# Registrar rota para aplicar FMDs a partir de RFOs
try:
    from escola.blueprints.apply_fmds import bp_apply_fmds
    app.register_blueprint(bp_apply_fmds)
except Exception:
    pass

moment = Moment(app)

from datetime import datetime

def datetimeformat(value, format="%d/%m/%Y"):
    if not value:
        return ""
    try:
        # Se vier s� 'YYYY-MM-DD'
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            dt = datetime.strptime(value, "%Y-%m-%d")
        else:
            dt = datetime.fromisoformat(value)
        return dt.strftime(format)
    except Exception:
        return value

app.jinja_env.filters['datetimeformat'] = datetimeformat

# Handler para fechar a sess�o SQLAlchemy ap�s cada request
@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db()

from escola.database import get_db, close_db
from escola.models_sqlalchemy import Usuario  # ajuste o nome conforme seu projeto

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.query(Usuario).filter_by(id=user_id).first()

# N�o precisa mais do teardown_db separado, j� inclu�mos ao final do bloco anterior:
# @app.teardown_appcontext
# def teardown_db(e=None):
#     close_db(e)

@app.context_processor
def inject_globals():
    """Injeta vari�veis globais em todos os templates"""
    from datetime import datetime
    return dict(
        NIVEL_MAP=utils.NIVEL_MAP,
        session=session,
        now=datetime.now
    )

@app.template_filter('data_br')
def formatar_data_br(data_str):
    """Filtro personalizado para formatar datas no padr�o brasileiro"""
    if not data_str:
        return '-'

    from datetime import datetime

    try:
        # Tentar v�rios formatos de entrada
        formatos = [
            '%Y-%m-%d',           # 2025-01-24
            '%Y-%m-%d %H:%M:%S',  # 2025-01-24 14:30:00
            '%d/%m/%Y',           # 24/01/2025
        ]

        for formato in formatos:
            try:
                data_obj = datetime.strptime(str(data_str).strip(), formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue

        # Se nenhum formato funcionou, retorna o valor original
        return data_str
    except:
        return data_str

from markupsafe import Markup, escape

@app.template_filter('nl2br')
def nl2br_filter(value):
    """Converte quebras de linha em <br> preservando escape de HTML."""
    if value is None:
        return ''
    # escape para evitar XSS e depois converte quebras em <br>
    escaped = escape(str(value))
    return Markup(escaped.replace('\r\n', '\n').replace('\r', '\n').replace('\n', Markup('<br>\n')))

@app.template_filter('datetime_br')
def formatar_datetime_br(data_str):
    """Filtro para formatar data e hora no padr�o brasileiro"""
    if not data_str:
        return '-'

    from datetime import datetime

    try:
        formatos = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]

        for formato in formatos:
            try:
                data_obj = datetime.strptime(str(data_str).strip(), formato)
                return data_obj.strftime('%d/%m/%Y �s %H:%M')
            except ValueError:
                continue

        return data_str
    except:
        return data_str

from escola.models_sqlalchemy import Aluno, Ocorrencia, Usuario, FichaMedidaDisciplinar, FaltaDisciplinar  # ajuste nomes conforme models
from escola.database import get_db

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('auth_bp.login'))
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@utils.login_required
def dashboard():
    db = get_db()
    total_alunos = db.query(Aluno).count()
    total_ocorrencias = db.query(Ocorrencia).filter_by(status="TRATADO").count()
    rfos_pendentes = db.query(Ocorrencia).filter_by(status="AGUARDANDO TRATAMENTO").count()
    total_usuarios = db.query(Usuario).count()
    total_fmd = db.query(FichaMedidaDisciplinar).count()

    return render_template('dashboard.html',
                           total_alunos=total_alunos,
                           total_ocorrencias=total_ocorrencias,
                           rfos_pendentes=rfos_pendentes,
                           total_usuarios=total_usuarios,
                           total_fmd=total_fmd)

@app.route('/api/dashboard_stats')
@utils.login_required
def api_dashboard_stats():
    db = get_db()
    total_alunos = db.query(Aluno).count()
    total_ocorrencias = db.query(Ocorrencia).filter_by(status="TRATADO").count()
    rfos_pendentes = db.query(Ocorrencia).filter_by(status="AGUARDANDO TRATAMENTO").count()
    total_usuarios = db.query(Usuario).count()
    total_fmd = db.query(FichaMedidaDisciplinar).count()

    return jsonify({
        'total_alunos': total_alunos,
        'total_ocorrencias': total_ocorrencias,
        'rfos_pendentes': rfos_pendentes,
        'total_usuarios': total_usuarios,
        'total_fmd': total_fmd
    })

@app.route('/api/faltas_por_natureza')
@utils.login_required
def api_faltas_por_natureza():
    natureza = request.args.get('natureza', '').upper()
    db = get_db()

    faltas = db.query(FaltaDisciplinar).filter_by(natureza=natureza).order_by(FaltaDisciplinar.descricao).all()
    return jsonify([{'id': f.id, 'descricao': f.descricao} for f in faltas])

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

# Fun��o administrativa antiga baseada em SQLite N�O se aplica ao SQLAlchemy!
# Recomenda-se substituir este bloco por ferramentas de migra��o como Alembic.
def inicializar_e_migrar():
    print("="*60)
    print("INICIANDO SISTEMA DE GEST�O ESCOLAR")
    print("="*60)
    print("Use Alembic e models_sqlalchemy.py para controle/migra��o de estrutura.")
    print("� Para criar as tabelas: veja modelos em 'models_sqlalchemy.py'.")
    print("� Para criar admin inicial, adapte fun��o para usar SQLAlchemy.")
    print("="*60)

# --- AUTO: registrar blueprint de ATAs (movido para antes do main) ---
try:
    from escola.blueprints.formularios_ata import formularios_ata_bp
    app.register_blueprint(formularios_ata_bp, url_prefix='/formularios/atas')
    print("Blueprint 'formularios_ata_bp' registrada (moved auto).")
except Exception as _e:
    print("Aviso: falha ao registrar 'formularios_ata_bp' automaticamente:", _e)
# --- fim AUTO ---

if __name__ == '__main__':
    # Se quiser alguma inicializa��o/migra��o: usar Alembic ou m�todos do SQLAlchemy
    # inicializar_e_migrar()  # <<< Comentado! Veja orienta��es no bloco anterior!
    app.run(debug=True)

# --- inject logo as base64 data uri into all templates (used by PDF template) ---
import os, base64, mimetypes
from flask import current_app

def _read_logo_data():
    try:
        p = os.path.join(current_app.root_path, "static", "logo_topo.png")
        if not os.path.exists(p):
            # try other typical extensions
            for ext in (".png", ".jpg", ".jpeg", ".svg"):
                px = os.path.join(current_app.root_path, "static", "logo_topo" + ext)
                if os.path.exists(px):
                    p = px
                    break
        if not os.path.exists(p):
            return None
        mime = mimetypes.guess_type(p)[0] or "image/png"
        with open(p, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{data}"
    except Exception:
        return None

@app.context_processor
def inject_logo_data():
    try:
        return {"LOGO_DATA_URI": _read_logo_data()}
    except Exception:
        return {"LOGO_DATA_URI": None}
# --- end inject ---

# --- registrar blueprint de data_matricula (adicionado automaticamente) ---
try:
    from escola.blueprints.matricula import bp_matricula
    app.register_blueprint(bp_matricula)
except Exception:
    # se algo falhar aqui (por ordem de imports ou contexto), n�o quebramos a aplica��o
    pass
# --- fim registro matricula ---
