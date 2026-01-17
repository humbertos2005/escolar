from datetime import datetime

def formatar_data_br(data_str):
    """
    Converte data de diversos formatos para o padrão brasileiro DD/MM/YYYY
    """
    if not data_str:
        return '-'
    
    try:
        # Tentar vários formatos de entrada
        formatos = [
            '%Y-%m-%d',           # 2025-01-24
            '%Y-%m-%d %H:%M:%S',  # 2025-01-24 14:30:00
            '%d/%m/%Y',           # 24/01/2025
            '%m/%d/%Y',           # 01/24/2025 (americano)
        ]
        
        for formato in formatos:
            try:
                data_obj = datetime.strptime(str(data_str).strip(), formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue
        
        # Se nenhum formato funcionou, retorna o valor original
        return data_str
    except:
        return data_str


def formatar_datetime_br(data_str):
    """
    Converte data/hora para o padrão brasileiro DD/MM/YYYY às HH:MM
    """
    if not data_str:
        return '-'
    
    try:
        formatos = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]
        
        for formato in formatos:
            try:
                data_obj = datetime.strptime(str(data_str).strip(), formato)
                return data_obj.strftime('%d/%m/%Y às %H:%M')
            except ValueError:
                continue
        
        return data_str
    except:
        return data_str


def data_hora_atual_br():
    """
    Retorna a data e hora atual no formato brasileiro
    """
    return datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
