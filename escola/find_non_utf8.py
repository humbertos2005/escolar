import os

def is_utf8(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False

problem_files = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            fullpath = os.path.join(root, file)
            if not is_utf8(fullpath):
                problem_files.append(fullpath)

print("Arquivos .py não UTF-8 encontrados:")
for f in problem_files:
    print(f)

if not problem_files:
    print("Todos os arquivos .py estão em UTF-8!")