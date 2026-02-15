from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models_sqlalchemy import (
    PontuacaoHistorico,
    FichaMedidaDisciplinar,
    MediaBimestral,
    Bimestre,
    Aluno
)
from database import get_db
from sqlalchemy import text

def calcular_pontuacao_aluno(aluno_id, data_final=None, ano=None, bimestre=None):
    """
    Calcula a pontuação do aluno considerando:
    - Eventos disciplinares até a data_final
    - Bonificações bimestrais
    - Bônus de 60 dias sem perder pontos (ACUMULATIVO entre bimestres)
    
    CORREÇÃO FINAL: Bônus acumula continuamente entre bimestres
    """
    print(f"DEBUG - aluno_id: {aluno_id}, data_final: {data_final}, ano: {ano}, bimestre: {bimestre}")
    db = get_db()
    
    # ========================================
    # DETERMINAR DATA LIMITE PARA CÁLCULO
    # ========================================
    if ano and bimestre:
        bim_obj = db.query(Bimestre).filter_by(ano=int(ano), numero=int(bimestre)).first()
        if bim_obj:
            data_final = bim_obj.fim
            if isinstance(data_final, str):
                data_final = datetime.strptime(data_final[:10], '%Y-%m-%d').date()
            print(f"DEBUG - Calculando para bimestre {ano}/{bimestre}, data_final ajustada: {data_final}")
        else:
            if data_final is None:
                data_final = datetime.now().date()
            elif isinstance(data_final, str):
                data_final = datetime.strptime(data_final, '%Y-%m-%d').date()
    else:
        if data_final is None:
            data_final = datetime.now().date()
        elif isinstance(data_final, str):
            data_final = datetime.strptime(data_final, '%Y-%m-%d').date()

    pontuacao = 8.0

    # ========================================
    # 1. EVENTOS DISCIPLINARES (PENALIDADES/ELOGIOS)
    # ========================================
    eventos = db.query(PontuacaoHistorico).filter(
        PontuacaoHistorico.aluno_id == aluno_id
    ).all()

    eventos_aplicados = []
    for evt in eventos:
        evt_date = evt.criado_em
        if isinstance(evt_date, str):
            try:
                evt_date = datetime.strptime(evt_date[:10], '%Y-%m-%d').date()
            except:
                continue
        
        # Só aplicar eventos até a data_final
        if evt_date > data_final:
            continue
            
        eventos_aplicados.append(evt)
        
        # Ignorar TRANSFERENCIA_BIMESTRE na soma direta
        if evt.tipo_evento not in ["TRANSFERENCIA_BIMESTRE"]:
            pontuacao += float(evt.valor_delta)
            pontuacao = min(10.0, max(0.0, pontuacao))
            print(f"DEBUG - Evento aplicado: {evt.tipo_evento}, delta: {evt.valor_delta}, pontuação: {pontuacao}")
        else:
            print(f"DEBUG - Evento ignorado na soma direta: {evt.tipo_evento} em {evt_date}")

    # ========================================
    # 2. BONIFICAÇÃO BIMESTRAL (média >= 8.0)
    # CORREÇÃO: Aplicar apenas para bimestres ANTERIORES ao atual
    # ========================================
    if ano and bimestre:
        # Para o bimestre N, aplicar bônus dos bimestres 1 até N-1
        for n in range(1, int(bimestre)):
            mb = db.execute(
                text("SELECT media FROM medias_bimestrais WHERE aluno_id = :aluno_id AND ano = :ano AND bimestre = :bimestre"),
                {"aluno_id": aluno_id, "ano": int(ano), "bimestre": n}
            ).fetchone()
            
            if mb and mb[0] >= 8.0:
                pontuacao += 0.5
                pontuacao = min(10.0, max(0.0, pontuacao))
                print(f"DEBUG - Bônus bimestral aplicado: {ano}/{n}, média: {mb[0]:.2f}")

    # ========================================
    # 3. BONIFICAÇÃO DOS 60 DIAS SEM PERDER PONTO
    # CORREÇÃO CRÍTICA: Cálculo ACUMULATIVO contínuo
    # ========================================
    
    # Encontra a data de referência (último evento negativo ou matrícula)
    eventos_negativos = [
        (evt.criado_em if not isinstance(evt.criado_em, str) 
         else datetime.strptime(evt.criado_em[:10], '%Y-%m-%d').date())
        for evt in eventos_aplicados
        if float(evt.valor_delta) < 0
    ]

    if eventos_negativos:
        # Último evento negativo
        data_referencia = max(eventos_negativos)
        tipo_referencia = "última falta"
    else:
        # Sem faltas: usar data de matrícula
        matricula_row = db.execute(
            text("SELECT data_matricula FROM alunos WHERE id = :aluno_id"),
            {"aluno_id": aluno_id}
        ).fetchone()
        
        if matricula_row and matricula_row[0]:
            data_matricula = matricula_row[0]
            if isinstance(data_matricula, str):
                data_matricula = datetime.strptime(data_matricula[:10], '%Y-%m-%d').date()
            data_referencia = data_matricula
            tipo_referencia = "matrícula"
        else:
            # Fallback: início do bimestre atual
            bim_obj = db.query(Bimestre).filter_by(ano=int(ano), numero=int(bimestre)).first()
            if bim_obj:
                data_referencia = bim_obj.inicio
                if isinstance(data_referencia, str):
                    data_referencia = datetime.strptime(data_referencia[:10], '%Y-%m-%d').date()
            else:
                data_referencia = data_final
            tipo_referencia = "início do bimestre"

    # Calcula TOTAL de dias sem perder ponto (acumulativo)
    dias_sem_perda = (data_final - data_referencia).days + 1
    print(f"DEBUG - Referência para bônus: {tipo_referencia} em {data_referencia}")
    print(f"DEBUG - Dias sem perda de pontos (ACUMULATIVO): {dias_sem_perda}")

    if dias_sem_perda > 60:
        dias_bonus = dias_sem_perda - 60
        bonus_bruto = dias_bonus * 0.2
        
        # Aplicar o bônus respeitando o teto de 10.0
        espaco_disponivel = 10.0 - pontuacao
        bonus_aplicado = min(bonus_bruto, espaco_disponivel)
        
        pontuacao += bonus_aplicado
        pontuacao = min(10.0, max(0.0, pontuacao))
        
        print(f"DEBUG - Dias de bônus: {dias_bonus}")
        print(f"DEBUG - Bônus bruto calculado: {bonus_bruto:.2f} pontos")
        print(f"DEBUG - Espaço disponível até 10.0: {espaco_disponivel:.2f}")
        print(f"DEBUG - Bônus aplicado (limitado): {bonus_aplicado:.2f} pontos")

    # ========================================
    # 4. CLASSIFICAÇÃO
    # ========================================
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

    print(f"DEBUG - Pontuação final: {pontuacao:.2f}, Comportamento: {comportamento}")
    print("=" * 80)

    return {
        "pontuacao": round(pontuacao, 2),
        "comportamento": comportamento
    }