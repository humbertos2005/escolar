from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True)
    matricula = Column(String, nullable=False)
    nome_completo = Column(String, nullable=False)
    data_nascimento = Column(String)
    data_matricula = Column(String)
    serie = Column(String)
    turma = Column(String)
    turno = Column(String)
    pai = Column(String)
    mae = Column(String)
    responsavel = Column(String)
    telefone1 = Column(String)
    telefone2 = Column(String)
    telefone3 = Column(String)
    email = Column(String)
    endereco = Column(String)
    bairro = Column(String)
    cidade = Column(String)
    estado = Column(String)