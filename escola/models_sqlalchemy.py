from sqlalchemy import Column, Integer, String, ForeignKey, Text, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Usuários do sistema
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)
    nivel = Column(String)
    data_criacao = Column(String)
    cargo = Column(String)
    email = Column(String)
    nome = Column(String)   
    cpf = Column(String)    

# Alunos
class Aluno(Base):
    __tablename__ = "alunos"
    id = Column(Integer, primary_key=True)
    matricula = Column(String)
    nome = Column(String)
    serie = Column(String)
    turma = Column(String)
    turno = Column(String)
    pai = Column(String)
    mae = Column(String)
    responsavel = Column(String)
    email = Column(String)
    rua = Column(String)
    numero = Column(String)
    complemento = Column(String)
    bairro = Column(String)
    cidade = Column(String)
    estado = Column(String)
    data_cadastro = Column(String)
    usuario_cadastro_id = Column(Integer)
    telefone = Column(String)
    photo = Column(String)
    data_matricula = Column(String)
    data_nascimento = Column(String)

# Telefones
class Telefone(Base):
    __tablename__ = "telefones"
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    numero = Column(String)

# Sequência do RFO
class RFOSequencia(Base):
    __tablename__ = "rfo_sequencia"
    ano = Column(Integer, primary_key=True)
    numero = Column(Integer)

# Tipos de ocorrência
class TipoOcorrencia(Base):
    __tablename__ = "tipos_ocorrencia"
    id = Column(Integer, primary_key=True)
    nome = Column(String)

# Ocorrências
class Ocorrencia(Base):
    __tablename__ = "ocorrencias"
    id = Column(Integer, primary_key=True)
    rfo_id = Column(String)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    tipo_ocorrencia_id = Column(Integer, ForeignKey("tipos_ocorrencia.id"))
    data_ocorrencia = Column(String)
    observador_id = Column(Integer, ForeignKey("usuarios.id"))
    relato_observador = Column(String)
    advertencia_oral = Column(String)
    material_recolhido = Column(String)
    data_registro = Column(String)
    hora_ocorrencia = Column(String)
    local_ocorrencia = Column(String)
    tipo_ocorrencia = Column(String)
    infracao_id = Column(Integer)
    descricao_detalhada = Column(String)
    status = Column(String)
    data_tratamento = Column(String)
    tipo_falta = Column(String)
    medida_aplicada = Column(String)
    observacao_tratamento = Column(String)
    reincidencia = Column(String)
    responsavel_registro_id = Column(Integer, ForeignKey("usuarios.id"))
    observador_nome = Column(String)
    relato_estudante = Column(String)
    despacho_gestor = Column(String)
    data_despacho = Column(String)
    falta_disciplinar_id = Column(Integer, ForeignKey("faltas_disciplinares.id"))
    tipo_ocorrencia_text = Column(String)
    subtipo_elogio = Column(String)
    tratamento_tipo = Column(String)
    observador_advertencia_oral = Column(String)
    pontos_aplicados = Column(Integer)
    falta_ids_csv = Column(String)
    circunstancias_atenuantes = Column(String)
    circunstancias_agravantes = Column(String)
    tipo_rfo = Column(String)
    prazo_comparecimento = Column(String, nullable=True)
    
# Sequência FMD
class FMDSequencia(Base):
    __tablename__ = "fmd_sequencia"
    ano = Column(Integer, primary_key=True)
    numero = Column(Integer)
    seq = Column(Integer)

# Faltas Disciplinares
class FaltaDisciplinar(Base):
    __tablename__ = "faltas_disciplinares"
    id = Column(Integer, primary_key=True)
    natureza = Column(String)
    descricao = Column(String)
    data_criacao = Column(String)

# Elogios
class Elogio(Base):
    __tablename__ = "elogios"
    id = Column(Integer, primary_key=True)
    tipo = Column(String)
    descricao = Column(String)
    data_criacao = Column(String)

# Comportamentos
class Comportamento(Base):
    __tablename__ = "comportamentos"
    id = Column(Integer, primary_key=True)
    descricao = Column(String)
    pontuacao = Column(Integer)
    data_criacao = Column(String)

# Circunstâncias
class Circunstancia(Base):
    __tablename__ = "circunstancias"
    id = Column(Integer, primary_key=True)
    tipo = Column(String)
    descricao = Column(String)
    data_criacao = Column(String)

# Bimestres
class Bimestre(Base):
    __tablename__ = "bimestres"
    id = Column(Integer, primary_key=True)
    ano = Column(Integer)
    numero = Column(Integer)
    inicio = Column(String)
    fim = Column(String)
    responsavel_id = Column(Integer)
    criado_em = Column(String)

# Tabela Disciplinar Config
class TabelaDisciplinarConfig(Base):
    __tablename__ = "tabela_disciplinar_config"
    id = Column(Integer, primary_key=True)
    chave = Column(String)
    valor = Column(String)
    descricao = Column(String)
    atualizado_em = Column(String)

# Pontuação Bimestral
class PontuacaoBimestral(Base):
    __tablename__ = "pontuacao_bimestral"
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    ano = Column(Integer)
    bimestre = Column(Integer)
    pontuacao_inicial = Column(Integer)
    pontuacao_atual = Column(Integer)
    atualizado_em = Column(String)

# Pontuação Histórico
class PontuacaoHistorico(Base):
    __tablename__ = "pontuacao_historico"
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    ano = Column(Integer)
    bimestre = Column(Integer)
    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    fmd_id = Column(Integer)
    tipo_evento = Column(String)
    valor_delta = Column(Integer)
    observacao = Column(String)
    criado_em = Column(String)

# Cabeçalhos
class Cabecalho(Base):
    __tablename__ = "cabecalhos"
    id = Column(Integer, primary_key=True)
    estado = Column(String)
    secretaria = Column(String)
    coordenacao = Column(String)
    escola = Column(String)
    logo_estado = Column(String)
    logo_escola = Column(String)
    created_at = Column(String)
    logo_secretaria = Column(String)

# Ocorrências Faltas
class OcorrenciaFalta(Base):
    __tablename__ = "ocorrencias_faltas"
    id = Column(Integer, primary_key=True)
    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    falta_id = Column(Integer, ForeignKey("faltas_disciplinares.id"))

# Prontuários
class Prontuario(Base):
    __tablename__ = "prontuarios"
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    responsavel = Column(String)
    serie = Column(String)
    turma = Column(String)
    email = Column(String)
    telefone1 = Column(String)
    telefone2 = Column(String)
    turno = Column(String)
    registros_fatos = Column(String)
    circunstancias_atenuantes = Column(String)
    circunstancias_agravantes = Column(String)
    created_at = Column(String)
    numero = Column(String)
    deleted = Column(String)

# Ocorrências Removidas
class OcorrenciaRemovida(Base):
    __tablename__ = "ocorrencias_removidas"
    id = Column(Integer, primary_key=True)
    original_id = Column(Integer)
    data = Column(String)
    removed_at = Column(String)

# Histórico de Prontuários
class ProntuarioHistory(Base):
    __tablename__ = "prontuarios_history"
    id = Column(Integer, primary_key=True)
    prontuario_id = Column(Integer, ForeignKey("prontuarios.id"))
    action = Column(String)
    changed_by = Column(String)
    changed_at = Column(String)
    payload_json = Column(String)

# Dados da Escola
class DadosEscola(Base):
    __tablename__ = "dados_escola"
    id = Column(Integer, primary_key=True)
    cabecalho_id = Column(Integer, ForeignKey("cabecalhos.id"))
    escola = Column(String)
    rua = Column(String)
    numero = Column(String)
    complemento = Column(String)
    bairro = Column(String)
    cidade = Column(String)
    estado = Column(String)
    cep = Column(String)
    cnpj = Column(String)
    diretor_nome = Column(String)
    diretor_cpf = Column(String)
    created_at = Column(String)
    email_remetente = Column(String)
    senha_email_app = Column(String)
    telefone = Column(String)
    dominio_sistema = Column(String)
    nome_sistema = Column(String)

# TACs
class TAC(Base):
    __tablename__ = "tacs"
    id = Column(Integer, primary_key=True)
    numero = Column(String)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    cabecalho_id = Column(Integer, ForeignKey("cabecalhos.id"))
    escola_text = Column(String)
    serie = Column(String)
    turma = Column(String)
    responsavel = Column(String)
    diretor_nome = Column(String)
    fato = Column(Text)
    prazo = Column(String)
    created_at = Column(String)
    updated_at = Column(String)
    deleted = Column(String)

class TACObrigacao(Base):
    __tablename__ = "tac_obrigacoes"
    id = Column(Integer, primary_key=True)
    tac_id = Column(Integer, ForeignKey("tacs.id"))
    descricao = Column(String)
    ordem = Column(Integer)

class TACParticipante(Base):
    __tablename__ = "tac_participantes"
    id = Column(Integer, primary_key=True)
    tac_id = Column(Integer, ForeignKey("tacs.id"))
    nome = Column(String)
    cargo = Column(String)
    ordem = Column(Integer)

# Ficha Medida Disciplinar
class FichaMedidaDisciplinar(Base):
    __tablename__ = "ficha_medida_disciplinar"
    id = Column(Integer, primary_key=True)
    fmd_id = Column(Integer)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    rfo_id = Column(String)
    data_fmd = Column(String)
    tipo_falta = Column(String)
    medida_aplicada = Column(String)
    descricao_falta = Column(String)
    observacoes = Column(String)
    responsavel_id = Column(Integer)
    data_registro = Column(String)
    status = Column(String)
    data_falta = Column(String)
    falta_disciplinar_ids = Column(String)
    tipo_falta_list = Column(String)
    relato = Column(String)
    medida_aplicada_outra = Column(String)
    comportamento_id = Column(Integer, ForeignKey("comportamentos.id"))
    pontuacao_id = Column(Integer)
    comparecimento = Column(String)
    prazo_comparecimento = Column(String)
    atenuantes_id = Column(String)
    agravantes_id = Column(String)
    gestor_id = Column(Integer)
    created_at = Column(String)
    updated_at = Column(String)
    baixa = Column(String)
    relato_faltas = Column(String)
    itens_faltas_ids = Column(String)
    comparecimento_responsavel = Column(String)
    atenuantes = Column(String)
    agravantes = Column(String)
    pontos_aplicados = Column(Integer)
    email_enviado_data = Column(String)
    email_enviado_para = Column(String)
    pontuacao_no_documento = Column(Numeric(4, 2))
    comportamento_no_documento = Column(String(30))

# Ocorrências/Alunos (relação N para N)
class OcorrenciaAluno(Base):
    __tablename__ = "ocorrencias_alunos"
    id = Column(Integer, primary_key=True)
    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    criado_em = Column(String)

# Atas
class Ata(Base):
    __tablename__ = "atas"
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    aluno_nome = Column(String)
    serie_turma = Column(String)
    numero = Column(String)
    ano = Column(Integer)
    conteudo = Column(Text)
    created_at = Column(String)
    updated_at = Column(String)
    created_by = Column(String)
    participants_json = Column(String)

# Prontuario RFO
class ProntuarioRFO(Base):
    __tablename__ = "prontuario_rfo"
    id = Column(Integer, primary_key=True)
    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    prontuario_id = Column(Integer, ForeignKey("prontuarios.id"))
    created_at = Column(String)

# Recuperação de senha
class RecuperacaoSenhaToken(Base):
    __tablename__ = "recuperacao_senha_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"))
    email = Column(String)
    token = Column(String)
    data_criacao = Column(String)
    expiracao = Column(String)
    usado = Column(String)
    data_uso = Column(String)
