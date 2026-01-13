from db_config import SessionLocal
from models_sqlalchemy import Aluno

def adiciona_aluno(nome):
    session = SessionLocal()
    novo = Aluno(nome=nome)
    session.add(novo)
    session.commit()
    session.close()
    print(f"Aluno '{nome}' adicionado!")

def adiciona_aluno(matricula, nome):
    session = SessionLocal()
    novo = Aluno(matricula=matricula, nome=nome)
    session.add(novo)
    session.commit()
    session.close()
    print(f"Aluno '{nome}' adicionado!")

def lista_alunos():
    session = SessionLocal()
    alunos = session.query(Aluno).all()
    for aluno in alunos:
        print(f"{aluno.id}: {aluno.nome}")
    session.close()

if __name__ == "__main__":
    adiciona_aluno("20240101", "Maria Teste SQLAlchemy")
    print("Lista de alunos cadastrados:")
    lista_alunos()