import locale

# Tentar configurar localiza��o brasileira
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except:
            print("   [AVISO] N�o foi poss�vel configurar localiza��o PT-BR")

from flask import g
from .db_config import SessionLocal, engine

def get_db():
    """
    Retorna a sess�o do banco de dados. Cria uma nova se n�o existir no contexto da requisi��o.
    """
    db = getattr(g, "_session_db", None)
    if db is None:
        db = g._session_db = SessionLocal()
    return db

def close_db(e=None):
    """
    Fecha a sess�o do banco de dados, se aberta no contexto.
    Usado com @app.teardown_appcontext.
    """
    db = getattr(g, "_session_db", None)
    if db is not None:
        db.close()

def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas a partir dos models (ORM).
    """
    from .models_sqlalchemy import Base  # Garanta que Base est� em models_sqlalchemy.py
    Base.metadata.create_all(bind=engine)

def executar_query(query_fn, fetch_one=False, fetch_all=False):
    """
    Executa fun��o recebendo uma sess�o SQLAlchemy, retornando resultado.
    Exemplo de uso:
        def exemplo(sess):
            return sess.query(Tabela).filter(...).first()
        dado = executar_query(exemplo, fetch_one=True)
    """
    db = SessionLocal()
    result = None
    try:
        data = query_fn(db)
        if fetch_one:
            result = data if data else None
        elif fetch_all:
            result = data if data else []
        else:
            result = data
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        print(f"Erro ao executar query: {e}")
        return None
    finally:
        db.close()
