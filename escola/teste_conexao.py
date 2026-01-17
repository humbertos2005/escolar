from db_config import engine

def testar_conexao():
    try:
        with engine.connect() as conexao:
            print("Conexão com o banco via SQLAlchemy funcionou!")
    except Exception as e:
        print("Erro ao conectar:", e)

if __name__ == "__main__":
    testar_conexao()