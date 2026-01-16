# Sistema Escolar - Documentação

## Sobre

Este sistema permite gestão de banco de dados escolar com flexibilidade para diferentes ambientes e tipos de bancos de dados, adaptando-se facilmente via variáveis de ambiente – sem necessidade de alteração do código-fonte.

Conta agora com arquitetura orientada ao ORM SQLAlchemy, trazendo portabilidade, escalabilidade e manutenção facilitada dos modelos de dados.

---

## Instalação

1. **Clone o repositório:**

   ```sh
   git clone <URL_DO_REPOSITORIO>
   cd <PASTA_DO_PROJETO>
   ```

2. **Instale as dependências do projeto (inclui o python-dotenv):**

   ```sh
   pip install -r requirements.txt
   ```

---

## Configuração do Banco de Dados

O sistema pode utilizar tanto SQLite (padrão) quanto bancos compatíveis com SQLAlchemy (PostgreSQL, MySQL) — basta configurar as variáveis de ambiente.

### 1. Usando SQLite (padrão)

Por padrão, o sistema opera sobre SQLite utilizando o arquivo `escola.db`.  
Para alterar o nome ou local do arquivo, defina a variável:

```sh
export DATABASE_FILE=/caminho/para/seu/arquivo.db
```

### 2. Usando PostgreSQL ou MySQL (SQLAlchemy)

Para usar um banco externo via SQLAlchemy:

```sh
export DATABASE_URL="postgresql://usuario:senha@host:porta/nome_do_banco"
# ou
export DATABASE_URL="mysql+pymysql://usuario:senha@host:porta/nome_do_banco"
```

Se a variável `DATABASE_URL` não estiver presente, o sistema utiliza SQLite automaticamente.

Você pode definir essas variáveis manualmente (linha de comando, painel de hospedagem, etc.) ou via arquivo `.env` (recomendado).

---

## Configuração de variáveis de ambiente via arquivo `.env`

1. **Copie o arquivo de exemplo:**

   ```sh
   cp .env.example .env
   ```

2. **Edite o arquivo `.env`**

   - Para SQLite, mantenha ou altere somente a linha `DATABASE_FILE`.
   - Para PostgreSQL ou MySQL, preencha a variável `DATABASE_URL` e comente/remova a linha `DATABASE_FILE`.

3. **Pronto!**  
   O sistema utilizará as variáveis do `.env` automaticamente **se você tiver python-dotenv instalado**.

> **Dica:** o arquivo `.env.example` é apenas um modelo. Por segurança, não envie o arquivo `.env` ao GitHub (adicione `.env` ao seu `.gitignore`).

---

## Variáveis suportadas

- **`DATABASE_FILE`**: Caminho/nome do arquivo SQLite (padrão: escola.db)
- **`DATABASE_URL`**: String de conexão para bancos via SQLAlchemy (PostgreSQL ou MySQL)

O sistema lê essas variáveis automaticamente graças ao pacote `python-dotenv`.

---

## Modelos de Dados: SQLAlchemy & Migração

A estrutura atual do sistema foi migrada para usar o SQLAlchemy como ORM principal.

### Status dos arquivos de modelo:
| Arquivo                 | Status        | Observação                                                                 |
|-------------------------|--------------|----------------------------------------------------------------------------|
| `models.py`             | 🚫 LEGADO    | **Não usar!** Apenas referência histórica do SQLite antigo.                |
| `models_sqlalchemy.py`  | ✅ ATUAL      | Use SEMPRE. ORM oficial, todas as definições e acesso via SQLAlchemy.      |

### Orientações:

- **Não escreva mais funções ou modelos em `models.py`.**
- Qualquer novo acesso a dados, modelo de tabela, consulta ou helper deve ser feito usando as classes do `models_sqlalchemy.py`.
- **Se precisar migrar alguma lógica de negócio ou cálculo do legado, consulte apenas o código do `models.py` para referência** e implemente a versão SQLAlchemy.
- Quando toda lógica relevante do arquivo legado estiver portada, `models.py` poderá ser arquivado ou removido futuramente.

---

## Uso

Com as dependências instaladas e o `.env` configurado, basta rodar o projeto com:

```sh
python app.py
```

Ou rode testes/conexões específicas pelos scripts utilitários, conforme a estrutura do seu projeto.

---

## Dicas adicionais

- Para alterar bancos de dados, basta ajustar ou trocar seu `.env`, sem mexer nos arquivos Python.
- Em ambientes de produção, configure as variáveis de ambiente diretamente no painel do serviço (Heroku, PythonAnywhere, etc).
- Consulte o arquivo `.env.example` para os exemplos de configuração.

---

## Manutenção e Colaboração

- Abra issues para relatar bugs ou sugerir melhorias.
- Pull requests são bem-vindos! Sempre mantenha variáveis sensíveis fora do código-fonte e do repositório.

---