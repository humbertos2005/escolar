# Sistema Escolar – Documentação Oficial

---

## Sobre

Este sistema é uma plataforma completa e modular para gestão escolar: cadastros, prontuários, pontuações, ocorrências, medidas disciplinares, TACs, atas, relatórios e muito mais.  
O core utiliza **Flask** + **SQLAlchemy ORM**, com arquitetura flexível e possibilidade de alternar facilmente entre múltiplos bancos de dados só editando um arquivo de configuração.

---

## Requisitos

- **Python 3.9 ou superior**
- **pip** (gerenciador de pacotes Python)
- **[Opcional] PostgreSQL ou MySQL** (caso deseje uso em rede)

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
   > O pacote `python-dotenv` já está incluso e permite configuração pelo `.env`.

---

## Escolha do Banco de Dados (Fácil Alternância)

✨ **IMPORTANTE: O sistema pode usar SQLite, PostgreSQL ou MySQL. A escolha exige apenas ajustar o arquivo `.env`; não é preciso editar código!**

### **1. Uso local/simples (padrão, recomendado para escola única):**
- **Não edite nada!**  
- O sistema criará e usará o arquivo `escola.db` na própria pasta, sem necessidade de instalar banco adicional.

**.env padrão:**
```
SQLALCHEMY_DATABASE_URI=sqlite:///escola.db
```

### **2. Uso em rede (recomendado para multi-escolas ou vários acessos concorrentes):**
- **Edite o `.env` e descomente/sobrescreva apenas UMA das opções abaixo conforme o banco desejado:**

**Para PostgreSQL:**
```
SQLALCHEMY_DATABASE_URI=postgresql://usuario:senha@host:porta/nome_do_banco
```

**Para MySQL/MariaDB:**
```
SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:senha@host:porta/nome_do_banco
```

**Exemplo completo de `.env`:**
```ini
# Para SQLite (uso individual ou testes):
SQLALCHEMY_DATABASE_URI=sqlite:///escola.db

# Para produção ou uso em rede (descomente apenas UM):
# SQLALCHEMY_DATABASE_URI=postgresql://usuario:senha@host:porta/nome_do_banco
# SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:senha@host:porta/nome_do_banco

# Outros possíveis: FLASK_SECRET_KEY, SMTP configs, etc
```

**Obs:**  
Se usar PostgreSQL ou MySQL, é necessário que o servidor de banco esteja instalado/funcionando no host ou rede desejada.

---

## Inicialização da Base de Dados

Ao iniciar o sistema **pela primeira vez**:
- O banco (e as tabelas) será criado **automaticamente** pela SQLAlchemy ORM (desde que os modelos estejam atualizados).
- Para atualizar o schema sem perder dados, use **migrations com [Alembic](https://alembic.sqlalchemy.org/)**.

---

## Rodando o Sistema

```sh
python app.py
```
Acesse [http://localhost:5000](http://localhost:5000) no navegador.

- Usuários e rotas aparecem conforme permissões e módulos ativos.
- O dashboard exibe totais dinâmicos das principais entidades.

---
## Empacotamento e Utilitários

- **Empacotamento desktop/Windows:**
  Arquivo `app.spec` incluso para build via PyInstaller:
  ```sh
  pyinstaller app.spec
  ```
- **Scripts administrativos e utilitários:**
  Veja a pasta `scripts/` para tarefas como bonificações, ajustes de bimestre etc.
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
├── .env.example         # Modelo de configuração de ambiente
├── app.spec             # Build do PyInstaller (opcional)
├── scripts/             # Scripts utilitários/admin
├── README.md
└── ...
```

---

## Boas Práticas e Recomendações

- **Nunca faça commit do `.env` real** — distribua apenas o `.env.example`.
- **Ajuste o `.gitignore`** para ignorar bases de dados, arquivos de upload e arquivos sensíveis.
- **Utilize Alembic** para evoluções em tabelas sem perder dados.
- **Mantenha suas dependências atualizadas:**  
  `pip install -U -r requirements.txt`
- **Defina FLASK_SECRET_KEY no `.env` em produção.**
- Ajuste variáveis/credenciais somente pelo `.env` ou ambiente, nunca no Python direto.

---

## Suporte e Colaboração

- Abra **Issues** para bugs ou sugestões.
- **Pull Requests** são bem-vindos!
- Consulte os comentários dos scripts principais para orientação e exemplos.

---

## Licença

(Adicione aqui sua licença, ex: MIT, GPLv3 etc)

---

> Dúvidas? Fale com o mantenedor oficial do projeto ou abra uma issue no GitHub!

---