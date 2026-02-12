# scripts/pontuacao_rotinas.py
"""
Rotinas para bonificações de pontuação:
- apply_bimestral_bonus: aplica +0.5 para alunos com média bimestral >= 8.0
- apply_no_loss_daily: aplica +0.2/dia para alunos sem perda nos últimos 60 dias, a partir do 61º dia, nunca antes da matrícula e nunca em duplicidade.

Uso manual:
  py -m scripts.pontuacao_rotinas apply_bimestral_bonus 2025 1 [--force]
  py -m scripts.pontuacao_rotinas apply_no_loss_daily 2025-04-04 [--ate 2025-04-11]

Uso automático: basta importar e chamar as funções diretamente.
"""

from __future__ import annotations
import argparse
from datetime import datetime, date, timedelta

from app import app
from database import get_db
from blueprints import alunos, disciplinar
from models_sqlalchemy import PontuacaoBimestral, PontuacaoHistorico, Aluno

from sqlalchemy import text

def apply_bimestral_bonus(ano: int, bimestre: int, force=False):
    """
    Aplica +0.5 para cada aluno com matrícula até o fim do bimestre,
    apenas se o aluno tiver média >= 8.0 no bimestre e não tiver recebido antes (a não ser que force).
    """
    with app.app_context():
        db = get_db()
        fim_bimestre = db.execute(
            text("SELECT fim FROM bimestres WHERE ano = :ano AND numero = :bimestre"),
            {"ano": ano, "bimestre": bimestre}
        ).fetchone()
        data_bimestre_fim = fim_bimestre[0] if fim_bimestre and fim_bimestre[0] else f"{ano}-12-31"

        alunos_data = db.query(Aluno.id, Aluno.data_matricula).all()
        applied = 0
        for aluno_id, data_matricula in alunos_data:
            # Só alunos matriculados antes do fim do bimestre
            if not data_matricula or data_matricula > data_bimestre_fim:
                continue
            # Evita duplicidade de lançamento
            if not force:
                h = (
                    db.query(PontuacaoHistorico)
                    .filter_by(aluno_id=aluno_id, ano=ano, bimestre=bimestre, tipo_evento='BIMESTRE_BONUS')
                    .first()
                )
                if h:
                    continue
            # Confirma média >= 8.0 do aluno para o bimestre
            mb_row = db.execute(
                text("SELECT media FROM medias_bimestrais WHERE aluno_id = :aluno_id AND ano = :ano AND bimestre = :bimestre"),
                {"aluno_id": aluno_id, "ano": ano, "bimestre": bimestre}
            ).fetchone()
            if not mb_row or mb_row[0] < 8.0:
                continue
            try:
                disciplinar._apply_delta_pontuacao(
                    db, aluno_id, str(data_bimestre_fim), 0.5,
                    ocorrencia_id=None, tipo_evento="BIMESTRE_BONUS"
                )
                applied += 1
            except Exception:
                app.logger.exception(f"Erro ao aplicar bonus bimestral para aluno_id={aluno_id}")
        db.commit()
        print(f"[INFO] Bônus bimestral de +0.5 aplicado para {applied} alunos em {ano} b{bimestre}.")

def aluno_sem_perda_periodo(db, aluno_id, data_inicio: date, data_fim: date) -> bool:
    """
    Retorna True se NÃO houver registro com valor_delta < 0 entre data_inicio e data_fim.
    """
    existe_perda = (
        db.query(PontuacaoHistorico)
        .filter(
            PontuacaoHistorico.aluno_id == aluno_id,
            PontuacaoHistorico.criado_em >= data_inicio.strftime("%Y-%m-%d"),
            PontuacaoHistorico.criado_em < (data_fim + timedelta(days=1)).strftime("%Y-%m-%d"),
            PontuacaoHistorico.valor_delta < 0
        )
        .first()
    )
    return existe_perda is None

def apply_no_loss_daily(data_inicio: date, data_fim: date = None):
    """
    Aplica +0.2 ao bimestre atual para cada aluno, a cada dia do intervalo [data_inicio, data_fim]
    desde que os 60 dias anteriores sejam sem perda E o aluno já esteja matriculado há 60 dias completos.
    NUNCA lança duplicado para o mesmo dia/aluno!
    """
    with app.app_context():
        db = get_db()
        if data_fim is None:
            data_fim = data_inicio
        dias = (data_fim - data_inicio).days + 1
        total_aplicados = 0

        alunos_data = db.query(Aluno.id, Aluno.data_matricula).all()

        for i in range(dias):
            check_date = data_inicio + timedelta(days=i)
            ano, bimestre = disciplinar._get_bimestre_for_date(db, check_date.strftime("%Y-%m-%d"))
            inicio_period = check_date - timedelta(days=60)
            fim_period = check_date - timedelta(days=1)
            applied = 0
            for aluno_id, data_matricula in alunos_data:
                if not data_matricula:
                    continue
                # Só conta quem está matriculado há pelo menos 60 dias completos antes do check_date
                if data_matricula > inicio_period:
                    continue
                # Evita duplicidade de lançamento para o mesmo dia
                existe = (
                    db.query(PontuacaoHistorico)
                    .filter_by(aluno_id=aluno_id, ano=ano, bimestre=bimestre, tipo_evento="NO_LOSS_DAILY")
                    .filter(PontuacaoHistorico.criado_em == check_date.strftime("%Y-%m-%d"))
                    .first()
                )
                if existe:
                    continue
                try:
                    if aluno_sem_perda_periodo(db, aluno_id, inicio_period, fim_period):
                        disciplinar._apply_delta_pontuacao(
                            db, aluno_id, check_date.strftime("%Y-%m-%d"), 0.2,
                            ocorrencia_id=None, tipo_evento="NO_LOSS_DAILY"
                        )
                        applied += 1
                        total_aplicados += 1
                except Exception:
                    app.logger.exception(f"Erro no no-loss daily para aluno_id={aluno_id} ({check_date})")
            db.commit()
            print(f"[INFO] {check_date}: bônus diário +0.2 aplicado para {applied} alunos (período {inicio_period.isoformat()}..{fim_period.isoformat()})")
        print(f"[INFO] Total no-loss daily bônus lançados: {total_aplicados}")

# --- Rotinas para integração automática ou manual ---

def executar_rotinas_automaticas():
    """
    Chamada principal para o agendador automático:
    - Aplica a bonificação diária dos 60 dias para 'hoje'
    - Aplica bonificação bimestral se for o último dia de algum bimestre
    """
    hoje = date.today()
    with app.app_context():
        db = get_db()
        # Bonificação diária (para hoje)
        apply_no_loss_daily(hoje, hoje)
        # Verifica se é fim de algum bimestre
        bimestre_fim = db.execute(
            text("SELECT ano, numero FROM bimestres WHERE fim = :data"),
            {"data": hoje.strftime("%Y-%m-%d")}
        ).fetchall()
        for row in bimestre_fim:
            ano, num = row
            # Aplica bônus bimestral automático no fim do bimestre
            apply_bimestral_bonus(ano, num)
        print("[INFO] Rotinas automáticas de pontuação executadas para hoje.")

# --- Modo manual (terminal) ---

def corrigir_bonificacoes_retroativas():
    """
    Para TODOS os alunos matriculados,
    verifica desde o 61º dia de matrícula até ontem (ou hoje, se preferir),
    e lança automaticamente TODO bônus diário (+0,2) devido e não lançado na tabela pontuacao_historico,
    sem duplicidade, respeitando as regras já existentes.
    """
    from datetime import date

    with app.app_context():
        db = get_db()
        total_bonificacoes = 0
        alunos_data = db.query(Aluno.id, Aluno.data_matricula).all()

        hoje = date.today()

        for aluno_id, data_matricula in alunos_data:
            if not data_matricula:
                continue

            # Busca a data do primeiro evento negativo OU data de matrícula
            evento_neg = db.query(PontuacaoHistorico)\
                .filter(
                    PontuacaoHistorico.aluno_id == aluno_id,
                    PontuacaoHistorico.valor_delta < 0
                )\
                .order_by(PontuacaoHistorico.criado_em.asc())\
                .first()
            data_referencia = data_matricula
            if evento_neg:
                data_referencia = evento_neg.criado_em if evento_neg.criado_em > data_matricula else data_matricula
            if isinstance(data_referencia, str):
                from datetime import datetime
                data_referencia = datetime.strptime(data_referencia[:10], '%Y-%m-%d').date()

            # O aluno só pode ganhar após completar 60 dias sem perda
            inicio_checagem = data_referencia + timedelta(days=60)
            fim_checagem = hoje - timedelta(days=1)  # Até ontem

            dia = inicio_checagem
            while dia <= fim_checagem:
                ano, bimestre = disciplinar._get_bimestre_for_date(db, dia.strftime("%Y-%m-%d"))
                # Não lançar se já existe o bônus nesse dia
                existe = (
                    db.query(PontuacaoHistorico)
                    .filter_by(aluno_id=aluno_id, ano=ano, bimestre=bimestre, tipo_evento="NO_LOSS_DAILY")
                    .filter(PontuacaoHistorico.criado_em == dia.strftime("%Y-%m-%d"))
                    .first()
                )
                if existe:
                    dia += timedelta(days=1)
                    continue
                # Checa se houve alguma perda nos 60 dias anteriores
                inicio_period = dia - timedelta(days=60)
                fim_period = dia - timedelta(days=1)
                if aluno_sem_perda_periodo(db, aluno_id, inicio_period, fim_period):
                    try:
                        disciplinar._apply_delta_pontuacao(
                            db, aluno_id, dia.strftime("%Y-%m-%d"), 0.2,
                            ocorrencia_id=None, tipo_evento="NO_LOSS_DAILY"
                        )
                        total_bonificacoes += 1
                    except Exception:
                        app.logger.exception(f"[RETROATIVO] Erro no lançamento retroativo aluno_id={aluno_id}, dia={dia}")
                dia += timedelta(days=1)
            db.commit()
        print(f"[INFO] Correção retroativa concluída. Bonificações diárias lançadas: {total_bonificacoes}")

def corrigir_bonificacoes_bimestrais_retroativas():
    """
    Para todos os alunos e todos os bimestres já passados,
    lança automaticamente o bônus bimestral (+0,5) caso a média bimestral seja >= 8.0 e ainda não tenha sido lançado,
    respeitando a data de matrícula e evitando duplicidade.
    """
    from datetime import date, datetime

    with app.app_context():
        db = get_db()
        total_bonificacoes = 0
        hoje = date.today()
        alunos_data = db.query(Aluno.id, Aluno.data_matricula).all()

        bimestres = db.execute(
            text("SELECT ano, numero, fim FROM bimestres WHERE fim < :hoje ORDER BY ano, numero"),
            {"hoje": hoje.strftime("%Y-%m-%d")}
        ).fetchall()

        for aluno_id, data_matricula in alunos_data:
            if not data_matricula:
                continue
            if isinstance(data_matricula, str):
                from datetime import datetime
                data_matricula = datetime.strptime(data_matricula[:10], "%Y-%m-%d").date()
            for bimestre_row in bimestres:
                ano, num, fim = bimestre_row
                # Verifica se aluno estava matriculado antes do fim do bimestre
                fim_dt = fim if isinstance(fim, date) else datetime.strptime(str(fim)[:10], '%Y-%m-%d').date()
                if data_matricula > fim_dt:
                    continue
                # Verifica duplicidade -- se bônus já lançado
                exists = (
                    db.query(PontuacaoHistorico)
                    .filter_by(aluno_id=aluno_id, ano=ano, bimestre=num, tipo_evento="BIMESTRE_BONUS")
                    .first()
                )
                if exists:
                    continue
                # Checa média bimestral
                mb_row = db.execute(
                    text("SELECT media FROM medias_bimestrais WHERE aluno_id = :aluno_id AND ano = :ano AND bimestre = :bimestre"),
                    {"aluno_id": aluno_id, "ano": ano, "bimestre": num}
                ).fetchone()
                if not mb_row or mb_row[0] < 8.0:
                    continue
                try:
                    disciplinar._apply_delta_pontuacao(
                        db, aluno_id, str(fim_dt), 0.5,
                        ocorrencia_id=None, tipo_evento="BIMESTRE_BONUS"
                    )
                    total_bonificacoes += 1
                    print(f"[RETRO BIMESTRE] aluno_id={aluno_id}, ano={ano}, bimestre={num}, lançado em {fim_dt}")
                except Exception:
                    app.logger.exception(f"[RETRO BIMESTRE] Erro para aluno_id={aluno_id}, ano={ano}, bimestre={num}")
            db.commit()
        print(f"[INFO] Correção retroativa bimestral concluída. Bonificações lançadas: {total_bonificacoes}")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p1 = sub.add_parser('apply_bimestral_bonus')
    p1.add_argument('ano', type=int)
    p1.add_argument('bimestre', type=int)
    p1.add_argument('--force', action='store_true')
    p2 = sub.add_parser('apply_no_loss_daily')
    p2.add_argument('date', type=str, help='data inicial YYYY-MM-DD (ou data única)')
    p2.add_argument('--ate', type=str, default=None, help='data final YYYY-MM-DD (opcional)')
    p3 = sub.add_parser('executar_rotinas_automaticas')
    p4 = sub.add_parser('corrigir_bonificacoes_retroativas')
    p5 = sub.add_parser('corrigir_bonificacoes_bimestrais_retroativas')
    args = parser.parse_args()
    if args.cmd == 'apply_bimestral_bonus':
        apply_bimestral_bonus(args.ano, args.bimestre, force=args.force)
    elif args.cmd == 'apply_no_loss_daily':
        data_inicio = datetime.strptime(args.date, "%Y-%m-%d").date()
        data_fim = datetime.strptime(args.ate, "%Y-%m-%d").date() if args.ate else None
        apply_no_loss_daily(data_inicio, data_fim)
    elif args.cmd == 'executar_rotinas_automaticas':
        executar_rotinas_automaticas()
    elif args.cmd == 'corrigir_bonificacoes_retroativas':
        corrigir_bonificacoes_retroativas()
    elif args.cmd == 'corrigir_bonificacoes_bimestrais_retroativas':
        corrigir_bonificacoes_bimestrais_retroativas()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()


