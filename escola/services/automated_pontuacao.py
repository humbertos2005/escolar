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
    Calcula a pontuação do aluno com TODAS as regras corretas:
    
    1. Pontuação inicial = pontuação final do bimestre anterior (ou 8.0 se for o 1º)
    2. Bônus de 60 dias ACUMULATIVO desde o início do ANO LETIVO (não desde matrícula)
    3. Bonificação bimestral APENAS do bimestre imediatamente anterior
    4. Data de referência = início do 1º bimestre (ou matrícula se posterior)
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

    # ========================================
    # DETERMINAR PONTUAÇÃO INICIAL DO BIMESTRE
    # ========================================
    if bimestre == 1:
        # Primeiro bimestre sempre começa com 8.0
        pontuacao = 8.0
        print(f"DEBUG - Pontuação inicial (1º bimestre): 8.0")
    else:
        # Bimestres seguintes: pega média final do bimestre anterior
        media_ant = db.execute(
            text("SELECT media FROM medias_bimestrais WHERE aluno_id = :aluno_id AND ano = :ano AND bimestre = :bimestre"),
            {"aluno_id": aluno_id, "ano": int(ano), "bimestre": int(bimestre)-1}
        ).fetchone()
        
        if media_ant and media_ant[0] is not None:
            pontuacao = float(media_ant[0])
            print(f"DEBUG - Pontuação inicial (do bim anterior {int(bimestre)-1}): {pontuacao:.2f}")
        else:
            pontuacao = 8.0
            print(f"DEBUG - Pontuação inicial (sem registro anterior): 8.0")

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
        if evt.tipo_evento not in ["TRANSFERENCIA_BIMESTRE", "BIMESTRE_BONUS"]:
            pontuacao += float(evt.valor_delta)
            pontuacao = min(10.0, max(0.0, pontuacao))
            print(f"DEBUG - Evento aplicado: {evt.tipo_evento}, delta: {evt.valor_delta}, pontuação: {pontuacao:.2f}")
        else:
            print(f"DEBUG - Evento ignorado na soma: {evt.tipo_evento} em {evt_date}")

    # ========================================
    # 2. BONIFICAÇÃO BIMESTRAL (média >= 8.0)
    # REGRA: Apenas do bimestre IMEDIATAMENTE ANTERIOR
    # ========================================
    if bimestre > 1:
        # Pega média do bimestre anterior
        mb = db.execute(
            text("SELECT media FROM medias_bimestrais WHERE aluno_id = :aluno_id AND ano = :ano AND bimestre = :bimestre"),
            {"aluno_id": aluno_id, "ano": int(ano), "bimestre": int(bimestre)-1}
        ).fetchone()
        
        if mb and mb[0] >= 8.0:
            pontuacao += 0.5
            pontuacao = min(10.0, max(0.0, pontuacao))
            print(f"DEBUG - Bônus bimestral aplicado (bim {int(bimestre)-1}): +0.5, média: {mb[0]:.2f}")

    # ========================================
    # 3. BONIFICAÇÃO DOS 60 DIAS SEM PERDER PONTO
    # REGRA CRÍTICA: Acumulativo desde INÍCIO DO 1º BIMESTRE do ano
    # ========================================
    
    # Busca o 1º bimestre do ano
    bim_1 = db.query(Bimestre).filter_by(ano=int(ano), numero=1).first()
    if not bim_1:
        print("DEBUG - ERRO: 1º bimestre não encontrado!")
        data_inicio_ano = data_final
    else:
        data_inicio_ano = bim_1.inicio
        if isinstance(data_inicio_ano, str):
            data_inicio_ano = datetime.strptime(data_inicio_ano[:10], '%Y-%m-%d').date()
    
    # Busca data de matrícula
    matricula_row = db.execute(
        text("SELECT data_matricula FROM alunos WHERE id = :aluno_id"),
        {"aluno_id": aluno_id}
    ).fetchone()
    
    data_matricula = None
    if matricula_row and matricula_row[0]:
        data_matricula = matricula_row[0]
        if isinstance(data_matricula, str):
            data_matricula = datetime.strptime(data_matricula[:10], '%Y-%m-%d').date()
    
    # REGRA: Se matriculado ANTES do 1º bim, referência = início do 1º bim
    #        Se matriculado DEPOIS, referência = data de matrícula
    if data_matricula and data_matricula < data_inicio_ano:
        data_referencia_inicial = data_inicio_ano
        tipo_referencia = f"início do 1º bimestre (matrícula anterior: {data_matricula})"
    elif data_matricula:
        data_referencia_inicial = data_matricula
        tipo_referencia = "matrícula (posterior ao início do ano)"
    else:
        data_referencia_inicial = data_inicio_ano
        tipo_referencia = "início do 1º bimestre (sem data de matrícula)"
    
    # Verifica se houve alguma falta que reseta a contagem
    eventos_negativos = [
        (evt.criado_em if not isinstance(evt.criado_em, str) 
         else datetime.strptime(evt.criado_em[:10], '%Y-%m-%d').date())
        for evt in eventos_aplicados
        if float(evt.valor_delta) < 0
    ]

    if eventos_negativos:
        # Última falta reseta a contagem
        data_referencia = max(eventos_negativos)
        tipo_referencia = f"última falta em {data_referencia}"
    else:
        # Sem faltas: usa referência inicial
        data_referencia = data_referencia_inicial

    # ========================================
    # CORREÇÃO: SOMA DIAS DE CADA BIMESTRE
    # ========================================
    
    # Busca todos os bimestres do ano até o bimestre atual
    bimestres_ano = db.query(Bimestre).filter_by(ano=int(ano)).filter(
        Bimestre.numero <= int(bimestre)
    ).order_by(Bimestre.numero).all()
    
    total_dias = 0
    detalhes_dias = []
    
    for bim in bimestres_ano:
        bim_inicio = bim.inicio
        bim_fim = bim.fim
        
        # Converte para date se necessário
        if isinstance(bim_inicio, str):
            bim_inicio = datetime.strptime(bim_inicio[:10], '%Y-%m-%d').date()
        if isinstance(bim_fim, str):
            bim_fim = datetime.strptime(bim_fim[:10], '%Y-%m-%d').date()
        
        # Ajusta as datas conforme a referência e o bimestre atual
        if bim.numero == 1:
            # 1º bimestre: usar a data de referência como início
            inicio_calculo = max(data_referencia, bim_inicio)
        else:
            # Demais bimestres: usar início do bimestre
            inicio_calculo = bim_inicio
        
        # Se for o bimestre atual, usar data_final
        if bim.numero == int(bimestre):
            fim_calculo = data_final
        else:
            fim_calculo = bim_fim
        
        # Calcula dias deste bimestre
        dias_bimestre = (fim_calculo - inicio_calculo).days + 1
        
        # Só conta se for positivo
        if dias_bimestre > 0:
            total_dias += dias_bimestre
            detalhes_dias.append(f"{bim.numero}º:{dias_bimestre}d")
    
    # Atualiza variável para manter compatibilidade
    dias_sem_perda = total_dias
    
    print(f"DEBUG - Início do 1º bimestre: {data_inicio_ano}")
    print(f"DEBUG - Data de matrícula: {data_matricula}")
    print(f"DEBUG - Referência para bônus: {tipo_referencia}")
    print(f"DEBUG - Bimestres: {' + '.join(detalhes_dias)} = {dias_sem_perda} dias")

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
    else:
        print(f"DEBUG - Menos de 60 dias, sem bônus aplicado")

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