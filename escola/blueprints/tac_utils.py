"""
Helpers para Termos de Adequação de Conduta (TAC)
- get_next_tac_number(db): retorna a próxima string do tipo 'TAC-YYYY-XXXX'
- format_tac_number(year, seq): auxiliar
Uso: importe get_next_tac_number(db) no blueprint que salvará TACs.
Agora 100% compatível com SQLAlchemy ORM.
"""
from datetime import datetime
import re
from escola.models_sqlalchemy import TAC

def format_tac_number(year: int, seq: int) -> str:
    """Formata TAC-YYYY-XXXX com seq zero-padded 4 dígitos."""
    return f"TAC-{year}-{seq:04d}"

def get_next_tac_number(db) -> str:
    """
    Calcula o próximo número TAC baseado nos registros existentes na tabela TAC (ORM).
    - db deve ser a session SQLAlchemy.
    Retorna string 'TAC-YYYY-XXXX'.
    """
    year = datetime.utcnow().year
    prefix = f"TAC-{year}-"
    try:
        # Busca o TAC mais recente para o ano
        tac = (
            db.query(TAC)
            .filter(TAC.numero.like(f"{prefix}%"))
            .order_by(TAC.id.desc())
            .first()
        )
        if tac and tac.numero:
            m = re.search(rf"^{re.escape(prefix)}(\d+)$", tac.numero)
            if m:
                seq = int(m.group(1)) + 1
            else:
                seq = 1
        else:
            seq = 1
    except Exception:
        # fallback simples: contar quantos já existem com prefixo e +1
        try:
            cnt = (
                db.query(TAC)
                .filter(TAC.numero.like(f"{prefix}%"))
                .count()
            )
            seq = cnt + 1
        except Exception:
            seq = 1
    return format_tac_number(year, seq)