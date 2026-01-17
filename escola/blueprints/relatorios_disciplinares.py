from flask import Blueprint, render_template, request, send_file, make_response
from database import get_db
from .utils import admin_required
from datetime import datetime
from weasyprint import HTML
import io
import csv

relatorios_disciplinares_bp = Blueprint('relatorios_disciplinares_bp', __name__, url_prefix='/relatorios_disciplinares')

def coletar_parametros_form():
    periodo = request.form.get('periodo')
    tipo_falta_ids = request.form.getlist('tipo_falta')
    data_inicio = request.form.get('data_inicio')
    data_fim = request.form.get('data_fim')

    ids_filtrar = []
    for item in tipo_falta_ids:
        try:
            id_falta = int(item.split(" - ")[0])
            ids_filtrar.append(id_falta)
        except Exception:
            pass

    if periodo == "semestre1":
        ano = datetime.now().year
        data_inicio = f"{ano}-01-01"
        data_fim = f"{ano}-06-30"
    elif periodo == "semestre2":
        ano = datetime.now().year
        data_inicio = f"{ano}-07-01"
        data_fim = f"{ano}-12-31"
    elif periodo == "geral":
        ano = datetime.now().year
        data_inicio = f"{ano}-01-01"
        data_fim = datetime.now().strftime('%Y-%m-%d')
    elif periodo == "personalizado":
        data_inicio = data_inicio or "1900-01-01"
        data_fim = data_fim or datetime.now().strftime('%Y-%m-%d')
    else:
        data_inicio = None
        data_fim = None

    parametros = {
        'periodo': periodo,
        'tipo_falta': tipo_falta_ids,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'ids_filtrar': ids_filtrar
    }
    return parametros

def get_ocorrencias_estatisticas(data_inicio, data_fim, ids_filtrar):
    db = get_db()
    sql = """
        SELECT o.id, o.data_ocorrencia, o.medida_aplicada,
               a.nome AS aluno_nome, a.serie, a.turma,
               f.id AS falta_id, f.natureza, f.descricao
        FROM ocorrencias o
        JOIN ocorrencias_faltas ofa ON ofa.ocorrencia_id = o.id
        JOIN faltas_disciplinares f ON f.id = ofa.falta_id
        JOIN alunos a ON a.id = o.aluno_id
        WHERE 1=1
    """
    params = []
    if data_inicio:
        sql += " AND o.data_ocorrencia >= ?"
        params.append(data_inicio)
    if data_fim:
        sql += " AND o.data_ocorrencia <= ?"
        params.append(data_fim)
    if ids_filtrar:
        sql += " AND f.id IN ({})".format(','.join(['?'] * len(ids_filtrar)))
        params.extend(ids_filtrar)
    sql += " ORDER BY o.data_ocorrencia DESC, o.id DESC"
    ocorrencias = db.execute(sql, params).fetchall()
    estatisticas = {}
    for oc in ocorrencias:
        key = f"{oc['falta_id']} - {oc['descricao']}"
        estatisticas[key] = estatisticas.get(key, 0) + 1
    return ocorrencias, estatisticas

@relatorios_disciplinares_bp.route('/', methods=['GET', 'POST'])
@admin_required
def index():
    db = get_db()
    faltas = db.execute("SELECT id, natureza, descricao FROM faltas_disciplinares ORDER BY id").fetchall()
    faltas_opcoes = [f"{f[0]} - {f[2]}" for f in faltas]

    resultado = None
    parametros = {}
    ocorrencias = []
    estatisticas = {}

    if request.method == 'POST':
        parametros = coletar_parametros_form()
        data_inicio = parametros['data_inicio']
        data_fim = parametros['data_fim']
        ids_filtrar = parametros['ids_filtrar']

        ocorrencias, estatisticas = get_ocorrencias_estatisticas(data_inicio, data_fim, ids_filtrar)
        resultado = f"Número de ocorrências encontradas: {len(ocorrencias)}"

    return render_template(
        'relatorios_disciplinares/index.html',
        resultado=resultado,
        parametros=parametros,
        faltas_opcoes=faltas_opcoes,
        ocorrencias=ocorrencias,
        estatisticas=estatisticas
    )

@relatorios_disciplinares_bp.route('/exportar_pdf', methods=['POST'])
@admin_required
def exportar_pdf():
    parametros = coletar_parametros_form()
    ocorrencias, estatisticas = get_ocorrencias_estatisticas(
        parametros['data_inicio'],
        parametros['data_fim'],
        parametros['ids_filtrar']
    )
    rendered = render_template(
        "relatorios_disciplinares/pdf.html",
        ocorrencias=ocorrencias,
        estatisticas=estatisticas,
        data_inicio=parametros['data_inicio'], data_fim=parametros['data_fim']
    )
    pdf_file = io.BytesIO()
    HTML(string=rendered).write_pdf(pdf_file)
    pdf_file.seek(0)
    filename = f"relatorio_ocorrencias_{parametros['data_inicio']}_a_{parametros['data_fim']}.pdf"
    return send_file(pdf_file, as_attachment=True, download_name=filename, mimetype='application/pdf')

@relatorios_disciplinares_bp.route('/exportar_csv', methods=['POST'])
@admin_required
def exportar_csv():
    parametros = coletar_parametros_form()
    ocorrencias, estatisticas = get_ocorrencias_estatisticas(
        parametros['data_inicio'],
        parametros['data_fim'],
        parametros['ids_filtrar']
    )
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Data', 'Aluno', 'Turma', 'Série', 'ID Falta', 'Natureza', 'Descrição da Falta', 'Medida Aplicada'])
    for oc in ocorrencias:
        cw.writerow([
            oc['data_ocorrencia'], oc['aluno_nome'], oc['turma'], oc['serie'],
            oc['falta_id'], oc['natureza'], oc['descricao'], oc['medida_aplicada']
        ])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=relatorio_ocorrencias_{parametros['data_inicio']}_a_{parametros['data_fim']}.csv"
    output.headers["Content-type"] = "text/csv"
    return output