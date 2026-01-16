from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from database import get_db
import csv
import io
import pandas as pd
from datetime import datetime

from .utils import login_required, admin_required, admin_secundario_required, validar_matricula, validar_email

# Definição da Blueprint
alunos_bp = Blueprint('alunos_bp', __name__)


def process_aluno_data(data_source):
    """
    Extrai e sanitiza dados de aluno de um dicionário (form ou linha CSV/XLSX).
    Unifica a lógica de telefones e normaliza os campos textuais para MAIÚSCULAS,
    preservando o campo 'email'.
    """
    campos = [
        'matricula', 'nome', 'serie', 'turma', 'turno', 'pai', 'mae',
        'responsavel', 'email', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'data_matricula'
    ]

    # Extrai valores com strip (funciona com form/CSV: espera get(key))
    data = {k: (data_source.get(k, '') if hasattr(data_source, 'get') else '') for k in campos}
    # garantir strings e strip
    for k in data:
        if data[k] is None:
            data[k] = ''
        else:
            data[k] = str(data[k]).strip()

    # Consolida telefones
    telefones = []
    # Caso seja de um FORM (campo 'telefone' vem como lista)
    try:
        if 'telefone' in data_source and hasattr(data_source, 'getlist') and isinstance(data_source.getlist('telefone'), list):
            telefones = [t.strip() for t in data_source.getlist('telefone') if t.strip()]
    except Exception:
        telefones = []
    # Caso seja de IMPORTAÇÃO (CSV/XLSX) - chaves "TELEFONE 1/2/3"
    if not telefones:
        for i in range(1, 4):
            key = f'TELEFONE {i}'
            if key in data_source and str(data_source.get(key, '')).strip():
                telefones.append(str(data_source.get(key, '')).strip())

    data['telefone'] = ', '.join(telefones) if telefones else ''

    # Normaliza para MAIÚSCULAS (Unicode-aware) EXCETO email e data_matricula
    for k, v in list(data.items()):
        if k in ('email', 'data_matricula'):
            continue
        if isinstance(v, str) and v != '':
            data[k] = v.upper()

    # Conversão data_matricula para formato ISO (YYYY-MM-DD) se necessário
    from datetime import datetime
    if data.get('data_matricula'):
        try:
            # Só converte se vier no formato brasileiro
            if '/' in data['data_matricula']:
                data['data_matricula'] = datetime.strptime(data['data_matricula'], '%d/%m/%Y').strftime('%Y-%m-%d')
        except Exception:
            pass

    return data

from models_sqlalchemy import Aluno

@alunos_bp.route('/listar_alunos')
@login_required
def listar_alunos():
    """Exibe a lista completa de alunos."""
    db = get_db()

    # Paginação simples
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    # Busca por nome ou matrícula
    search = request.args.get('search', '').strip()

    if search:
        query = db.query(Aluno).filter(
            (Aluno.nome.ilike(f'%{search}%')) | (Aluno.matricula.ilike(f'%{search}%'))
        )
        total = query.count()
        alunos = (query
                  .order_by(Aluno.nome.asc())
                  .limit(per_page)
                  .offset(offset)
                  .all())
    else:
        query = db.query(Aluno)
        total = query.count()
        alunos = (query
                  .order_by(Aluno.nome.asc())
                  .limit(per_page)
                  .offset(offset)
                  .all())

    total_pages = (total + per_page - 1) // per_page

    alunos_processados = []
    for aluno in alunos:
        aluno_dict = {c.name: getattr(aluno, c.name) for c in Aluno.__table__.columns}
        telefones = aluno_dict.get('telefone', '').split(',') if aluno_dict.get('telefone') else []
        aluno_dict['telefone_1'] = telefones[0].strip() if len(telefones) > 0 else '-'
        aluno_dict['telefone_2'] = telefones[1].strip() if len(telefones) > 1 else '-'
        aluno_dict['telefone_3'] = telefones[2].strip() if len(telefones) > 2 else '-'
        alunos_processados.append(aluno_dict)

    return render_template('index.html',
                           alunos=alunos_processados,
                           page=page,
                           total_pages=total_pages,
                           search=search)

from models_sqlalchemy import Aluno

@alunos_bp.route('/adicionar_aluno', methods=['GET', 'POST'])
@admin_secundario_required
def adicionar_aluno():
    """Permite o cadastro individual de um novo aluno."""
    if request.method == 'POST':
        db = get_db()
        error = None
        
        data = process_aluno_data(request.form)

        # Validações
        if not data['matricula']:
            error = 'A matrícula é obrigatória.'
        elif not validar_matricula(data['matricula']):
            error = 'Matrícula inválida. Deve ter no mínimo 3 caracteres.'
        elif not data['nome']:
            error = 'O nome do aluno é obrigatório.'
        elif len(data['nome']) < 3:
            error = 'O nome do aluno deve ter no mínimo 3 caracteres.'
        elif data['email'] and not validar_email(data['email']):
            error = 'E-mail inválido.'
        elif db.query(Aluno).filter_by(matricula=data['matricula']).first() is not None:
            error = f"A matrícula '{data['matricula']}' já está cadastrada."

        if error is None:
            try:
                novo_aluno = Aluno(
                    matricula=data['matricula'],
                    nome=data['nome'],
                    serie=data['serie'],
                    turma=data['turma'],
                    turno=data['turno'],
                    pai=data['pai'],
                    mae=data['mae'],
                    responsavel=data['responsavel'],
                    telefone=data['telefone'],
                    email=data['email'],
                    rua=data['rua'],
                    numero=data['numero'],
                    complemento=data['complemento'],
                    bairro=data['bairro'],
                    cidade=data['cidade'],
                    estado=data['estado'],
                    data_matricula=data.get('data_matricula')
                )
                db.add(novo_aluno)
                db.commit()
                flash(f'Aluno "{data["nome"]}" cadastrado com sucesso!', 'success')
                return redirect(url_for('alunos_bp.listar_alunos'))
            except Exception as e:
                db.rollback()
                error = f'Erro ao cadastrar aluno: {e}'
        
        flash(error, 'danger')

    return render_template('adicionar_aluno.html')

from models_sqlalchemy import Aluno

@alunos_bp.route('/editar_aluno/<int:aluno_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_aluno(aluno_id):
    """Permite a edição dos dados de um aluno."""
    db = get_db()
    aluno = db.query(Aluno).filter_by(id=aluno_id).first()
    
    if aluno is None:
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('alunos_bp.listar_alunos'))
        
    aluno_dict = {c.name: getattr(aluno, c.name) for c in Aluno.__table__.columns}
    
    if request.method == 'POST':
        error = None
        data = process_aluno_data(request.form)
        
        # Validações
        if not data['matricula']:
            error = 'A matrícula é obrigatória.'
        elif not validar_matricula(data['matricula']):
            error = 'Matrícula inválida.'
        elif not data['nome']:
            error = 'O nome do aluno é obrigatório.'
        elif len(data['nome']) < 3:
            error = 'O nome do aluno deve ter no mínimo 3 caracteres.'
        elif data['email'] and not validar_email(data['email']):
            error = 'E-mail inválido.'
        
        # Verifica se matrícula mudou e já existe
        if data['matricula'] != aluno_dict['matricula']:
            existing_aluno = db.query(Aluno).filter(Aluno.matricula == data['matricula'], Aluno.id != aluno_id).first()
            if existing_aluno:
                error = f"A matrícula '{data['matricula']}' já está em uso por outro aluno."

        if error is None:
            try:
                aluno.matricula = data['matricula']
                aluno.nome = data['nome']
                aluno.serie = data['serie']
                aluno.turma = data['turma']
                aluno.turno = data['turno']
                aluno.pai = data['pai']
                aluno.mae = data['mae']
                aluno.responsavel = data['responsavel']
                aluno.telefone = data['telefone']
                aluno.email = data['email']
                aluno.rua = data['rua']
                aluno.numero = data['numero']
                aluno.complemento = data['complemento']
                aluno.bairro = data['bairro']
                aluno.cidade = data['cidade']
                aluno.estado = data['estado']
                aluno.data_matricula = data['data_matricula']
                db.commit()
                flash(f'Dados do aluno "{data["nome"]}" atualizados com sucesso!', 'success')
                return redirect(url_for('alunos_bp.listar_alunos'))
            except Exception as e:
                db.rollback()
                error = f'Erro ao atualizar aluno: {e}'
        
        flash(error, 'danger')

    return render_template('editar_aluno.html', aluno=aluno_dict)


from models_sqlalchemy import Aluno, Ocorrencia

@alunos_bp.route('/excluir_aluno/<int:aluno_id>', methods=['POST'])
@admin_required
def excluir_aluno(aluno_id):
    """Exclui um aluno e todas as suas ocorrências relacionadas."""
    db = get_db()
    try:
        aluno = db.query(Aluno).filter_by(id=aluno_id).first()
        if not aluno:
            flash('Aluno não encontrado.', 'danger')
            return redirect(url_for('alunos_bp.listar_alunos'))

        nome_aluno = aluno.nome

        # Exclui todas as ocorrências daquele aluno
        db.query(Ocorrencia).filter_by(aluno_id=aluno_id).delete()
        # Exclui o aluno
        db.delete(aluno)
        db.commit()
        flash(f'Aluno "{nome_aluno}" e suas ocorrências excluídos com sucesso.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir aluno: {e}', 'danger')
    return redirect(url_for('alunos_bp.listar_alunos'))

from models_sqlalchemy import Aluno

@alunos_bp.route('/importar_alunos', methods=['GET', 'POST'])
@admin_secundario_required
def importar_alunos():
    """Gerencia a importação de alunos via arquivo CSV/XLSX."""
    if request.method == 'POST':
        if 'arquivo_csv' not in request.files:
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
            
        arquivo = request.files['arquivo_csv']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)

        erros_importacao = []
        sucessos = 0
        db = get_db()
        
        try:
            filename = arquivo.filename.lower()
            
            # CORREÇÃO CRÍTICA PARA EXCEL
            if filename.endswith(('.xls', '.xlsx')):
                # Força engine openpyxl e tratamento correto de dados vazios
                df = pd.read_excel(arquivo, dtype=str, engine='openpyxl')
                df = df.fillna('')  # Substitui NaN por string vazia
                df = df.dropna(how='all')  # Remove linhas completamente vazias
                df.columns = df.columns.str.strip().str.upper()  # Normaliza colunas
                print(f"✓ Colunas encontradas no Excel: {list(df.columns)}")
                registros = df.to_dict('records')
            elif filename.endswith('.csv'):
                try:
                    stream = io.StringIO(arquivo.stream.read().decode("utf-8"))
                except UnicodeDecodeError:
                    arquivo.stream.seek(0)
                    stream = io.StringIO(arquivo.stream.read().decode("latin-1"))
                reader = csv.DictReader(stream, delimiter=';')
                registros = list(reader)
                registros_temp = []
                for row in registros:
                    normalized_row = {k.upper().strip(): str(v).strip() for k, v in row.items()}
                    registros_temp.append(normalized_row)
                registros = registros_temp
            else:
                flash('Formato de arquivo não suportado. Use CSV, XLSX ou XLS.', 'danger')
                return redirect(request.url)

        except Exception as e:
            flash(f'Erro ao ler o arquivo: {str(e)}', 'danger')
            return redirect(request.url)

        print(f"✓ Total de registros a processar: {len(registros)}")
        
        for i, row in enumerate(registros, start=2):
            try:
                matricula = str(row.get('MATRICULA', row.get('MATRÍCULA', ''))).strip()
                nome = str(row.get('NOME', '')).strip()
                data_nascimento = str(row.get('DATA_NASCIMENTO', '')).strip()
                data_matricula = str(row.get('DATA_MATRICULA', row.get('DATA_MATRÍCULA', ''))).strip()
                serie = str(row.get('SERIE', row.get('SÉRIE', ''))).strip()
                turma = str(row.get('TURMA', '')).strip()
                turno = str(row.get('TURNO', '')).strip()
                pai = str(row.get('PAI', '')).strip()
                mae = str(row.get('MAE', row.get('MÃE', ''))).strip()
                responsavel = str(row.get('RESPONSAVEL', row.get('RESPONSÁVEL', ''))).strip()
                email = str(row.get('E-MAIL', row.get('EMAIL', ''))).strip()
                endereco_unico = str(row.get('ENDERECO', row.get('ENDEREÇO', ''))).strip()
                rua = str(row.get('RUA', endereco_unico)).strip()
                numero = str(row.get('NUMERO', row.get('NÚMERO', ''))).strip()
                complemento = str(row.get('COMPLEMENTO', '')).strip()
                bairro = str(row.get('BAIRRO', '')).strip()
                cidade = str(row.get('CIDADE', '')).strip()
                estado = str(row.get('ESTADO', '')).strip()

                print(f"Linha {i}: MAT={matricula}, NOME={nome}, NASC={data_nascimento}, SERIE={serie}")

                if not matricula or not nome or matricula == '' or nome == '':
                    erros_importacao.append({
                        'linha': i,
                        'matricula': matricula or 'N/A',
                        'nome': nome or 'N/A',
                        'erro': 'Matrícula e Nome são obrigatórios.'
                    })
                    continue

                # Verifica duplicidade
                existing = db.query(Aluno).filter_by(matricula=matricula).first()

                if existing:
                    erros_importacao.append({
                        'linha': i,
                        'matricula': matricula,
                        'nome': nome,
                        'erro': 'Matrícula já existente.'
                    })
                    continue

                telefones = []
                for j in range(1, 4):
                    tel = str(row.get(f'TELEFONE {j}', row.get(f'TELEFONE{j}', ''))).strip()
                    if tel and tel != '':
                        telefones.append(tel)
                if not telefones:
                    tel_unico = str(row.get('TELEFONE', row.get('TELEFONES', ''))).strip()
                    if tel_unico:
                        telefones = [t.strip() for t in tel_unico.split(',') if t.strip()]
                telefone_str = ', '.join(telefones[:3])  # Limita a 3 telefones

                novo_aluno = Aluno(
                    matricula=matricula,
                    nome=nome,
                    data_nascimento=data_nascimento,
                    data_matricula=data_matricula,
                    serie=serie,
                    turma=turma,
                    turno=turno,
                    pai=pai,
                    mae=mae,
                    responsavel=responsavel,
                    telefone=telefone_str,
                    email=email,
                    rua=rua,
                    numero=numero,
                    complemento=complemento,
                    bairro=bairro,
                    cidade=cidade,
                    estado=estado
                )
                db.add(novo_aluno)
                sucessos += 1
                print(f"✓ Aluno {nome} cadastrado com sucesso!")

            except Exception as e:
                erros_importacao.append({
                    'linha': i,
                    'matricula': matricula if 'matricula' in locals() else 'N/A',
                    'nome': nome if 'nome' in locals() else 'N/A',
                    'erro': f'Erro ao processar: {str(e)}'
                })
                print(f"✗ Erro na linha {i}: {str(e)}")

        try:
            db.commit()
            if erros_importacao:
                session['erros_importacao'] = erros_importacao
                flash(f'Importação concluída: {sucessos} alunos cadastrados, {len(erros_importacao)} erro(s).', 'warning')
                return redirect(url_for('alunos_bp.erros_importacao'))
            else:
                flash(f'Importação concluída com sucesso! {sucessos} alunos cadastrados.', 'success')
        except Exception as e:
            db.rollback()
            flash(f'Erro ao salvar dados no banco: {e}', 'danger')

        return redirect(url_for('alunos_bp.listar_alunos'))
        
    return render_template('importar_alunos.html')


from models_sqlalchemy import Aluno

@alunos_bp.route('/backup_alunos')
@admin_secundario_required
def backup_alunos():
    """Exporta todos os dados dos alunos para um arquivo CSV."""
    db = get_db()
    alunos = db.query(Aluno).order_by(Aluno.nome.asc()).all()
    
    if not alunos:
        flash('Nenhum aluno encontrado para backup.', 'warning')
        return redirect(url_for('alunos_bp.listar_alunos'))

    output = io.StringIO()
    # Obtém os nomes dos campos dinamicamente
    fieldnames = [column.name for column in Aluno.__table__.columns]
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';')

    writer.writeheader()
    for aluno in alunos:
        row = {c: getattr(aluno, c) for c in fieldnames}
        writer.writerow(row)

    response = make_response(output.getvalue())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response.headers["Content-Disposition"] = f"attachment; filename=backup_alunos_{timestamp}.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return response


from models_sqlalchemy import Aluno, Ocorrencia, RFOSequencia  # Ajuste o nome do modelo RFOSequencia conforme o models_sqlalchemy.py

@alunos_bp.route('/excluir_todos', methods=['POST'])
@admin_required
def excluir_todos():
    """Exclui todos os alunos e ocorrências, e reinicia o contador de IDs."""
    db = get_db()
    try:
        db.query(Ocorrencia).delete()
        db.query(Aluno).delete()
        db.query(RFOSequencia).delete()
        db.commit()
        flash('TODOS os alunos e ocorrências foram excluídos. O sistema foi reiniciado.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Erro ao excluir todos os dados: {e}', 'danger')
    return redirect(url_for('alunos_bp.listar_alunos'))

from models_sqlalchemy import Aluno

@alunos_bp.route('/buscar_aluno_json')
@login_required
def buscar_aluno_json():
    """Rota AJAX para Autocomplete de alunos."""
    termo_busca = request.args.get('q', '').strip()
    aluno_id = request.args.get('id', type=int)
    db = get_db()
    resultados = []

    if termo_busca:
        alunos = (
            db.query(Aluno)
            .filter(
                (Aluno.nome.ilike(f'%{termo_busca}%')) |
                (Aluno.matricula.ilike(f'%{termo_busca}%'))
            )
            .order_by(Aluno.nome.asc())
            .limit(10)
            .all()
        )
    elif aluno_id:
        alunos = db.query(Aluno).filter_by(id=aluno_id).all()
    else:
        return jsonify([])

    for aluno in alunos:
        resultados.append({
            'id': aluno.id,
            'value': f"{aluno.matricula} - {aluno.nome}",
            'data': {
                'matricula': aluno.matricula,
                'nome': aluno.nome,
                'serie': aluno.serie or '',
                'turma': aluno.turma or ''
            }
        })
        
    return jsonify(resultados)

@alunos_bp.route('/gerenciar_alunos', methods=['GET', 'POST'])
@admin_secundario_required
def gerenciar_alunos():
    """Exibe a página única com abas para gerenciar alunos (cadastrar e importar)."""
    if request.method == 'POST': 
        # Verificar se é importação de arquivo (tem arquivo) ou cadastro individual
        if 'arquivo_csv' in request.files and request.files['arquivo_csv'].filename != '':
            # É importação de Excel
            return importar_alunos()
        else:
            # É cadastro individual
            return adicionar_aluno()
    return render_template('cadastros/gerenciar_alunos.html')