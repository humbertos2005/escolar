from db_config import engine
from models_sqlalchemy import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")
