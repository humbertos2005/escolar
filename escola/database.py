import locale
from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base  # ADICIONADO declarative_base
import os

# Definição do Base para uso com SQLAlchemy
Base = declarative_base()  # <<--- LINHA CRUCIAL

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

# Lê de .env ou variável de ambiente, ou usa SQLite padrão
DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URI", f"sqlite:///{os.environ.get('DATABASE_FILE', 'escola.db')}")

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
    from models_sqlalchemy import Base  # Importa apenas aqui para evitar ciclos
    Base.metadata.create_all(bind=engine)
