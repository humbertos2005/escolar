"""Criação inicial das tabelas

Revision ID: 9566c35464b4
Revises: 
Create Date: 2026-01-17 14:34:36.657944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9566c35464b4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'alunos',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('matricula', sa.String, nullable=False),
        sa.Column('nome', sa.String, nullable=False),
        sa.Column('serie', sa.String, nullable=True),
        sa.Column('turma', sa.String, nullable=True),
        sa.Column('turno', sa.String, nullable=True),
        sa.Column('pai', sa.String, nullable=True),
        sa.Column('mae', sa.String, nullable=True),
        sa.Column('responsavel', sa.String, nullable=True),
        sa.Column('email', sa.String, nullable=True),
        sa.Column('rua', sa.String, nullable=True),
        sa.Column('numero', sa.String, nullable=True),
        sa.Column('complemento', sa.String, nullable=True),
        sa.Column('bairro', sa.String, nullable=True),
        sa.Column('cidade', sa.String, nullable=True),
        sa.Column('estado', sa.String, nullable=True),
        sa.Column('data_cadastro', sa.String, nullable=True),
        sa.Column('telefone', sa.String, nullable=True),
        sa.Column('photo', sa.String, nullable=True),
        sa.Column('data_matricula', sa.String, nullable=True),
        sa.Column('data_nascimento', sa.String, nullable=True),
    )
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('username', sa.String, nullable=False),
        sa.Column('password', sa.String, nullable=False),
        sa.Column('nivel', sa.String, nullable=True),
        sa.Column('data_criacao', sa.String, nullable=True),
        sa.Column('cargo', sa.String, nullable=True),
        sa.Column('email', sa.String, nullable=True),
    )
    # Adicione aqui todos os outros blocos de op.create_table para as demais tabelas do sistema
    # Basta replicar o padrão acima para cada tabela principal do seu sistema

def downgrade() -> None:
    pass
