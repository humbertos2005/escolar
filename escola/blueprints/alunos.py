from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from database import get_db
import sqlite3
import csv
import io
import pandas as pd
from datetime import datetime, timedelta

from .utils import login_required, admin_required, admin_secundario_required, validar_matricula, validar_email

# Definição da Blueprint
alunos_bp = Blueprint('alunos_bp', __name__)

# Constante para conversão de datas do Excel
EXCEL_EPOCH_DATE = datetime(1899, 12, 30)


def parse_date_from_excel_or_text(date_str):
    """
    Converte uma string de data do Excel (número serial) ou formato brasileiro (DD/MM/AAAA)
    para o formato ISO (YYYY-MM-DD).
    
    Args:
        date_str: String contendo a data em formato Excel serial ou DD/MM/AAAA
        
    Returns:
        String no formato YYYY-MM-DD ou string vazia se a conversão falhar
    """
    if not date_str:
        return ''
    
    # Verifica se é NaN ou NaT do pandas/numpy
    try:
        import pandas as pd
        if pd.isna(date_str):
            return ''
    except (ImportError, TypeError):
        pass
    
    try:
        # Tenta converter como número serial do Excel
        excel_date = float(date_str)
        # Validação: data serial do Excel deve estar dentro de limites razoáveis
        # Excel serial 1 = 1900-01-01, mas o cálculo usa 1899-12-30 como epoch
        # para compensar o bug do ano bissexto do Excel (1900 não foi bissexto)
        if excel_date < -100000 or excel_date > 100000:
            return ''
        return (EXCEL_EPOCH_DATE + timedelta(days=excel_date)).strftime('%Y-%m-%d')
    except (ValueError, TypeError, OverflowError):
        # Se falhar, tenta como formato brasileiro (DD/MM/AAAA)
        try:
            if '/' in str(date_str):
                return datetime.strptime(str(date_str), '%d/%m/%Y').strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pass
    return ''


def get_column_value(row, *column_names):
    """
    Busca o valor de uma coluna testando múltiplos nomes possíveis.
    
    Args:
        row: Dicionário contendo os dados da linha
        *column_names: Nomes de colunas a serem testados em ordem
        
    Returns:
        String com o valor encontrado ou string vazia
    """
    for name in column_names:
        value = row.get(name)
        if value is not None:
            return str(value).strip()
    return ''



def process_aluno_data(data_source):
    """
    Extrai e sanitiza dados de aluno de um dicionário (form ou linha CSV/XLSX).
    Unifica a lógica de telefones e normaliza os campos textuais para MAIÚSCULAS,
    preservando o campo 'email'.
    """
    campos = [
        'matricula', 'nome', 'data_nascimento', 'data_matricula', 'serie', 'turma', 'turno', 'pai', 'mae',
        'responsavel', 'email', 'rua', 'numero', 'complemento', 'bairro', 'cidade', 'estado'
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

    # Normaliza para MAIÚSCULAS (Unicode-aware) EXCETO email e datas
    for k, v in list(data.items()):
        if k in ('email', 'data_nascimento', 'data_matricula'):
            # preserva exatamente como foi informado
            continue
        if isinstance(v, str) and v != '':
            data[k] = v.upper()

    return data

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
        search_like = f'%{search}%'
        alunos = db.execute('''
            SELECT * FROM alunos 
            WHERE nome LIKE ? OR matricula LIKE ?
            ORDER BY nome ASC
            LIMIT ? OFFSET ?
        ''', (search_like, search_like, per_page, offset)).fetchall()
        
        total = db.execute('''
            SELECT COUNT(*) as total FROM alunos 
            WHERE nome LIKE ? OR matricula LIKE ?
        ''', (search_like, search_like)).fetchone()['total']
    else:
        alunos = db.execute('''
            SELECT * FROM alunos 
            ORDER BY nome ASC
            LIMIT ? OFFSET ?
        ''', (per_page, offset)).fetchall()
        
        total = db.execute('SELECT COUNT(*) as total FROM alunos').fetchone()['total']
    
    total_pages = (total + per_page - 1) // per_page
    
    # NOVO: Processa telefones para exibição separada
    alunos_processados = []
    for aluno in alunos:
        aluno_dict = dict(aluno)
        # Separa telefones
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
        elif db.execute(
            'SELECT id FROM alunos WHERE matricula = ?', (data['matricula'],)
        ).fetchone() is not None:
            error = f"A matrícula '{data['matricula']}' já está cadastrada."

        if error is None:
            try:
                db.execute(
                    '''
                    INSERT INTO alunos 
                    (matricula, nome, data_nascimento, data_matricula, serie, turma, turno, pai, mae, responsavel, telefone, email, 
                     rua, numero, complemento, bairro, cidade, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (data['matricula'], data['nome'], data['data_nascimento'], data['data_matricula'], data['serie'], data['turma'], data['turno'], 
                     data['pai'], data['mae'], data['responsavel'], data['telefone'], data['email'], 
                     data['rua'], data['numero'], data['complemento'], data['bairro'], data['cidade'], 
                     data['estado'])
                )
                db.commit()
                flash(f'Aluno "{data["nome"]}" cadastrado com sucesso!', 'success')
                return redirect(url_for('alunos_bp.listar_alunos'))
            except sqlite3.Error as e:
                error = f'Erro ao cadastrar aluno: {e}'
        
        flash(error, 'danger')

    return render_template('adicionar_aluno.html')


@alunos_bp.route('/editar_aluno/<int:aluno_id>', methods=['GET', 'POST'])
@admin_secundario_required
def editar_aluno(aluno_id):
    """Permite a edição dos dados de um aluno."""
    db = get_db()
    aluno = db.execute('SELECT * FROM alunos WHERE id = ?', (aluno_id,)).fetchone()
    
    if aluno is None:
        flash('Aluno não encontrado.', 'danger')
        return redirect(url_for('alunos_bp.listar_alunos'))
        
    aluno_dict = dict(aluno)
    
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
            existing_aluno = db.execute(
                'SELECT id FROM alunos WHERE matricula = ? AND id != ?', 
                (data['matricula'], aluno_id)
            ).fetchone()
            if existing_aluno:
                error = f"A matrícula '{data['matricula']}' já está em uso por outro aluno."

        if error is None:
            try:
                db.execute(
                    '''
                    UPDATE alunos SET 
                    matricula = ?, nome = ?, data_nascimento = ?, data_matricula = ?, serie = ?, turma = ?, turno = ?, pai = ?, mae = ?, 
                    responsavel = ?, telefone = ?, email = ?, rua = ?, numero = ?, complemento = ?, 
                    bairro = ?, cidade = ?, estado = ? 
                    WHERE id = ?
                    ''',
                    (data['matricula'], data['nome'], data['data_nascimento'], data['data_matricula'], data['serie'], data['turma'], data['turno'], 
                     data['pai'], data['mae'], data['responsavel'], data['telefone'], data['email'], 
                     data['rua'], data['numero'], data['complemento'], data['bairro'], data['cidade'], 
                     data['estado'], aluno_id)
                )
                db.commit()
                flash(f'Dados do aluno "{data["nome"]}" atualizados com sucesso!', 'success')
                return redirect(url_for('alunos_bp.listar_alunos'))
            except sqlite3.Error as e:
                error = f'Erro ao atualizar aluno: {e}'
        
        flash(error, 'danger')

    return render_template('editar_aluno.html', aluno=aluno_dict)


@alunos_bp.route('/excluir_aluno/<int:aluno_id>', methods=['POST'])
@admin_required
def excluir_aluno(aluno_id):
    """Exclui um aluno e todas as suas ocorrências relacionadas."""
    db = get_db()
    
    try:
        aluno = db.execute('SELECT nome FROM alunos WHERE id = ?', (aluno_id,)).fetchone()
        
        if not aluno:
            flash('Aluno não encontrado.', 'danger')
            return redirect(url_for('alunos_bp.listar_alunos'))
        
        # Deleta as ocorrências do aluno (CASCADE já configurado)
        db.execute('DELETE FROM ocorrencias WHERE aluno_id = ?', (aluno_id,))
        # Deleta o aluno
        db.execute('DELETE FROM alunos WHERE id = ?', (aluno_id,))
        db.commit()
        
        flash(f'Aluno "{aluno["nome"]}" e suas ocorrências excluídos com sucesso.', 'success')
            
    except sqlite3.Error as e:
        flash(f'Erro ao excluir aluno: {e}', 'danger')
        
    return redirect(url_for('alunos_bp.listar_alunos'))


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
                
                # Remove linhas completamente vazias
                df = df.dropna(how='all')
                
                # Normaliza nomes das colunas: remove espaços extras e converte para maiúsculas
                df.columns = df.columns.str.strip().str.upper()
                
                # DEBUG: imprime as colunas encontradas
                print(f"✓ Colunas encontradas no Excel: {list(df.columns)}")
                
                registros = df.to_dict('records')
                
            elif filename.endswith('.csv'):
                # Tenta múltiplos encodings para CSV
                try:
                    stream = io.StringIO(arquivo.stream.read().decode("utf-8"))
                except UnicodeDecodeError:
                    arquivo.stream.seek(0)
                    stream = io.StringIO(arquivo.stream.read().decode("latin-1"))
                
                reader = csv.DictReader(stream, delimiter=';')
                registros = list(reader)
                
                # Normaliza chaves do CSV
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

        # CORREÇÃO: Mapeamento completo de colunas
        print(f"✓ Total de registros a processar: {len(registros)}")
        
        # Processa os registros
        for i, row in enumerate(registros, start=2):
            try:
                # Extração com mapeamento correto
                matricula = str(row.get('MATRICULA', '')).strip()
                nome = str(row.get('NOME', '')).strip()
                serie = str(row.get('SERIE', row.get('SÉRIE', ''))).strip()
                turma = str(row.get('TURMA', '')).strip()
                turno = str(row.get('TURNO', '')).strip()
                pai = str(row.get('PAI', '')).strip()
                mae = str(row.get('MAE', row.get('MÃE', ''))).strip()
                responsavel = str(row.get('RESPONSAVEL', row.get('RESPONSÁVEL', ''))).strip()
                email = str(row.get('E-MAIL', row.get('EMAIL', ''))).strip()
                
                # Endereço - CORREÇÃO: suporta múltiplos formatos
                rua = str(row.get('RUA', row.get('ENDERECO', row.get('ENDEREÇO', '')))).strip()
                numero = str(row.get('NUMERO', row.get('NÚMERO', ''))).strip()
                complemento = str(row.get('COMPLEMENTO', '')).strip()
                bairro = str(row.get('BAIRRO', '')).strip()
                cidade = str(row.get('CIDADE', '')).strip()
                estado = str(row.get('ESTADO', '')).strip()

                # Extrair novas colunas de data
                data_nascimento = get_column_value(row, 'DATA_NASCIMENTO', 'DATA NASCIMENTO')
                data_matricula = get_column_value(row, 'DATA_MATRÍCULA', 'DATA_MATRICULA', 'DATA MATRÍCULA')

                # Processar datas usando helper function
                data_nascimento = parse_date_from_excel_or_text(data_nascimento)
                data_matricula = parse_date_from_excel_or_text(data_matricula)

                # DEBUG
                print(f"Linha {i}: MAT={matricula}, NOME={nome}, SERIE={serie}, MAE={mae}, EMAIL={email}")

                if not matricula or not nome or matricula == '' or nome == '':
                    erros_importacao.append({
                        'linha': i,
                        'matricula': matricula or 'N/A',
                        'nome': nome or 'N/A',
                        'erro': 'Matrícula e Nome são obrigatórios.'
                    })
                    continue

                # Verifica duplicidade
                existing = db.execute(
                    'SELECT id FROM alunos WHERE matricula = ?', (matricula,)
                ).fetchone()

                if existing:
                    erros_importacao.append({
                        'linha': i,
                        'matricula': matricula,
                        'nome': nome,
                        'erro': 'Matrícula já existente.'
                    })
                    continue

                # Processa telefones - CORREÇÃO: aceita múltiplos formatos
                telefones = []
                for j in range(1, 4):
                    tel = str(row.get(f'TELEFONE {j}', row.get(f'TELEFONE{j}', ''))).strip()
                    if tel and tel != '':
                        telefones.append(tel)
                
                # Se não encontrou telefones separados, tenta TELEFONE(S)
                if not telefones:
                    tel_unico = str(row.get('TELEFONE', row.get('TELEFONES', ''))).strip()
                    if tel_unico:
                        # Se tem múltiplos telefones separados por vírgula
                        telefones = [t.strip() for t in tel_unico.split(',') if t.strip()]

                telefone_str = ', '.join(telefones[:3])  # Limita a 3 telefones

                # Insere o aluno
                db.execute('''
                    INSERT INTO alunos 
                    (matricula, nome, data_nascimento, data_matricula, serie, turma, turno, pai, mae, 
                     responsavel, telefone, email, rua, numero, complemento, bairro, cidade, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    matricula, nome, data_nascimento, data_matricula, serie, turma, turno, pai, mae, 
                    responsavel, telefone_str, email, rua, numero, complemento, bairro, cidade, estado
                ))
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

        except sqlite3.Error as e:
            db.rollback()
            flash(f'Erro ao salvar dados no banco: {e}', 'danger')

        return redirect(url_for('alunos_bp.listar_alunos'))
        
    return render_template('importar_alunos.html')


@alunos_bp.route('/erros_importacao')
@admin_secundario_required
def erros_importacao():
    """Exibe o relatório de erros da última importação."""
    erros = session.pop('erros_importacao', None)
    return render_template('erros_importacao.html', erros=erros)


@alunos_bp.route('/backup_alunos')
@admin_secundario_required
def backup_alunos():
    """Exporta todos os dados dos alunos para um arquivo CSV."""
    db = get_db()
    alunos = db.execute('SELECT * FROM alunos ORDER BY nome').fetchall()
    
    if not alunos:
        flash('Nenhum aluno encontrado para backup.', 'warning')
        return redirect(url_for('alunos_bp.listar_alunos'))

    output = io.StringIO()
    fieldnames = alunos[0].keys()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';')

    writer.writeheader()
    for aluno in alunos:
        writer.writerow(dict(aluno))

    response = make_response(output.getvalue())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response.headers["Content-Disposition"] = f"attachment; filename=backup_alunos_{timestamp}.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return response


@alunos_bp.route('/excluir_todos', methods=['POST'])
@admin_required
def excluir_todos():
    """Exclui todos os alunos e ocorrências, e reinicia o contador de IDs."""
    db = get_db()
    
    try:
        db.execute('DELETE FROM ocorrencias')
        db.execute('DELETE FROM alunos')
        db.execute("DELETE FROM sqlite_sequence WHERE name IN ('alunos', 'ocorrencias')")
        db.execute('DELETE FROM rfo_sequencia')
        
        db.commit()
        flash('TODOS os alunos e ocorrências foram excluídos. O sistema foi reiniciado.', 'success')
    except sqlite3.Error as e:
        db.rollback()
        flash(f'Erro ao excluir todos os dados: {e}', 'danger')
        
    return redirect(url_for('alunos_bp.listar_alunos'))


@alunos_bp.route('/buscar_aluno_json')
@login_required
def buscar_aluno_json():
    """Rota AJAX para Autocomplete de alunos."""
    termo_busca = request.args.get('q', '').strip()
    aluno_id = request.args.get('id', type=int)
    db = get_db()
    resultados = []

    if termo_busca:
        termo_like = f'%{termo_busca}%'
        alunos = db.execute('''
            SELECT id, matricula, nome, serie, turma 
            FROM alunos 
            WHERE nome LIKE ? OR matricula LIKE ?
            ORDER BY nome
            LIMIT 10
        ''', (termo_like, termo_like)).fetchall()
        
    elif aluno_id:
        alunos = db.execute('''
            SELECT id, matricula, nome, serie, turma 
            FROM alunos 
            WHERE id = ?
        ''', (aluno_id,)).fetchall()
    else:
        return jsonify([])

    for aluno in alunos:
        resultados.append({
            'id': aluno['id'], 
            'value': f"{aluno['matricula']} - {aluno['nome']}",
            'data': {
                'matricula': aluno['matricula'],
                'nome': aluno['nome'],
                'serie': aluno['serie'] or '',
                'turma': aluno['turma'] or ''
            }
        })
        
    return jsonify(resultados)



@alunos_bp.route('/gerenciar_alunos', methods=['GET', 'POST'])
@admin_secundario_required
def gerenciar_alunos():
    """Exibe a página única com abas para gerenciar alunos (cadastrar e importar)."""
    if request.method == 'POST':
        # Redirecionar para a lógica de importação
        return importar_alunos()
    return render_template('cadastros/gerenciar_alunos.html')
