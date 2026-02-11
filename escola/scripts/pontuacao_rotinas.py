# scripts/pontuacao_rotinas.py
"""
Rotinas para bonificações de pontuação:
- apply_bimestral_bonus: aplica +0.5 para alunos com média bimestral >= 8.0
- apply_no_loss_daily: aplica +0.2/dia para alunos sem perda nos últimos 60 dias

Uso (executar como módulo do package):
  py -m scripts.pontuacao_rotinas apply_bimestral_bonus 2025 1 [--force]
  py -m scripts.pontuacao_rotinas apply_no_loss_daily 2025-12-31

OBS: substituir get_media_bimestral() pela consulta real das notas via ORM.
"""
from __future__ import annotations
import argparse
from datetime import datetime, date, timedelta

from app import app
from database import get_db
from blueprints import alunos, disciplinar

# IMPORT MODELS ORM
from models_sqlalchemy import PontuacaoBimestral, PontuacaoHistorico

from sqlalchemy import text

def apply_bimestral_bonus(ano: int, bimestre: int, force=False):
    """Aplica +0.5 para cada aluno com média_bimestral >= 8.0."""
    with app.app_context():
        db = get_db()
        alunos = db.execute(text("SELECT id FROM alunos")).fetchall()
        alunos_ids = [row[0] for row in alunos]
        applied = 0

        # Obtém a data do fim do bimestre para lançamento correto
        fim_bimestre = db.execute(
            text("SELECT fim FROM bimestres WHERE ano = :ano AND numero = :bimestre"),
            {"ano": ano, "bimestre": bimestre}
        ).fetchone()
        data_bimestre_fim = fim_bimestre[0] if fim_bimestre and fim_bimestre[0] else f"{ano}-12-31"

        for aluno_id in alunos_ids:
            if not force:
                h = (
                    db.query(PontuacaoHistorico)
                    .filter_by(aluno_id=aluno_id, ano=ano, bimestre=bimestre, tipo_evento='BIMESTRE_BONUS')
                    .first()
                )
                if h:
                    continue
            try:
                disciplinar._apply_delta_pontuacao(
                    db, aluno_id, data_bimestre_fim, 0.5,
                    ocorrencia_id=None, tipo_evento="BIMESTRE_BONUS"
                )
                applied += 1
            except Exception:
                app.logger.exception("Erro ao aplicar bonus bimestral para aluno_id=%s", aluno_id)
        db.commit()
        print(f"Bônus bimestral de +0.5 aplicado automaticamente para {applied} alunos em {ano} b{bimestre}.")

def aluno_sem_perda_periodo(db, aluno_id, data_inicio: date, data_fim: date) -> bool:
    """Retorna True se NÃO houver registro com valor_delta < 0 entre data_inicio e data_fim."""
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

def apply_no_loss_daily(check_date: date):
    """
    Se os 60 dias anteriores não contiverem perda (valor_delta < 0),
    aplica +0.2 ao bimestre atual para cada aluno (destinado a rodar diariamente).
    """
    with app.app_context():
        db = get_db()
        ano, bimestre = disciplinar._get_bimestre_for_date(db, check_date.strftime("%Y-%m-%d"))
        alunos = db.execute(text("SELECT id FROM alunos")).fetchall()
        alunos_ids = [row[0] for row in alunos]
        applied = 0
        inicio_period = check_date - timedelta(days=60)
        fim_period = check_date - timedelta(days=1)
        for aluno_id in alunos_ids:
            try:
                if aluno_sem_perda_periodo(db, aluno_id, inicio_period, fim_period):
                    disciplinar._apply_delta_pontuacao(
                        db, aluno_id, check_date.strftime("%Y-%m-%d"), 0.2,
                        ocorrencia_id=None, tipo_evento="NO_LOSS_DAILY"
                    )
                    applied += 1
            except Exception:
                app.logger.exception("Erro ao aplicar no-loss daily para aluno_id=%s", aluno_id)
        db.commit()
        print(f"Applied no-loss daily bonus to {applied} alunos for {check_date.isoformat()} (period {inicio_period.isoformat()}..{fim_period.isoformat()}).")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p1 = sub.add_parser('apply_bimestral_bonus')
    p1.add_argument('ano', type=int)
    p1.add_argument('bimestre', type=int)
    p1.add_argument('--force', action='store_true')
    p2 = sub.add_parser('apply_no_loss_daily')
    p2.add_argument('date', type=str, help='date YYYY-MM-DD (use today)')
    args = parser.parse_args()
    if args.cmd == 'apply_bimestral_bonus':
        apply_bimestral_bonus(args.ano, args.bimestre, force=args.force)
    elif args.cmd == 'apply_no_loss_daily':
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        apply_no_loss_daily(d)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
