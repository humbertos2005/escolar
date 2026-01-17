from database import engine
from models_sqlalchemy import Base, Usuario
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from datetime import datetime

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")

    Session = sessionmaker(bind=engine)
    session = Session()
    if not session.query(Usuario).filter_by(username='admin_ti').first():
        usuario = Usuario(
            username='admin_ti',
            password=generate_password_hash('admin123'),
            nivel='1',
            data_criacao=datetime.now().isoformat(),  # opcional
            cargo='Administrador',                    # opcional
            email='admin@escola.com'
        )
        session.add(usuario)
        session.commit()
        print("Usuário admin_ti criado com sucesso!")
    else:
        print("Usuário admin_ti já existe.")
    session.close()