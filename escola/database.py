import sqlite3
from flask import g
import locale
import os
from dotenv import load_dotenv
load_dotenv()  # Garante leitura das variáveis no .env

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

DATABASE = os.getenv('DATABASE_PATH', 'escola.db')

def get_db():
    """
    Retorna a conexão com o banco de dados. 
    Cria uma nova se não existir no contexto de requisição.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Permite acesso às colunas como atributos de dicionário
        db.row_factory = sqlite3.Row
        # Habilita chaves estrangeiras para integridade referencial
        db.execute('PRAGMA foreign_keys = ON')
    return db

def init_db():
    """
    Função de inicialização básica do banco de dados.
    Garante que o arquivo exista e cria as tabelas.
    """
    # Importação local para evitar circularidade, já que models.py importa get_db de database.py
    from models import criar_tabelas
    criar_tabelas()

def close_db(e=None):
    """
    Fecha a conexão com o banco de dados se ela tiver sido aberta no contexto.
    Usada principalmente com @app.teardown_appcontext.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def executar_query(query, params=(), fetch_one=False, fetch_all=False):
    """
    Função auxiliar para executar queries com tratamento de erro.
    Útil para operações que não estão no contexto de requisição Flask.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor
            
        conn.commit()
        return result
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Erro ao executar query: {e}")
        return None
        
    finally:
        if conn:
            conn.close()
