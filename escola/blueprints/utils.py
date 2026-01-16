from flask import session, flash, redirect, url_for
from functools import wraps
import secrets

def gerar_token_seguro(nbytes=32):
    """Gera um token seguro para recupera��o de senha"""
    return secrets.token_urlsafe(nbytes)

# --- DICION�RIOS DE CONFIGURA��O DO SISTEMA ---

NIVEL_MAP = { 
    1: "Admin Geral (TI)",
    2: "Admin Secund�rio",
    3: "Usu�rio"
}

TIPO_OCORRENCIA_MAP = {
    1: "Relat�rio de Fato Observado em Sala de Aula",
    2: "Relat�rio de Fato Observado no Ambiente Escolar"
}

TIPO_FALTA_MAP = [
    "LEVE",
    "M�DIA",
    "GRAVE",    
]

MEDIDAS_MAP = {
    "1": "Advert�ncia Oral",
    "2": "Advert�ncia Escrita",
    "3": "Suspens�o de Sala de Aula",
    "4": "A��es Educativas",
    "5": "Transfer�ncia Educativa"
}

# DICION�RIO COMPLETO DE INFRA��ES
INFRACAO_MAP = {
    1: "Apresentar-se com uniforme diferente do estabelecido pelo regulamento do uniforme",
    2: "Apresentar-se com barba ou bigode sem fazer",
    3: "Apresentar-se com cabelo com corte, penteado ou colora��o ex�tica",
    4: "Apresentar-se com piercing, alargador ou similar",
    5: "Apresentar-se com tatuagem exposta",
    6: "Usar bon�, gorro, len�o ou similar dentro da sala de aula ou depend�ncias cobertas",
    7: "Usar aparelho sonoro (fone de ouvido, caixa de som port�til) em sala de aula sem autoriza��o",
    8: "Usar celular em sala de aula sem autoriza��o do professor",
    9: "Alimentar-se em sala de aula sem autoriza��o",
    10: "Mascar chiclete em sala de aula",
    11: "Conversar excessivamente atrapalhando a aula",
    12: "Fazer brincadeiras inadequadas durante a aula",
    13: "Levantar-se sem autoriza��o durante a aula",
    14: "Recusar-se a realizar atividade proposta pelo professor",
    15: "Atrasar-se para entrada ou retorno do intervalo",
    16: "Faltar sem justificativa",
    17: "Sair da sala sem autoriza��o",
    18: "Ausentar-se da escola sem autoriza��o",
    19: "Permanecer fora da sala durante o hor�rio de aula sem justificativa",
    20: "Danificar ou pichar patrim�nio escolar",
    21: "Sujar depend�ncias da escola intencionalmente",
    22: "Desperdi�ar �gua, energia ou merenda",
    23: "Desrespeitar professor, funcion�rio ou colega",
    24: "Usar linguagem inadequada (palavr�es, xingamentos)",
    25: "Intimidar, amea�ar ou constranger colegas (bullying)",
    26: "Praticar viol�ncia f�sica (empurr�es, socos, chutes)",
    27: "Incitar ou participar de conflitos/brigas",
    28: "Portar objeto cortante, perfurante ou contundente",
    29: "Fumar nas depend�ncias da escola",
    30: "Consumir bebida alco�lica nas depend�ncias da escola",
    31: "Portar, consumir ou distribuir subst�ncias il�citas",
    32: "Praticar ato de vandalismo",
    33: "Furtar ou tentar furtar pertences de colegas ou da escola",
    34: "Falsificar assinatura ou documento escolar",
    35: "Colar ou tentar colar em avalia��es",
    36: "Desrespeitar s�mbolos nacionais",
    37: "Fazer grava��o de �udio/v�deo sem autoriza��o",
    38: "Divulgar imagens ou informa��es de colegas/professores sem autoriza��o",
    39: "Praticar ass�dio moral ou sexual",
    40: "Recusar-se a participar de atividade c�vica (hino, hasteamento)",
    41: "Promover ou participar de manifesta��o n�o autorizada",
    42: "Outros atos n�o especificados que violem o regimento escolar"
}


# --- DECORADORES DE AUTORIZA��O ---

def login_required(f):
    """Verifica se o usu�rio est� logado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth_bp.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Verifica se o usu�rio logado � Admin Geral (N�vel 1) ou Admin Secund�rio (N�vel 2)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('nivel') not in [1, 2, '1', '2']:
            flash('Acesso negado. Apenas administradores podem acessar esta área.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def admin_secundario_required(f):
    """Verifica se o usu�rio logado � Admin Geral (1) ou Admin Secund�rio (2)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('nivel') not in [1, 2, '1', '2']:
            flash('RFO encaminhada para tratamento.', 'success')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def usuario_ou_superior_required(f):
    """Verifica se o usu�rio logado tem qualquer n�vel de acesso (1, 2 ou 3)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('nivel') not in [1, 2, 3]:
            flash('Acesso negado.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# --- FUN��ES AUXILIARES ---

def formatar_telefone(telefone):
    """Formata telefone para padr�o brasileiro."""
    if not telefone:
        return ""
    
    # Remove caracteres n�o num�ricos
    numeros = ''.join(filter(str.isdigit, telefone))
    
    # Formata conforme quantidade de d�gitos
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    else:
        return telefone


def validar_matricula(matricula):
    """Valida formato de matr�cula."""
    if not matricula:
        return False
    # Remove espa�os
    matricula = matricula.strip()
    # Valida comprimento m�nimo
    return len(matricula) >= 3


def validar_email(email):
    """Valida��o simples de email."""
    if not email:
        return True  # Email � opcional
    return '@' in email and '.' in email.split('@')[1]

def get_proximo_rfo_id(incrementar=False):
    """
    Gera um identificador para RFO no formato RFO-XXXX/YYYY (ex: RFO-0001/2025).
    Usa a conex�o de banco fornecida por database.get_db() para contar ocorr�ncias
    do ano atual e retorna RFO-{seq:04d}/{year}. Se houver qualquer erro, cai
    para um fallback baseado em timestamp (�nico prop�sito de garantir retorno).
    """
    try:
        from datetime import datetime
        # obt�m get_db do m�dulo database (definido em database.py)
        from escola.database import get_db

        year = datetime.utcnow().strftime('%Y')
        try:
            db = get_db()
            row = db.execute("SELECT COUNT(*) as c FROM ocorrencias WHERE strftime('%Y', created_at) = ?", (year,)).fetchone()
            base_count = int(row['c']) if row and row['c'] is not None else 0
        except Exception:
            # se por alguma raz�o n�o temos acesso ao contexto Flask/get_db, usar 0
            base_count = 0

        seq = base_count + 1
        return f"RFO-{seq:04d}/{year}"
    except Exception:
        # fallback robusto por timestamp (n�o ideal, mas evita quebrar UI)
        from datetime import datetime
        year = datetime.utcnow().strftime('%Y')
        fallback_seq = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[-6:]
        return f"RFO-{fallback_seq}/{year}"

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
