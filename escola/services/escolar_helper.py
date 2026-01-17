# services/escolar_helper.py

from datetime import datetime, timedelta, date
import calendar
from sqlalchemy.orm import Session
from sqlalchemy import func
from escola.models_sqlalchemy import (
    RFOSequencia, FMDSequencia,
    FaltaDisciplinar, TipoOcorrencia, Elogio,
    Circunstancia, Comportamento,
    PontuacaoBimestral, FichaMedidaDisciplinar, Aluno
    # Se criar futuramente: NMDSequencia, OcorrenciaAluno, etc.
)
from escola.database import get_db  # Deve retornar a session do SQLAlchemy

# --- Sequenciais ---

def get_proximo_rfo_id(incrementar=False):
    db = get_db()
    ano_atual = str(datetime.now().year)
    seq = db.query(RFOSequencia).filter_by(ano=ano_atual).first()
    proximo_numero = seq.numero + 1 if seq else 1
    rfo_id = f"RFO-{proximo_numero:04d}/{ano_atual}"

    if incrementar:
        if seq:
            seq.numero = proximo_numero
        else:
            seq = RFOSequencia(ano=ano_atual, numero=proximo_numero)
            db.add(seq)
        db.commit()
    return rfo_id

def get_proximo_fmd_id(incrementar=False):
    db = get_db()
    ano_atual = str(datetime.now().year)
    seq = db.query(FMDSequencia).filter_by(ano=ano_atual).first()
    proximo_numero = seq.numero + 1 if seq else 1
    fmd_id = f"FMD-{proximo_numero:04d}/{ano_atual}"

    if incrementar:
        if seq:
            seq.numero = proximo_numero
        else:
            seq = FMDSequencia(ano=ano_atual, numero=proximo_numero)
            db.add(seq)
        db.commit()
    return fmd_id

def get_proximo_nmd_id(incrementar=False):
    # Se a classe NMDSequencia não existir, retorna string informativa.
    db = get_db()
    ano_atual = str(datetime.now().year)
    try:
        from escola.models_sqlalchemy import NMDSequencia
    except ImportError:
        return f"NMD-{ano_atual}-ERRO"
    seq = db.query(NMDSequencia).filter_by(ano=ano_atual).first()
    proximo_numero = seq.numero + 1 if seq else 1
    nmd_id = f"NMD-{ano_atual}-{str(proximo_numero).zfill(4)}"
    if incrementar:
        if seq:
            seq.numero = proximo_numero
        else:
            seq = NMDSequencia(ano=ano_atual, numero=proximo_numero)
            db.add(seq)
        db.commit()
    return nmd_id

# --- Listagens ---

def get_tipos_ocorrencia():
    db = get_db()
    return db.query(TipoOcorrencia).order_by(TipoOcorrencia.nome).all()

def get_faltas_disciplinares():
    db = get_db()
    return db.query(FaltaDisciplinar).order_by(FaltaDisciplinar.natureza, FaltaDisciplinar.descricao).all()

def get_elogios():
    db = get_db()
    return db.query(Elogio).order_by(Elogio.tipo, Elogio.descricao).all()

def get_faltas_por_natureza(natureza):
    db = get_db()
    return db.query(FaltaDisciplinar).filter_by(natureza=natureza).order_by(FaltaDisciplinar.id, FaltaDisciplinar.descricao).all()

def get_circunstancias(tipo):
    db = get_db()
    return db.query(Circunstancia).filter_by(tipo=tipo).order_by(Circunstancia.descricao).all()

def get_comportamentos():
    db = get_db()
    return db.query(Comportamento).order_by(Comportamento.pontuacao.desc()).all()

# --- Helpers de Pontuação e Comportamento ---

def _end_of_bimestre(ano, bimestre):
    # Mapa: 1º bimestre final em fevereiro, 2º em abril, 3º em junho, 4º em agosto (default)
    mapping = {1: 2, 2: 4, 3: 6, 4: 8}
    month = mapping.get(int(bimestre), 8)
    last_day = calendar.monthrange(int(ano), month)[1]
    return date(int(ano), month, last_day)

def _infer_comportamento_por_faixa(p):
    try:
        p = float(p)
    except Exception:
        return None
    if p >= 10.0:
        return "Excepcional"
    elif p >= 9.0:
        return "Ótimo"
    elif p >= 7.0:
        return "Bom"
    elif p >= 5.0:
        return "Regular"
    elif p >= 2.0:
        return "Insuficiente"
    else:
        return "Incompatível"

def compute_pontuacao_corrente(aluno_id, as_of=None):
    db = get_db()
    try:
        if as_of is None:
            as_of = datetime.utcnow()
        # 1) último pontuacao_bimestral do aluno
        pb = (db.query(PontuacaoBimestral)
                .filter_by(aluno_id=aluno_id)
                .order_by(PontuacaoBimestral.ano.desc(), PontuacaoBimestral.bimestre.desc())
                .first())
        if pb:
            try:
                base = float(pb.pontuacao_atual)
            except Exception:
                base = 8.0
            cutoff_date = None
            try:
                ae = pb.atualizado_em
                if ae:
                    try:
                        cutoff_date = datetime.fromisoformat(ae)
                    except Exception:
                        try:
                            cutoff_date = datetime.strptime(ae, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            cutoff_date = None
                if cutoff_date is None:
                    end_date = _end_of_bimestre(int(pb.ano), int(pb.bimestre))
                    cutoff_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
            except Exception:
                cutoff_date = None
        else:
            base = 8.0
            cutoff_date = None

        # 2) soma pontos_aplicados FMDs (após cutoff)
        soma_fmd = 0.0
        try:
            q = db.query(func.sum(FichaMedidaDisciplinar.pontos_aplicados))
            q = q.filter(FichaMedidaDisciplinar.aluno_id == aluno_id)
            if cutoff_date:
                q = q.filter(FichaMedidaDisciplinar.data_registro != None)
                q = q.filter(func.datetime(FichaMedidaDisciplinar.data_registro) > cutoff_date)
            r = q.first()
            soma_fmd = float(r[0]) if r and r[0] is not None else 0.0
        except Exception:
            soma_fmd = 0.0

        # 3) bônus - bimestre anterior >= 8.0
        bonus8 = 0.0
        try:
            if pb:
                ano = int(pb.ano)
                b = int(pb.bimestre)
                prev_b, prev_ano = (b-1, ano) if b > 1 else (4, ano-1)
                prev = (db.query(PontuacaoBimestral)
                        .filter_by(aluno_id=aluno_id, ano=str(prev_ano), bimestre=prev_b)
                        .first())
                if prev and prev.pontuacao_atual is not None:
                    if float(prev.pontuacao_atual) >= 8.0:
                        bonus8 = 0.5
        except Exception:
            pass

        # 4) bônus diário após 60 dias sem perda
        bonus9 = 0.0
        try:
            last_loss_row = (db.query(func.max(FichaMedidaDisciplinar.data_registro))
                            .filter(FichaMedidaDisciplinar.aluno_id == aluno_id)
                            .filter(FichaMedidaDisciplinar.pontos_aplicados < 0)
                            .first())
            last_loss = None
            if last_loss_row and last_loss_row[0]:
                try:
                    last_loss = datetime.fromisoformat(last_loss_row[0])
                except Exception:
                    try:
                        last_loss = datetime.strptime(last_loss_row[0], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        last_loss = None
            if last_loss is None:
                aluno = db.query(Aluno).get(aluno_id)
                dm = aluno.data_matricula if aluno else None
                if dm:
                    try:
                        last_loss = datetime.fromisoformat(dm)
                    except Exception:
                        try:
                            last_loss = datetime.strptime(dm, "%Y-%m-%d")
                        except Exception:
                            last_loss = None
            if last_loss:
                grace_end = last_loss + timedelta(days=60)
                if as_of > grace_end:
                    days_eligible = (as_of.date() - grace_end.date()).days
                    if days_eligible > 0:
                        bonus9 = days_eligible * 0.2
        except Exception:
            bonus9 = 0.0

        total = base + soma_fmd + bonus8 + bonus9
        try:
            total = round(float(total), 2)
        except Exception:
            total = float(base)
        total = min(max(total, 0.0), 10.0)

        comportamento = _infer_comportamento_por_faixa(total)

        detalhes = {
            'base': base,
            'soma_fmd': soma_fmd,
            'bonus8': round(bonus8, 2),
            'bonus9': round(bonus9, 2),
            'total_raw': total,
            'cutoff_date': cutoff_date.isoformat() if cutoff_date else None
        }
        return {'pontuacao': total, 'comportamento': comportamento, 'detalhes': detalhes}
    except Exception as ex:
        print(f"[ERRO compute_pontuacao_corrente] {ex}")
        return {'pontuacao': None, 'comportamento': None, 'detalhes': {}}

def get_aluno_estado_atual(aluno_id):
    try:
        res = compute_pontuacao_corrente(aluno_id)
        if res.get('pontuacao') is None:
            db = get_db()
            pb = (db.query(PontuacaoBimestral)
                    .filter_by(aluno_id=aluno_id)
                    .order_by(PontuacaoBimestral.ano.desc(), PontuacaoBimestral.bimestre.desc())
                    .first())
            if pb and pb.pontuacao_atual is not None:
                pontuacao = pb.pontuacao_atual
            else:
                srow = db.query(func.sum(FichaMedidaDisciplinar.pontos_aplicados)).filter_by(aluno_id=aluno_id).first()
                soma_pontos = srow[0] if srow else None
                inicial = 8.0
                if soma_pontos is not None:
                    pontuacao = round(float(inicial) + float(soma_pontos), 2)
                else:
                    pontuacao = round(float(inicial), 2)
            comportamento = _infer_comportamento_por_faixa(pontuacao) if pontuacao is not None else None
            return {'comportamento': comportamento, 'pontuacao': pontuacao}
        return {'comportamento': res.get('comportamento'), 'pontuacao': res.get('pontuacao')}
    except Exception as ex:
        print(f"[ERRO get_aluno_estado_atual] {ex}")
        return {'comportamento': None, 'pontuacao': None}

# --- Migração rápida disciplinar (caso precise criar tabelas extras) ---

def ensure_disciplinar_migrations():
    db = get_db()
    try:
        from escola.models_sqlalchemy import OcorrenciaAluno
        # Criação de tabela OcorrenciaAluno (ocorrencias_alunos - muitos para muitos)
        if not db.engine.dialect.has_table(db.connection(), 'ocorrencias_alunos'):
            OcorrenciaAluno.__table__.create(db.engine)
    except ImportError:
        pass
    # Criação de tabela FMDSequencia se não existir
    if not db.engine.dialect.has_table(db.connection(), 'fmd_sequencia'):
        FMDSequencia.__table__.create(db.engine)
    # Observação: Outras migrações (colunas novas etc.) devem ser feitas via Alembic preferencialmente
    db.commit()

# Sequencial FMD (útil para rotinas que usam o campo 'seq')
def next_fmd_seq_and_year():
    db = get_db()
    ano = datetime.now().year
    seq_obj = db.query(FMDSequencia).filter_by(ano=str(ano)).first()
    if seq_obj and getattr(seq_obj, "seq", None) is not None:
        seq = seq_obj.seq + 1
        seq_obj.seq = seq
    else:
        maxseq = 0
        rows = db.query(FichaMedidaDisciplinar.fmd_id).filter(FichaMedidaDisciplinar.fmd_id.like(f"FMD-%/{ano}")).all()
        import re
        for r in rows:
            fid = r[0] if isinstance(r, (list, tuple)) else getattr(r, "fmd_id", None)
            if fid:
                m = re.match(r'^FMD-(\d{1,})/' + str(ano) + r'$', fid)
                if m:
                    try:
                        n = int(m.group(1))
                        if n > maxseq:
                            maxseq = n
                    except Exception:
                        pass
        seq = maxseq + 1
        seq_obj = FMDSequencia(ano=str(ano), numero=seq, seq=seq)
        db.add(seq_obj)
    db.commit()
    return seq, ano
