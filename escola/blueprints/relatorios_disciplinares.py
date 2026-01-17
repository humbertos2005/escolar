from flask import Blueprint, render_template, request, send_file, make_response
from database import get_db
from .utils import admin_required
from datetime import datetime
from weasyprint import HTML
import io
import csv

from models_sqlalchemy import (
    Ocorrencia,
    OcorrenciaFalta,
    FaltaDisciplinar,
    Aluno,
)

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

    # Montar query ORM com todos os joins necessários
    query = (
        db.query(
            Ocorrencia.id.label('id'),
            Ocorrencia.data_ocorrencia.label('data_ocorrencia'),
            Ocorrencia.medida_aplicada.label('medida_aplicada'),
            Aluno.nome.label('aluno_nome'),
            Aluno.serie.label('serie'),
            Aluno.turma.label('turma'),
            FaltaDisciplinar.id.label('falta_id'),
            FaltaDisciplinar.natureza.label('natureza'),
            FaltaDisciplinar.descricao.label('descricao')
        )
        .join(OcorrenciaFalta, OcorrenciaFalta.ocorrencia_id == Ocorrencia.id)
        .join(FaltaDisciplinar, FaltaDisciplinar.id == OcorrenciaFalta.falta_id)
        .join(Aluno, Aluno.id == Ocorrencia.aluno_id)
    )
    if data_inicio:
        query = query.filter(Ocorrencia.data_ocorrencia >= data_inicio)
    if data_fim:
        query = query.filter(Ocorrencia.data_ocorrencia <= data_fim)
    if ids_filtrar:
        query = query.filter(FaltaDisciplinar.id.in_(ids_filtrar))
    query = query.order_by(Ocorrencia.data_ocorrencia.desc(), Ocorrencia.id.desc())

    ocorrencias = query.all()

    estatisticas = {}
    for oc in ocorrencias:
        key = f"{oc.falta_id} - {oc.descricao}"
        estatisticas[key] = estatisticas.get(key, 0) + 1

    # Retornar lista de namedtuples/objects
    return ocorrencias, estatisticas

@relatorios_disciplinares_bp.route('/', methods=['GET', 'POST'])
@admin_required
def index():
    db = get_db()
    # Para montar as opções, consultar ORM
    faltas = db.query(FaltaDisciplinar.id, FaltaDisciplinar.natureza, FaltaDisciplinar.descricao).order_by(FaltaDisciplinar.id).all()
    faltas_opcoes = [f"{f.id} - {f.descricao}" for f in faltas]

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
            oc.data_ocorrencia, oc.aluno_nome, oc.turma, oc.serie,
            oc.falta_id, oc.natureza, oc.descricao, oc.medida_aplicada
        ])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=relatorio_ocorrencias_{parametros['data_inicio']}_a_{parametros['data_fim']}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
