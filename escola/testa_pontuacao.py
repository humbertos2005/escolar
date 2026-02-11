from app import app
from database import get_db
from services.escolar_helper import _apply_delta_pontuacao

with app.app_context():
    db = get_db()
    _apply_delta_pontuacao(
        db, 540, '2025-02-03', 0,
        ocorrencia_id=None,
        tipo_evento="INICIO_ANO",
        data_despacho='2025-02-03'
    )
    print("Pontuação inicial lançada (se não houver erro).")