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
# novo blueprint de Prontuários (adicionado)
from blueprints.formularios_prontuario import formularios_prontuario_bp
# novo blueprint de TACS (Termos de Adequação de Conduta)
from blueprints.formularios_tac import formularios_tac_bp
from blueprints.visualizacoes import visualizacoes_bp
from blueprints import utils

# Configurar localização brasileira
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except:
            print("   [AVISO] Não foi possível configurar localização PT-BR")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave-secreta-gestao-escolar-2025-v2")
app.config['DATABASE'] = DATABASE

# Configurar Flask-Moment com localização brasileira
moment = Moment(app)
app.config['MOMENT_DEFAULT_FORMAT'] = 'DD/MM/YYYY'

app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# blueprints existentes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(alunos_bp, url_prefix='/alunos')
app.register_blueprint(disciplinar_bp, url_prefix='/disciplinar')
app.register_blueprint(cadastros_bp, url_prefix='/cadastros')

# Registramos primeiro o blueprint específico de Prontuários para evitar
# colisões de rota com formularios_bp (ambos usavam '/prontuario/...').
# Assim, as rotas de visualizar/editar do blueprint de prontuários são
# resolvidas corretamente pelo Flask.
app.register_blueprint(formularios_prontuario_bp, url_prefix='/formularios')

# Registrar blueprint dos TACS (Termos de Adequação de Conduta)
app.register_blueprint(formularios_tac_bp, url_prefix='/formularios')

# Mantemos o blueprint genérico de formulários em seguida
app.register_blueprint(formularios_bp, url_prefix='/formularios')

app.register_blueprint(visualizacoes_bp, url_prefix='/visualizacoes')
app.register_blueprint(bimestres_bp)

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
    """Injeta variáveis globais em todos os templates"""
    from datetime import datetime
    return dict(
        NIVEL_MAP=utils.NIVEL_MAP,
        session=session,
        now=datetime.now
    )

@app.template_filter('data_br')
def formatar_data_br(data_str):
    """Filtro personalizado para formatar datas no padrão brasileiro"""
    if not data_str:
        return '-'

    from datetime import datetime

    try:
        # Tentar vários formatos de entrada
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
    """Filtro para formatar data e hora no padrão brasileiro"""
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
                return data_obj.strftime('%d/%m/%Y às %H:%M')
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
    print("INICIANDO SISTEMA DE GESTÃO ESCOLAR")
    print("="*60)
    print("1. Criando/verificando estrutura do banco de dados...")
    with app.app_context():
        criar_tabelas()
        print("   ✓ Tabelas verificadas/criadas com sucesso!")

        print("1.1. Verificando/adicionando colunas de RFO à tabela 'ocorrencias'...")
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("PRAGMA table_info(ocorrencias);")
            colunas = [col[1] for col in cursor.fetchall()]

            if 'relato_observador' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN relato_observador TEXT NOT NULL DEFAULT '';")
                print("   [MIGRAÇÃO] Coluna 'relato_observador' adicionada à tabela 'ocorrencias'.")

            if 'advertencia_oral' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN advertencia_oral TEXT NOT NULL DEFAULT 'nao';")
                print("   [MIGRAÇÃO] Coluna 'advertencia_oral' adicionada à tabela 'ocorrencias'.")

            if 'material_recolhido' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN material_recolhido TEXT;")
                print("   [MIGRAÇÃO] Coluna 'material_recolhido' adicionada à tabela 'ocorrencias'.")

            if 'infracao_id' in colunas and 'tipo_ocorrencia_id' not in colunas:
                print("   [AVISO] Coluna 'infracao_id' detectada. Considere migrar para 'tipo_ocorrencia_id'.")
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN tipo_ocorrencia_id INTEGER;")
                print("   [MIGRAÇÃO] Coluna 'tipo_ocorrencia_id' adicionada.")
            elif 'tipo_ocorrencia_id' not in colunas:
                cursor.execute("ALTER TABLE ocorrencias ADD COLUMN tipo_ocorrencia_id INTEGER;")
                print("   [MIGRAÇÃO] Coluna 'tipo_ocorrencia_id' adicionada.")

            db.commit()
            print("   ✓ Colunas de RFO verificadas/adicionadas com sucesso!")
        except sqlite3.OperationalError as e:
            print(f"   [AVISO] Falha ao verificar/adicionar colunas à 'ocorrencias': {e}")
            db.rollback()

    print("2. Verificando usuário administrador inicial...")
    db_conn = sqlite3.connect(DATABASE)
    db_conn.row_factory = sqlite3.Row
    try:
        criar_admin_inicial(db_conn)
        print("   ✓ Usuário administrador verificado!")
    except Exception as e:
        print(f"   ✗ Erro ao criar admin inicial: {e}")
    finally:
        db_conn.close()

    print("3. Verificando necessidade de migração de dados...")
    migracao_info = migrar_estrutura_antiga_ocorrencias()
    if migracao_info['ocorrencias_migradas'] > 0:
        print(f"   ✓ {migracao_info['ocorrencias_migradas']} ocorrências migradas!")
    else:
        print("   ✓ Nenhuma migração necessária!")
    print("="*60)

if __name__ == '__main__':
    inicializar_e_migrar()
    app.run(debug=True)
