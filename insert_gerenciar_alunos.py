import shutil, os, sys

path = "templates/dashboard.html"
if not os.path.exists(path):
    print("ERRO: arquivo não encontrado:", path)
    sys.exit(1)

# criar backup
bak = path + ".button.bak"
shutil.copy2(path, bak)
print("Backup criado:", bak)

with open(path, "r", encoding="utf-8") as f:
    txt = f.read()

# já existe o link?
if "alunos_bp.gerenciar_alunos" in txt:
    print("Link 'Gerenciar Alunos' já presente no dashboard; nada a fazer.")
    sys.exit(0)

anchor_html = (
    '    <a href="{{ url_for(\'alunos_bp.gerenciar_alunos\') }}" class="action-btn btn-outline-primary">\n'
    '        <i class="fas fa-users"></i> Gerenciar Alunos\n'
    '    </a>\n'
)

marker = '<div class="quick-actions">'
idx = txt.find(marker)
if idx == -1:
    print("Div 'quick-actions' não encontrada. Não foi inserido o botão.")
    sys.exit(1)

insertion_point = idx + len(marker)
new = txt[:insertion_point] + "\n" + anchor_html + txt[insertion_point:]
with open(path, "w", encoding="utf-8") as f:
    f.write(new)

print("Botão 'Gerenciar Alunos' inserido em templates/dashboard.html")