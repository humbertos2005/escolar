"""
Helpers para Termos de Adequação de Conduta (TAC)
- get_next_tac_number(db): retorna a próxima string do tipo 'TAC-YYYY-XXXX'
- format_tac_number(year, seq): auxiliar
Uso: importe get_next_tac_number(db) no blueprint que salvará TACs.
"""
from datetime import datetime
import re

def format_tac_number(year: int, seq: int) -> str:
    """Formata TAC-YYYY-XXXX com seq zero-padded 4 dígitos."""
    return f"TAC-{year}-{seq:04d}"

def get_next_tac_number(db) -> str:
    """
    Calcula o próximo número TAC baseado nos registros existentes na tabela tacs.
    - db deve ser o objeto/pool do seu get_db() (conexão sqlite com row factory).
    Retorna string 'TAC-YYYY-XXXX'.
    """
    year = datetime.utcnow().year
    prefix = f"TAC-{year}-"
    try:
        # busca o maior número já criado no ano atual
        row = db.execute("SELECT numero FROM tacs WHERE numero LIKE ? ORDER BY id DESC LIMIT 1", (f"{prefix}%",)).fetchone()
        if row and row.get('numero'):
            # extrair sequência como inteiro
            m = re.search(rf"^{re.escape(prefix)}(\d+)$", row['numero'])
            if m:
                seq = int(m.group(1)) + 1
            else:
                seq = 1
        else:
            seq = 1
    except Exception:
        # fallback simples: contar quantos já existem com prefixo e +1
        try:
            cnt = db.execute("SELECT COUNT(1) as c FROM tacs WHERE numero LIKE ?", (f"{prefix}%",)).fetchone()
            seq = (cnt['c'] if cnt and 'c' in cnt else 0) + 1
        except Exception:
            seq = 1
    return format_tac_number(year, seq)