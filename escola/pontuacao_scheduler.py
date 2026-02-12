from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from scripts.pontuacao_rotinas import executar_rotinas_automaticas

def tarefa_diaria():
    print(f"\n[INFO] Executando rotinas automáticas de pontuação: {datetime.now()}")
    executar_rotinas_automaticas()

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    # Executa todo dia às 23:59
    scheduler.add_job(tarefa_diaria, 'cron', hour=23, minute=59)
    scheduler.start()
    print("[INFO] Agendador iniciado. Rotinas automáticas de pontuação serão executadas diariamente às 23:59.")
    # Mantém o programa rodando
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()