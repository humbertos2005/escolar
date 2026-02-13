import locale
from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv  # ← ADICIONAR

# ← CARREGAR .ENV ANTES DE TUDO
load_dotenv()

# Definição do Base para uso com SQLAlchemy
Base = declarative_base()

# Tentar configurar localização brasileira
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

# Lê de .env (agora vai funcionar!)
DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URI")

# Se não encontrou, usa SQLite como fallback (mas avisa!)
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{os.environ.get('DATABASE_FILE', 'escola.db')}"
    print(f"   [AVISO] SQLALCHEMY_DATABASE_URI não encontrado no .env. Usando SQLite: {DATABASE_URL}")

# Cria engine e sessionmaker
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Retorna uma sessão SQLAlchemy pronta para uso.
    """
    db = getattr(g, '_session_sqlalchemy', None)
    if db is None:
        db = g._session_sqlalchemy = SessionLocal()
    return db

def close_db(e=None):
    """
    Fecha a sessão SQLAlchemy, se aberta no contexto do Flask.
    """
    db = getattr(g, '_session_sqlalchemy', None)
    if db is not None:
        db.close()

def init_db():
    """
    Inicializa o banco, criando todas as tabelas definidas em models_sqlalchemy.py.
    """
    from models_sqlalchemy import Base
    Base.metadata.create_all(bind=engine)
