from db_config import SessionLocal
from models_sqlalchemy import Aluno

def adiciona_aluno(**kwargs):
    session = SessionLocal()
    aluno = Aluno(**kwargs)
    session.add(aluno)
    session.commit()
    session.close()
    print(f"Aluno '{kwargs.get('nome_completo')}' adicionado!")

def lista_alunos():
    session = SessionLocal()
    alunos = session.query(Aluno).all()
    for aluno in alunos:
        print(f"{aluno.id}: {aluno.matricula} - {aluno.nome_completo} - {aluno.data_nascimento} - {aluno.data_matricula}")
    session.close()

if __name__ == "__main__":
    # Preencha todos os dados conforme desejar
    adiciona_aluno(
        matricula="20240102",
        nome_completo="João Completo SQLAlchemy",
        data_nascimento="2007-04-15",
        data_matricula="2024-02-01",
        serie="8º Ano",
        turma="B",
        turno="Manhã",
        pai="Carlos Silva",
        mae="Ana Souza",
        responsavel="Carlos Silva",
        telefone1="(11) 99999-9999",
        telefone2="(11) 98888-8888",
        telefone3="",
        email="joao.silva@email.com",
        endereco="Rua Direito, 123",
        bairro="Centro",
        cidade="São Paulo",
        estado="SP"
    )
    print("Lista de alunos cadastrados:")
    lista_alunos()