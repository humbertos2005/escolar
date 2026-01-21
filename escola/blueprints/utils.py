from flask import session, flash, redirect, url_for
from functools import wraps
import secrets

def gerar_token_seguro(nbytes=32):
    """Gera um token seguro para recuperação de senha"""
    return secrets.token_urlsafe(nbytes)

# --- DICIONÁRIOS DE CONFIGURAÇÃO DO SISTEMA ---

NIVEL_MAP = { 
    1: "Admin Geral (TI)",
    2: "Admin Secundário",
    3: "Usuário"
}

TIPO_OCORRENCIA_MAP = {
    1: "Relatório de Fato Observado em Sala de Aula",
    2: "Relatório de Fato Observado no Ambiente Escolar"
}

TIPO_FALTA_MAP = [
    "LEVE",
    "MÉDIA",
    "GRAVE",    
]

MEDIDAS_MAP = {
    "1": "Advertência Oral",
    "2": "Advertência Escrita",
    "3": "Suspensão de Sala de Aula",
    "4": "Ações Educativas",
    "5": "Transferência Educativa"
}

# DICIONÁRIO COMPLETO DE INFRAÇÕES
INFRACAO_MAP = {
    1: "Apresentar-se com uniforme diferente do estabelecido pelo regulamento do uniforme",
    2: "Apresentar-se com barba ou bigode sem fazer",
    3: "Apresentar-se com cabelo com corte, penteado ou coloração exótica",
    4: "Apresentar-se com piercing, alargador ou similar",
    5: "Apresentar-se com tatuagem exposta",
    6: "Usar boné, gorro, lenço ou similar dentro da sala de aula ou dependências cobertas",
    7: "Usar aparelho sonoro (fone de ouvido, caixa de som portátil) em sala de aula sem autorização",
    8: "Usar celular em sala de aula sem autorização do professor",
    9: "Alimentar-se em sala de aula sem autorização",
    10: "Mascar chiclete em sala de aula",
    11: "Conversar excessivamente atrapalhando a aula",
    12: "Fazer brincadeiras inadequadas durante a aula",
    13: "Levantar-se sem autorização durante a aula",
    14: "Recusar-se a realizar atividade proposta pelo professor",
    15: "Atrasar-se para entrada ou retorno do intervalo",
    16: "Faltar sem justificativa",
    17: "Sair da sala sem autorização",
    18: "Ausentar-se da escola sem autorização",
    19: "Permanecer fora da sala durante o horário de aula sem justificativa",
    20: "Danificar ou pichar patrimônio escolar",
    21: "Sujar dependências da escola intencionalmente",
    22: "Desperdiçar água, energia ou merenda",
    23: "Desrespeitar professor, funcionário ou colega",
    24: "Usar linguagem inadequada (palavrões, xingamentos)",
    25: "Intimidar, ameaçar ou constranger colegas (bullying)",
    26: "Praticar violência física (empurrões, socos, chutes)",
    27: "Incitar ou participar de conflitos/brigas",
    28: "Portar objeto cortante, perfurante ou contundente",
    29: "Fumar nas dependências da escola",
    30: "Consumir bebida alcoólica nas dependências da escola",
    31: "Portar, consumir ou distribuir substâncias ilícitas",
    32: "Praticar ato de vandalismo",
    33: "Furtar ou tentar furtar pertences de colegas ou da escola",
    34: "Falsificar assinatura ou documento escolar",
    35: "Colar ou tentar colar em avaliações",
    36: "Desrespeitar símbolos nacionais",
    37: "Fazer gravação de áudio/vídeo sem autorização",
    38: "Divulgar imagens ou informações de colegas/professores sem autorização",
    39: "Praticar assédio moral ou sexual",
    40: "Recusar-se a participar de atividade cívica (hino, hasteamento)",
    41: "Promover ou participar de manifestação não autorizada",
    42: "Outros atos não especificados que violem o regimento escolar"
}

# --- DECORADORES DE AUTORIZAÇÃO ---
def login_required(f):
    """Verifica se o usuário está logado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth_bp.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Verifica se o usuário logado é Admin Geral (Nível 1) ou Admin Secundário (Nível 2)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        nivel = str(session.get('nivel'))
        if nivel not in ['1', '2']:  # permite nível 1 E 2, mesmo que venha como string ou inteiro
            flash('Acesso negado. Apenas administradores podem acessar esta área.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def admin_secundario_required(f):
    """Verifica se o usuário logado é Admin Geral (1) ou Admin Secundário (2)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        nivel = str(session.get('nivel'))
        if nivel not in ['1', '2']:
            flash('RFO encaminhada para tratamento.', 'success')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def usuario_ou_superior_required(f):
    """Verifica se o usuário logado tem qualquer nível de acesso (1, 2 ou 3)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('nivel') not in [1, 2, 3]:
            flash('Acesso negado.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# --- FUNÇÕES AUXILIARES ---

def formatar_telefone(telefone):
    """Formata telefone para padrão brasileiro."""
    if not telefone:
        return ""
    
    # Remove caracteres não numéricos
    numeros = ''.join(filter(str.isdigit, telefone))
    
    # Formata conforme quantidade de dígitos
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    else:
        return telefone


def validar_matricula(matricula):
    """Valida formato de matrícula."""
    if not matricula:
        return False
    # Remove espaços
    matricula = matricula.strip()
    # Valida comprimento mínimo
    return len(matricula) >= 3


def validar_email(email):
    """Validação simples de email."""
    if not email:
        return True  # Email é opcional
    return '@' in email and '.' in email.split('@')[1]

def get_proximo_rfo_id(incrementar=False):
    from datetime import datetime
    from database import get_db
    from models_sqlalchemy import RFOSequencia, Ocorrencia

    import re

    db = get_db()
    year = datetime.utcnow().strftime('%Y')

    # Busca todos os rfo_id já usados para o ano
    todos_rfos = db.query(Ocorrencia.rfo_id).filter(Ocorrencia.rfo_id.like(f"RFO-%/{year}")).all()
    usados = set()
    for (rfoid,) in todos_rfos:
        if rfoid:
            match = re.match(r"RFO-(\d+)/" + str(year), rfoid)
            if match:
                usados.add(int(match.group(1)))
    row = db.query(RFOSequencia).filter_by(ano=year).first()
    ultimo = row.numero if row else 0

    # O novo número será o maior já usado + 1, nunca repetido
    seq = max(usados) + 1 if usados else 1
    if seq <= ultimo:
        seq = ultimo + 1

    if row:
        if incrementar:
            row.numero = seq
            db.commit()
    else:
        if incrementar:
            row = RFOSequencia(ano=year, numero=seq)
            db.add(row)
            db.commit()
    return f"RFO-{seq:04d}/{year}"

import smtplib
import ssl
from email.message import EmailMessage

def enviar_email(destinatario, assunto, corpo, corpo_html, remetente, senha):
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    msg.set_content(corpo)
    msg.add_alternative(corpo_html, subtype="html")

    context = ssl._create_unverified_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(remetente, senha)
        server.send_message(msg)
