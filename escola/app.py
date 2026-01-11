# -*- coding: utf-8 -*-
from flask import Flask, render_template, g, session, redirect, url_for, flash, jsonify, request
from database import init_db, close_db, get_db, DATABASE
import sqlite3
import os
import locale
from blueprints.bimestres import bimestres_bp
from flask_moment import Moment
from models import criar_tabelas, criar_admin_inicial, migrar_estrutura_antiga_ocorrencias
from blueprints.auth import auth_bp
from blueprints.alunos import alunos_bp
from blueprints.disciplinar import disciplinar_bp
from blueprints.cadastros import cadastros_bp
from blueprints.formularios import formularios_bp
# novo blueprint de ProntuÃ¡rios (adicionado)
from blueprints.formularios_prontuario import formularios_prontuario_bp
# novo blueprint de TACS (Termos de AdequaÃ§Ã£o de Conduta)
from blueprints.formularios_tac import formularios_tac_bp
from blueprints.visualizacoes import visualizacoes_bp
from blueprints import utils
from blueprints.relatorios_disciplinares import relatorios_disciplinares_bp
from blueprints.documentos import documentos_bp

# Configurar localizaÃ§Ã£o brasileira
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except:
            print("   [AVISO] NÃ£o foi possÃ­vel configurar localizaÃ§Ã£o PT-BR")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave-secreta-gestao-escolar-2025-v2")
app.config['DATABASE'] = DATABASE
app.register_blueprint(relatorios_disciplinares_bp, url_prefix='/relatorios_disciplinares')

from datetime import datetime

def datetimeformat(value, format="%d/%m/%Y"):
    if not value:
        return ""
    try:
        # Se vier só 'YYYY-MM-DD'
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            dt = datetime.strptime(value, "%Y-%m-%d")
        else:
            dt = datetime.fromisoformat(value)
        return dt.strftime(format)
    except Exception:
        return value

app.jinja_env.filters['datetimeformat'] = datetimeformat

# Configurar Flask-Moment com localizaÃ§Ã£o brasileira
moment = Moment(app)
app.config['MOMENT_DEFAULT_FORMAT'] = 'DD/MM/YYYY'

app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# blueprints existentes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(alunos_bp, url_prefix='/alunos')
app.register_blueprint(disciplinar_bp, url_prefix='/disciplinar')
app.register_blueprint(cadastros_bp, url_prefix='/cadastros')

# Registramos primeiro o blueprint especÃ­fico de ProntuÃ¡rios para evitar
# colisÃµes de rota com formularios_bp (ambos usavam '/prontuario/...').
# Assim, as rotas de visualizar/editar do blueprint de prontuÃ¡rios sÃ£o
# resolvidas corretamente pelo Flask.
app.register_blueprint(formularios_prontuario_bp, url_prefix='/formularios')

# Registrar blueprint dos TACS (Termos de AdequaÃ§Ã£o de Conduta)
app.register_blueprint(formularios_tac_bp, url_prefix='/formularios')

# Mantemos o blueprint genÃ©rico de formulÃ¡rios em seguida
app.register_blueprint(formularios_bp, url_prefix='/formularios')

app.register_blueprint(visualizacoes_bp, url_prefix='/visualizacoes')
app.register_blueprint(bimestres_bp)
app.register_blueprint(documentos_bp, url_prefix="/documentos")


# Registrar rota para aplicar FMDs a partir de RFOs
try:
    from blueprints.apply_fmds import bp_apply_fmds
    app.register_blueprint(bp_apply_fmds)
except Exception:
    pass

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM usuarios WHERE id = ?', (user_id,)
        ).fetchone()

@app.teardown_appcontext
def teardown_db(e=None):
    close_db(e)

@app.context_processor
def inject_globals():
    """Injeta variÃ¡veis globais em todos os templates"""
    from datetime import datetime
    return dict(
        NIVEL_MAP=utils.NIVEL_MAP,
        session=session,
        now=datetime.now
    )

@app.template_filter('data_br')
def formatar_data_br(data_str):
    """Filtro personalizado para formatar datas no padrÃ£o brasileiro"""
    if not data_str:
        return '-'

    from datetime import datetime

    try:
        # Tentar vÃ¡rios formatos de entrada
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

# Adicione este filtro em app.py (coloque-o junto dos outros @app.template_filter)
from markupsafe import Markup, escape

@app.template_filter('nl2br')
def nl2br_filter(value):
    """Converte quebras de linha em <br> preservando escape de HTML."""
    if value is None:
        return ''
    # escape para evitar XSS e depois converte quebras em <br>
    escaped = escape(str(value))
    # usa <br>\n para manter alguma legibilidade no HTML gerado
    return Markup(escaped.replace('\r\n', '\n').replace('\r', '\n').replace('\n', Markup('<br>\n')))

@app.template_filter('datetime_br')
def formatar_datetime_br(data_str):
    """Filtro para formatar data e hora no padrÃ£o brasileiro"""
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
                return data_obj.strftime('%d/%m/%Y Ã s %H:%M')
            except ValueError:
                continue

        return data_str
    except:
        return data_str

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('auth_bp.login'))
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@utils.login_required
def dashboard():
    db = get_db()
    total_alunos = db.execute('SELECT COUNT(id) FROM alunos').fetchone()[0]
    total_ocorrencias = db.execute("SELECT COUNT(id) FROM ocorrencias WHERE status = 'TRATADO'").fetchone()[0]
    rfos_pendentes = db.execute("SELECT COUNT(id) FROM ocorrencias WHERE status = 'AGUARDANDO TRATAMENTO'").fetchone()[0]
    total_usuarios = db.execute('SELECT COUNT(id) FROM usuarios').fetchone()[0]
    total_fmd = db.execute('SELECT COUNT(id) FROM ficha_medida_disciplinar').fetchone()[0]

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
    total_alunos = db.execute('SELECT COUNT(id) FROM alunos').fetchone()[0]
    total_ocorrencias = db.execute("SELECT COUNT(id) FROM ocorrencias WHERE status = 'TRATADO'").fetchone()[0]
    rfos_pendentes = db.execute("SELECT COUNT(id) FROM ocorrencias WHERE status = 'AGUARDANDO TRATAMENTO'").fetchone()[0]
    total_usuarios = db.execute('SELECT COUNT(id) FROM usuarios').fetchone()[0]
    total_fmd = db.execute('SELECT COUNT(id) FROM ficha_medida_disciplinar').fetchone()[0]

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

    faltas = db.execute('''
        SELECT id, descricao 
        FROM faltas_disciplinares 
        WHERE natureza = ?
        ORDER BY descricao
    ''', (natureza,)).fetchall()

    return jsonify([{'id': f['id'], 'descricao': f['descricao']} for f in faltas])

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

def inicializar_e_migrar():
    print("="*60)
    print("INICIANDO SISTEMA DE GESTÃƒO ESCOLAR")
    print("="*60)
    print("1. Criando/verificando estrutura do banco de dados...")
    with app.app_context():
        criar_tabelas()
        print("   âœ“ Tabelas verificadas/criadas com sucesso!")

        print("1.1. Verificando/adicionando colunas de RFO Ã  tabela 'ocorrencias'...")
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("PRAGMA table_info(ocorrencias);")
            colunas = [col[1] for col in cursor.fetchall()]

            if 'relato_observador' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN relato_observador TEXT NOT NULL DEFAULT '';")
                print("   [MIGRAÃ‡ÃƒO] Coluna 'relato_observador' adicionada Ã  tabela 'ocorrencias'.")

            if 'advertencia_oral' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN advertencia_oral TEXT NOT NULL DEFAULT 'nao';")
                print("   [MIGRAÃ‡ÃƒO] Coluna 'advertencia_oral' adicionada Ã  tabela 'ocorrencias'.")

            if 'material_recolhido' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN material_recolhido TEXT;")
                print("   [MIGRAÃ‡ÃƒO] Coluna 'material_recolhido' adicionada Ã  tabela 'ocorrencias'.")

            if 'infracao_id' in colunas and 'tipo_ocorrencia_id' not in colunas:
                print("   [AVISO] Coluna 'infracao_id' detectada. Considere migrar para 'tipo_ocorrencia_id'.")
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN tipo_ocorrencia_id INTEGER;")
                print("   [MIGRAÃ‡ÃƒO] Coluna 'tipo_ocorrencia_id' adicionada.")
            elif 'tipo_ocorrencia_id' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN tipo_ocorrencia_id INTEGER;")
                print("   [MIGRAÃ‡ÃƒO] Coluna 'tipo_ocorrencia_id' adicionada.")

            db.commit()
            print("   âœ“ Colunas de RFO verificadas/adicionadas com sucesso!")
        except sqlite3.OperationalError as e:
            print(f"   [AVISO] Falha ao verificar/adicionar colunas Ã  'ocorrencias': {e}")
            db.rollback()

    print("2. Verificando usuÃ¡rio administrador inicial...")
    db_conn = sqlite3.connect(DATABASE)
    db_conn.row_factory = sqlite3.Row
    try:
        criar_admin_inicial(db_conn)
        print("   âœ“ UsuÃ¡rio administrador verificado!")
    except Exception as e:
        print(f"   âœ— Erro ao criar admin inicial: {e}")
    finally:
        db_conn.close()

    print("3. Verificando necessidade de migraÃ§Ã£o de dados...")
    migracao_info = migrar_estrutura_antiga_ocorrencias()
    if migracao_info['ocorrencias_migradas'] > 0:
        print(f"   âœ“ {migracao_info['ocorrencias_migradas']} ocorrÃªncias migradas!")
    else:
        print("   âœ“ Nenhuma migraÃ§Ã£o necessÃ¡ria!")
    print("="*60)


# --- AUTO: registrar blueprint de ATAs (movido para antes do main) ---
try:
    from blueprints.formularios_ata import formularios_ata_bp
    app.register_blueprint(formularios_ata_bp, url_prefix='/formularios/atas')
    print("Blueprint 'formularios_ata_bp' registrada (moved auto).")
except Exception as _e:
    print("Aviso: falha ao registrar 'formularios_ata_bp' automaticamente:", _e)
# --- fim AUTO ---
if __name__ == '__main__':
    inicializar_e_migrar()
    app.run(debug=True)

# Registrar normalização automática de campos de alunos






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
    from blueprints.matricula import bp_matricula
    app.register_blueprint(bp_matricula)
except Exception:
    # se algo falhar aqui (por ordem de imports ou contexto), não quebramos a aplicação
    pass
# --- fim registro matricula ---
