# services/escolar_helper.py

from datetime import datetime, timedelta, date
import calendar
from sqlalchemy.orm import Session
from sqlalchemy import func
from models_sqlalchemy import (
    RFOSequencia, FMDSequencia,
    FaltaDisciplinar, TipoOcorrencia, Elogio,
    Circunstancia, Comportamento,
    PontuacaoBimestral, FichaMedidaDisciplinar, Aluno,
    TabelaDisciplinarConfig, Bimestre,
    # Se criar futuramente: NMDSequencia, OcorrenciaAluno, etc.
)
from database import get_db  # Deve retornar a session do SQLAlchemy
from unidecode import unidecode
import re
from flask import current_app

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
        from models_sqlalchemy import NMDSequencia
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
        from models_sqlalchemy import OcorrenciaAluno
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

def compute_pontuacao_em_data(aluno_id, data_referencia):
    """
    Retorna a pontuação e o comportamento do aluno NA DATA informada.
    - aluno_id: ID do aluno
    - data_referencia: data (string: 'YYYY-MM-DD') ou datetime
    INCLUI CÁLCULO DE BÔNUS (60 dias sem ocorrências)
    """
    from datetime import datetime, timedelta
    db = get_db()
    try:
        # Garante formato correto de data
        if isinstance(data_referencia, str):
            try:
                data_ref = datetime.fromisoformat(data_referencia)
            except Exception:
                try:
                    data_ref = datetime.strptime(data_referencia, '%Y-%m-%d')
                except Exception:
                    data_ref = datetime.now()
        elif isinstance(data_referencia, datetime):
            data_ref = data_referencia
        else:
            data_ref = datetime.now()

        # Começa com 8.0 pontos (regra do sistema)
        pontuacao = 8.0

        # Busca todos os lançamentos históricos até a data
        from models_sqlalchemy import PontuacaoHistorico

        def string_to_date(s):
            try:
                return datetime.strptime(s, '%d/%m/%Y').date()
            except Exception:
                try:
                    return datetime.strptime(s, '%Y-%m-%d').date()
                except Exception:
                    return None

        historico = [
            h for h in db.query(PontuacaoHistorico).filter(
                PontuacaoHistorico.aluno_id == aluno_id
            ).all()
            if string_to_date(h.criado_em) and string_to_date(h.criado_em) <= data_ref.date()
        ]

        # Aplica todos os deltas (somas e subtrações)
        for h in historico:
            try:
                pontuacao += float(h.valor_delta)
            except Exception:
                continue

        # BÔNUS: 60 dias sem ocorrências = +0.2 por dia após o período de graça
        bonus_tempo = 0.0
        print(f"DEBUG INÍCIO CÁLCULO BÔNUS - aluno_id={aluno_id}")
        try:
            # Busca a última ocorrência COM perda (delta negativo)
            historico_perdas = [
                h for h in db.query(PontuacaoHistorico).filter(
                    PontuacaoHistorico.aluno_id == aluno_id,
                    PontuacaoHistorico.valor_delta < 0
                ).all()
                if string_to_date(h.criado_em) and string_to_date(h.criado_em) < data_ref.date()
            ]
            
            print(f"DEBUG - Histórico de perdas encontrado: {len(historico_perdas)} registros")
            
            if historico_perdas:
                # Última perda
                ultima_perda_date = max([string_to_date(h.criado_em) for h in historico_perdas])
                print(f"DEBUG - Última perda em: {ultima_perda_date}")
            else:
                # Se não tem perdas, usa a data de matrícula do aluno
                print(f"DEBUG - Nenhuma perda encontrada, buscando data de matrícula...")
                aluno = db.query(Aluno).get(aluno_id)
                dm = aluno.data_matricula if aluno else None
                print(f"DEBUG - Data de matrícula: {dm}")
                if dm:
                    try:
                        ultima_perda_date = datetime.strptime(dm, '%Y-%m-%d').date()
                        print(f"DEBUG - Data de matrícula convertida: {ultima_perda_date}")
                    except Exception as ex:
                        print(f"DEBUG - ERRO ao converter data de matrícula: {ex}")
                        ultima_perda_date = None
                else:
                    ultima_perda_date = None
            
            if ultima_perda_date:
                # Calcula dias desde a última perda até a data de referência
                dias_sem_perda = (data_ref.date() - ultima_perda_date).days
                print(f"DEBUG - Dias sem perda: {dias_sem_perda}")
                
                # Aplica bônus SOMENTE após 60 dias de graça
                if dias_sem_perda > 60:
                    dias_bonus = dias_sem_perda - 60
                    bonus_tempo = dias_bonus * 0.2
                    print(f"DEBUG BÔNUS APLICADO: {dias_sem_perda} dias sem perda, {dias_bonus} dias de bônus = +{bonus_tempo}")
                else:
                    print(f"DEBUG - Ainda no período de graça (60 dias)")
            else:
                print(f"DEBUG - Não foi possível determinar data base para bônus")
        except Exception as ex:
            print(f"[ERRO ao calcular bônus de tempo] {ex}")
            import traceback
            traceback.print_exc()
            bonus_tempo = 0.0
        try:
            # Busca a última ocorrência COM perda (delta negativo)
            historico_perdas = [
                h for h in db.query(PontuacaoHistorico).filter(
                    PontuacaoHistorico.aluno_id == aluno_id,
                    PontuacaoHistorico.valor_delta < 0
                ).all()
                if string_to_date(h.criado_em) and string_to_date(h.criado_em) <= data_ref.date()
            ]
            
            if historico_perdas:
                # Última perda
                ultima_perda_date = max([string_to_date(h.criado_em) for h in historico_perdas])
            else:
                # Se não tem perdas, usa a data de matrícula do aluno
                aluno = db.query(Aluno).get(aluno_id)
                dm = aluno.data_matricula if aluno else None
                if dm:
                    try:
                        ultima_perda_date = datetime.strptime(dm, '%Y-%m-%d').date()
                    except Exception:
                        ultima_perda_date = None
                else:
                    ultima_perda_date = None
            
            if ultima_perda_date:
                # Calcula dias desde a última perda até a data de referência
                dias_sem_perda = (data_ref.date() - ultima_perda_date).days
                
                # Aplica bônus SOMENTE após 60 dias de graça
                if dias_sem_perda > 60:
                    dias_bonus = dias_sem_perda - 60
                    bonus_tempo = dias_bonus * 0.2
                    print(f"DEBUG BÔNUS: {dias_sem_perda} dias sem perda, {dias_bonus} dias de bônus = +{bonus_tempo}")
        except Exception as ex:
            print(f"[ERRO ao calcular bônus de tempo] {ex}")
            bonus_tempo = 0.0

        # Soma o bônus
        pontuacao += bonus_tempo

        # Limites conforme regras do sistema
        pontuacao = max(0.0, min(10.0, pontuacao))

        # Descobre comportamento correspondente
        comportamento = _infer_comportamento_por_faixa(pontuacao)

        return {'pontuacao': round(pontuacao, 2), 'comportamento': comportamento}
    except Exception as ex:
        print(f"[ERRO compute_pontuacao_em_data] {ex}")
        return {'pontuacao': None, 'comportamento': None}
    
def _calcular_delta_por_medida(medida_aplicada, qtd, config):
    """
    Calcula o delta (positivo/negativo) aplicável à pontuação a partir do texto da medida e quantidade.
    Aceita variações como advertencia oral, advertência oral, adv oral, advert oral, etc.
    Também faz print dos valores de depuração.
    """
    if not medida_aplicada:
        print("DEBUG - medida_aplicada vazia.")
        return 0.0

    # Remove acentos, coloca maiúsculo e remove espaços duplicados
    m = unidecode(str(medida_aplicada)).upper().replace("  ", " ").strip()
    try:
        qtd = float(qtd or 1)
    except Exception:
        qtd = 1.0

    # Formas mais comuns de cada medida
    if 'ADVERTENCIA ORAL' in m or 'ADV ORAL' in m or ('ORAL' in m and 'ADVERT' in m):
        delta = qtd * float(config.get('advertencia_oral', -0.1))
        print("DEBUG - delta calculado para ADVERTÊNCIA ORAL:", delta)
        return delta
    if 'ADVERTENCIA ESCRITA' in m or 'ADV ESCRITA' in m or ('ESCRITA' in m and 'ADVERT' in m):
        delta = qtd * float(config.get('advertencia_escrita', -0.3))
        print("DEBUG - delta calculado para ADVERTÊNCIA ESCRITA:", delta)
        return delta
    if 'SUSPENS' in m or 'SUSPENSAO' in m:
        nums = re.findall(r'(\d+)', m)
        dias = int(nums[0]) if nums else int(qtd)
        delta = dias * float(config.get('suspensao_dia', -0.5))
        print("DEBUG - delta calculado para SUSPENSÃO:", delta)
        return delta
    if 'ACAO EDUCATIVA' in m or 'ACAO EDUCATIVA' in m or 'EDUCATIVA' in m:
        nums = re.findall(r'(\d+)', m)
        dias = int(nums[0]) if nums else int(qtd)
        delta = dias * float(config.get('acao_educativa_dia', -1.0))
        print("DEBUG - delta calculado para AÇÃO EDUCATIVA:", delta)
        return delta
    if 'ELOGIO' in m:
        delta = qtd * float(config.get('elogio_individual', 0.5))
        print("DEBUG - delta calculado para ELOGIO:", delta)
        return delta

    print("DEBUG - Nenhum caso identificado. Retornando delta 0.0")
    return 0.0

def _get_config_values(db):
    """Lê tabela_disciplinar_config e retorna dict de valores (ORM; fallback defaults se ausente)."""
    defaults = {
        'advertencia_oral': -0.1,
        'advertencia_escrita': -0.3,
        'suspensao_dia': -0.5,
        'acao_educativa_dia': -1.0,
        'elogio_individual': 0.5,
        'elogio_coletivo': 0.3
    }
    try:
        rows = db.query(TabelaDisciplinarConfig).all()
        for r in rows:
            defaults[getattr(r, 'chave')] = float(getattr(r, 'valor'))
    except Exception:
        pass
    return defaults

def _get_bimestre_for_date(db, data_str):
    """
    Determina (ano_int, bimestre_int) consultando a tabela 'bimestres' com SQLAlchemy.
    Se não encontrar ou erro, faz fallback para 4 bimestres por ano.
    """
    try:
        d = datetime.strptime(data_str[:10], '%Y-%m-%d').date()
    except Exception:
        d = date.today()
    ano = d.year
    try:
        rows = db.query(Bimestre).filter_by(ano=ano).order_by(Bimestre.numero).all()
        if rows:
            for r in rows:
                num = int(getattr(r, 'numero')) if getattr(r, 'numero') is not None else None
                inicio = getattr(r, 'inicio')
                fim = getattr(r, 'fim')
                try:
                    inicio_date = datetime.strptime(str(inicio)[:10], '%Y-%m-%d').date() if inicio else None
                except Exception:
                    inicio_date = None
                try:
                    fim_date = datetime.strptime(str(fim)[:10], '%Y-%m-%d').date() if fim else None
                except Exception:
                    fim_date = None
                if (inicio_date is None or inicio_date <= d) and (fim_date is None or fim_date >= d):
                    if num is not None:
                        return ano, num
    except Exception:
        try:
            current_app.logger.debug("Erro ao consultar tabela bimestres; usando fallback.")
        except Exception:
            pass
    b = ((d.month - 1) // 3) + 1
    return ano, b

def _apply_delta_pontuacao(db, aluno_id, data_tratamento_str, delta, ocorrencia_id=None, tipo_evento=None, data_despacho=None):
    """
    Aplica delta na pontuacao_bimestral do aluno (cria linha se inexistente).
    Garante limites mínimos/máximos (0.0 .. 10.0).
    Registra no pontuacao_historico usando DD/MM/AAAA (sem horas).
    """
    if not aluno_id:
        return

    from datetime import datetime
    ano, bimestre = _get_bimestre_for_date(db, data_tratamento_str)
    from models_sqlalchemy import PontuacaoBimestral, PontuacaoHistorico

    # Formata a data para DD/MM/AAAA
    criado_em = None
    if data_despacho:
        # Se vier YYYY-MM-DD, converte para DD/MM/AAAA
        if '-' in data_despacho and len(data_despacho) >= 10:
            criado_em = datetime.strptime(data_despacho[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        elif '/' in data_despacho and len(data_despacho) >= 10:
            criado_em = data_despacho[:10]
        else:
            criado_em = datetime.now().strftime('%d/%m/%Y')
    else:
        criado_em = datetime.now().strftime('%d/%m/%Y')

    try:
        print(f"DEBUG _apply_delta_pontuacao: aluno_id={aluno_id}, delta={delta}, criado_em={criado_em}")
        row = db.query(PontuacaoBimestral).filter_by(aluno_id=aluno_id, ano=ano, bimestre=bimestre).first()
        if row:
            atual = float(row.pontuacao_atual)
            novo = max(0.0, min(10.0, atual + float(delta)))
            row.pontuacao_atual = novo
            row.atualizado_em = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            inicial = 8.0
            novo = max(0.0, min(10.0, inicial + float(delta)))
            row = PontuacaoBimestral(
                aluno_id=aluno_id,
                ano=ano,
                bimestre=bimestre,
                pontuacao_inicial=inicial,
                pontuacao_atual=novo,
                atualizado_em=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            db.add(row)

        hist = PontuacaoHistorico(
            aluno_id=aluno_id,
            ano=ano,
            bimestre=bimestre,
            ocorrencia_id=ocorrencia_id,
            tipo_evento=tipo_evento,
            valor_delta=float(delta),
            criado_em=criado_em
        )
        db.add(hist)
        db.commit()
    except Exception:
        print("EXCEPTION _apply_delta_pontuacao:", aluno_id, delta, criado_em)
        current_app.logger.exception('Erro ao aplicar delta pontuacao (possível tabela ausente).')
        db.rollback()
