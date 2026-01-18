# Sistema Escolar – Documentação Oficial

---

## Sobre

Este sistema é uma plataforma completa e modular para gestão escolar: cadastros, prontuários, pontuações, ocorrências, medidas disciplinares, TACs, atas, relatórios e muito mais.  
O core utiliza **Flask** + **SQLAlchemy ORM**, com arquitetura flexível e possibilidade de alternar facilmente entre múltiplos bancos de dados só editando um arquivo de configuração.

---

## Requisitos

- **Python 3.9 ou superior**
- **pip** (gerenciador de pacotes Python)
- **[Opcional] PostgreSQL ou MySQL** (recomendado para uso em rede ou produção)
- Para uso local/testes, **NÃO é necessário instalar banco**: o sistema utiliza SQLite automaticamente.

---

## Tutorial de Instalação de Banco de Dados Externo (PostgreSQL / MySQL)

### ⚠️ **IMPORTANTE:**  
Para uso em produção ou ambiente multiusuário/rede, é necessário instalar e configurar um servidor de banco de dados PostgreSQL ou MySQL/MariaDB.  
Para uso individual/local, não é necessário instalar banco — basta usar o padrão SQLite.

---

### ● **Instalando o PostgreSQL (Servidor Local ou em Rede)**

1. **Baixe o instalador oficial:**  
   [Download Oficial PostgreSQL](https://www.postgresql.org/download/)

2. **Execute o instalador:**  
   - Siga as instruções na tela.
   - Guarde a senha do usuário `postgres` definida na instalação.
   - Deixe a porta padrão (5432) se não tiver outra preferência.

3. **(Opcional) Instale ferramentas auxiliares:**  
   - **pgAdmin:** ferramenta gráfica para administrar o banco:  
     [Download pgAdmin](https://www.pgadmin.org/download/)

4. **Crie usuário e banco para o sistema escolar:**  
   - Abra o **SQL Shell (psql)** (procure no menu iniciar).
   - Pressione Enter para host, database e porta.
   - Quando pedir “Username [postgres]:”, pressione Enter.
   - Digite a senha definida na instalação.
   - Digite os comandos abaixo (um de cada vez):
     ```sql
     CREATE USER meuapp WITH PASSWORD 'minhasenha';
     CREATE DATABASE escolar OWNER meuapp;
     GRANT ALL PRIVILEGES ON DATABASE escolar TO meuapp;
     ```
     *(Troque `meuapp`, `minhasenha`, `escolar` conforme desejar.)*

5. **Configure o arquivo `.env`:**
   ```ini
   SQLALCHEMY_DATABASE_URI=postgresql://meuapp:minhasenha@localhost:5432/escolar
   ```
   *(Preencha com os dados usados na etapa anterior.)*

---

### ● **Instalando o MySQL/MariaDB**

1. **Baixe o instalador oficial:**  
   [Download Oficial MySQL](https://dev.mysql.com/downloads/installer/)

2. **Execute o instalador e siga os passos na tela**
   - Crie um usuário e um banco específico para o sistema escolar.

3. **Exemplo de configuração no arquivo `.env`:**
   ```ini
   SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:senha@localhost:3306/nome_do_banco
   ```

---

### ● **Uso Local/Simplificado (SQLite)**
- **Não requer instalação extra!**
- O sistema cria e utiliza o arquivo `escola.db` automaticamente:
  ```ini
  SQLALCHEMY_DATABASE_URI=sqlite:///escola.db
  ```
- **Ideal para testes ou para escola única com uso individual.**

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

## Escolha do Banco de Dados

✨ **IMPORTANTE:**  
O sistema pode usar **SQLite**, **PostgreSQL** ou **MySQL/MariaDB**. A escolha exige apenas ajustar o arquivo `.env`; não é preciso editar código!

### **Como configurar o banco (.env):**

#### *Exemplo para SQLite (local/individual, padrão):*
```ini
SQLALCHEMY_DATABASE_URI=sqlite:///escola.db
```

#### *Exemplo para PostgreSQL (produção/rede):*
```ini
SQLALCHEMY_DATABASE_URI=postgresql://meuapp:minhasenha@localhost:5432/escolar
```

#### *Exemplo para MySQL/MariaDB:*
```ini
SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:senha@localhost:3306/nome_do_banco
```

**Obs.:**  
O servidor PostgreSQL ou MySQL precisa estar instalado e funcionando no computador/servidor que armazenará os dados.

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

## Observações Importantes — Banco de Dados

- Para uso local ou escola pequena, **basta SQLite** (não precisa instalar nada extra).
- Para redes escolares, multiusuários ou produção profissional, **PostgreSQL ou MySQL/MariaDB devem ser instalados no servidor antes de rodar o sistema**.
- Usuário e base do banco externo devem ser criados pelo administrador, conforme os tutoriais acima.

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