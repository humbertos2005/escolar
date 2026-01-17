# Sistema Escolar – Documentação Oficial

---

## Sobre

Este sistema é uma plataforma completa e modular para gestão e acompanhamento escolar, incluindo cadastros, prontuários, pontuações, ocorrências, medidas disciplinares, TACs, atas, relatórios e muito mais.  
O core utiliza **Flask** + **SQLAlchemy ORM**, com arquitetura extensível, suporte a múltiplos bancos de dados e configuração 100% dinâmica via variáveis de ambiente.

---

## Requisitos

- **Python 3.9 ou superior**
- **pip** (gerenciador de pacotes Python)
- **[Opcional] PostgreSQL ou MySQL** (caso não use SQLite)

---

## Instalação do Projeto

1. **Clone o repositório:**
   ```sh
   git clone <URL_DO_REPOSITORIO>
   cd <PASTA_DO_PROJETO>
   ```

2. **Crie o ambiente virtual (recomendado):**
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. **Instale as dependências:**
   ```sh
   pip install -r requirements.txt
   ```
   > Certifique-se de que o pacote `python-dotenv` está incluso, pois ele carrega automaticamente as variáveis do arquivo `.env` em desenvolvimento.

---

## Configuração do Banco de Dados

O sistema aceita **SQLite (padrão)**, **PostgreSQL** ou **MySQL** — basta definir uma variável de ambiente ou configurar o arquivo `.env`. Nenhuma alteração de código é necessária.

### 1. Usando SQLite (padrão)

> O sistema funcionará de imediato via SQLite, usando o arquivo `escola.db` local.

Configure em `.env`:
```
DATABASE_FILE=escola.db
```
(ou outro caminho/nome conforme desejar)

### 2. Usando PostgreSQL ou MySQL/MariaDB

Defina em `.env` (ou nas variáveis de ambiente no servidor):

Para PostgreSQL:
```
DATABASE_URL=postgresql://usuario:senha@host:porta/nome_do_banco
```
Para MySQL/MariaDB:
```
DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/nome_do_banco
```
Se `DATABASE_URL` estiver definido, **ele tem prioridade sobre** `DATABASE_FILE`.

### 3. Exemplo Básico de `.env`

```ini
# Para desenvolvimento local com SQLite
DATABASE_FILE=escola.db

# Para produção com Postgres ou MySQL (descomente apenas um)
# DATABASE_URL=postgresql://usuario:senha@host:porta/nome_do_banco
# DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/nome_do_banco

# Outros possíveis: FLASK_SECRET_KEY, SMTP configs, etc
```

> Por segurança, nunca faça commit do seu `.env` real — use o `.gitignore`.

---

## Inicialização da Base de Dados

Ao iniciar o sistema pela primeira vez:
- O banco (e as tabelas) será criado automaticamente via SQLAlchemy ORM, **desde que** os modelos estejam atualizados.
- Para schema avançado, recomenda-se uso de **migrations com [Alembic](https://alembic.sqlalchemy.org/)**.  
  > Consulte a documentação/README de migrations para atualizar estrutura de produção.

---
## Rodando o Sistema

```sh
python app.py
```
Acesse [http://localhost:5000](http://localhost:5000) no navegador.

- Usuários e rotas são exibidos conforme permissões e módulos; veja a barra de navegação.
- O dashboard central fornece totalizadores dinâmicos.

### Ferramentas Extras

- **Empacotamento desktop/Windows:**  
  Arquivo `app.spec` incluso para build via PyInstaller:
  ```sh
  pyinstaller app.spec
  ```
- **Scripts administrativos e utilitários:**  
  Consulte a pasta `scripts/` para rotinas como bonificações de pontuação, ajustes de bimestre, etc.
  ```sh
  python scripts/pontuacao_rotinas.py --help
  ```

---

## Estrutura do Projeto

```
├── app.py               # Aplicação principal Flask
├── database.py          # Configurações SQLAlchemy (engine, session, helpers)
├── models_sqlalchemy.py # Models ORM
├── blueprints/          # Blueprints Flask (modularização de rotas e lógica)
├── templates/           # Templates HTML (Jinja2)
├── static/              # Arquivos estáticos (CSS, JS, imagens...)
├── requirements.txt
├── .env.example         # Exemplo de configuração de ambiente
├── app.spec             # Build do PyInstaller (opcional)
├── scripts/             # Scripts utilitários/admin
├── README.md
└── ...
```

---

## Dicas de Produção e Boas Práticas

- **Nunca use `.env` real no repositório — distribua apenas `.env.example`.**
- **Ajuste o `.gitignore`** para ignorar toda base de dados real, uploads de usuários e arquivos sensíveis.
- **Utilize Alembic** para evoluir/migrar tabelas sem perder dados já inseridos.
- **Mantenha bibliotecas atualizadas** (`pip install -U -r requirements.txt`)
- **Defina e proteja o FLASK_SECRET_KEY em ambiente de produção!**
- Altere variáveis e credenciais apenas via ambiente ou `.env`, sem codificar valores sensíveis nos arquivos Python.

---

## Colaboração, Suporte e Contribuição

- Abra **Issues** para reportar bugs ou sugerir melhorias.
- Contribuições por **Pull Requests** são bem-vindas!
- Mantenha sempre dados sensíveis e de produção fora dos commits.
- Consulte os comentários dos principais scripts e módulos para orientação.

---

## Licença

(Cole sua licença aqui, ex: MIT, GPLv3 etc)

---

> Para dúvidas, entre em contato com o mantenedor oficial do projeto ou abra uma issue!

---