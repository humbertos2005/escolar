from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models_sqlalchemy import (
    PontuacaoHistorico,
    FichaMedidaDisciplinar,
    medias_bimestrais, # tabela: id, aluno_id, ano, bimestre, media
    Bimestre
)
from database import get_db

def calcular_pontuacao_aluno(aluno_id, data_final=None):
    db = get_db()
    if data_final is None:
        data_final = datetime.now().date()
    elif isinstance(data_final, str):
        data_final = datetime.strptime(data_final, '%Y-%m-%d').date()

    pontuacao = 8.0

    # 1. Eventos disciplinares (penalidades/elogios)
    eventos = db.query(PontuacaoHistorico).filter(
        PontuacaoHistorico.aluno_id == aluno_id
    ).all()

    for evt in eventos:
        evt_date = evt.criado_em
        if isinstance(evt_date, str):
            try:
                evt_date = datetime.strptime(evt_date[:10], '%Y-%m-%d').date()
            except:
                continue
        if evt_date > data_final:
            continue
        pontuacao += float(evt.valor_delta)
        pontuacao = min(10.0, max(0.0, pontuacao))

    # 2. Bonificação bimestral
    bimestres = db.query(Bimestre).filter_by(ano=data_final.year).order_by(Bimestre.numero).all()
    for b in bimestres:
        bimestre_fim = b.fim
        if isinstance(bimestre_fim, str):
            bimestre_fim = datetime.strptime(bimestre_fim[:10], '%Y-%m-%d').date()
        if data_final >= bimestre_fim:
            mb = db.execute(
                "SELECT media FROM medias_bimestrais WHERE aluno_id = :aluno_id AND ano = :ano AND bimestre = :bimestre",
                {"aluno_id": aluno_id, "ano": b.ano, "bimestre": b.numero}
            ).fetchone()
            if mb and mb[0] >= 8.0:
                pontuacao += 0.5
                pontuacao = min(10.0, max(0.0, pontuacao))

    # 3. Bonificação dos 60 dias sem perder ponto
    ultimo_evento_negativo = None
    for evt in eventos:
        evt_date = evt.criado_em
        if isinstance(evt_date, str):
            try:
                evt_date = datetime.strptime(evt_date[:10], '%Y-%m-%d').date()
            except:
                continue
        if evt_date <= data_final and float(evt.valor_delta) < 0:
            if ultimo_evento_negativo is None or evt_date > ultimo_evento_negativo:
                ultimo_evento_negativo = evt_date

    if not ultimo_evento_negativo:
        # Considera data de matrícula
        matricula = db.execute(
            "SELECT data_matricula FROM alunos WHERE id = :aluno_id",
            {"aluno_id": aluno_id}
        ).fetchone()
        if matricula:
            ultimo_evento_negativo = matricula[0]
            if isinstance(ultimo_evento_negativo, str):
                ultimo_evento_negativo = datetime.strptime(ultimo_evento_negativo[:10], '%Y-%m-%d').date()

    if ultimo_evento_negativo:
        dias_sem_perda = (data_final - ultimo_evento_negativo).days
        if dias_sem_perda > 60:
            bonus = (dias_sem_perda - 60) * 0.2
            pontuacao += bonus
            pontuacao = min(10.0, max(0.0, pontuacao))

    # 4. Classificação
    if pontuacao == 10.0:
        comportamento = "Excepcional"
    elif pontuacao >= 9.0:
        comportamento = "Ótimo"
    elif pontuacao >= 7.0:
        comportamento = "Bom"
    elif pontuacao >= 5.0:
        comportamento = "Regular"
    elif pontuacao >= 2.0:
        comportamento = "Insuficiente"
    else:
        comportamento = "Incompatível"

    return {
        "pontuacao": round(pontuacao, 2),
        "comportamento": comportamento
    }