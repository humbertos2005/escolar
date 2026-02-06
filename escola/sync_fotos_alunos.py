"""
Script para sincronizar fotos de alunos.
Atualiza o campo 'photo' no banco de dados com base nos arquivos existentes em static/uploads/alunos/
"""
import os
import sys
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Ajusta o path para importar módulos do projeto
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from database import get_db
from models_sqlalchemy import Aluno

def sync_fotos():
    """
    Sincroniza fotos de alunos:
    - Lista arquivos em static/uploads/alunos/
    - Extrai matrícula do nome do arquivo (formato: MATRICULA_nome.ext)
    - Atualiza campo photo no banco de dados
    """
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads', 'alunos')
    
    if not os.path.exists(uploads_dir):
        print(f"❌ Pasta não encontrada: {uploads_dir}")
        return
    
    print(f"📂 Verificando arquivos em: {uploads_dir}\n")
    
    # Lista todos os arquivos de imagem
    extensoes_validas = ('.jpg', '.jpeg', '.png', '.gif')
    arquivos = [f for f in os.listdir(uploads_dir) if f.lower().endswith(extensoes_validas)]
    
    print(f"📊 Total de arquivos encontrados: {len(arquivos)}\n")
    
    if not arquivos:
        print("⚠️  Nenhum arquivo de imagem encontrado.")
        return
    
    with app.app_context():
        db = get_db()
        
        atualizados = 0
        nao_encontrados = 0
        ja_preenchidos = 0
        
        for filename in arquivos:
            # Extrai matrícula (parte antes do primeiro underscore)
            partes = filename.split('_')
            if not partes:
                print(f"⚠️  Formato inválido: {filename}")
                continue
            
            matricula_candidata = partes[0]
            
            # Busca aluno por matrícula
            aluno = db.query(Aluno).filter_by(matricula=matricula_candidata).first()
            
            if not aluno:
                print(f"⚠️  Aluno não encontrado: {filename} (matrícula: {matricula_candidata})")
                nao_encontrados += 1
                continue
            
            # Verifica se já tem foto cadastrada
            if aluno.photo and aluno.photo.strip():
                # Só atualiza se for diferente
                if aluno.photo != filename:
                    print(f"🔄 Atualizando: {aluno.nome} ({matricula_candidata})")
                    print(f"   Anterior: {aluno.photo}")
                    print(f"   Nova: {filename}")
                    aluno.photo = filename
                    atualizados += 1
                else:
                    ja_preenchidos += 1
            else:
                print(f"✅ Cadastrando: {aluno.nome} ({matricula_candidata}) → {filename}")
                aluno.photo = filename
                atualizados += 1
        
        if atualizados > 0:
            try:
                db.commit()
                print(f"\n✅ {atualizados} registro(s) atualizado(s) com sucesso!")
            except Exception as e:
                db.rollback()
                print(f"\n❌ Erro ao salvar: {e}")
        else:
            print(f"\n✅ Nenhuma atualização necessária.")
        
        print(f"\n📊 RESUMO:")
        print(f"   - Atualizados: {atualizados}")
        print(f"   - Já preenchidos: {ja_preenchidos}")
        print(f"   - Não encontrados: {nao_encontrados}")
        print(f"   - Total processado: {len(arquivos)}")

if __name__ == '__main__':
    print("=" * 60)
    print("🔄 SINCRONIZAÇÃO DE FOTOS DE ALUNOS")
    print("=" * 60)
    sync_fotos()
    print("=" * 60)