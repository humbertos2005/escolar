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

# Guia de Implementação - Transferência Automática de Saldo entre Bimestres

## 📋 Resumo da Solução

Foi criada a função `transferir_saldo_entre_bimestres()` que automatiza a continuidade de pontuação disciplinar entre bimestres, eliminando a necessidade de intervenção manual.

---

## 🎯 O que a função faz

1. **Calcula o saldo final** de cada aluno no bimestre de origem usando `PontuacaoHistorico`
2. **Transfere automaticamente** esse saldo como pontuação inicial do próximo bimestre
3. **Registra no histórico** como evento `TRANSFERENCIA_BIMESTRE` para auditoria
4. **Respeita o teto de 10.0** - alunos com saldo superior ficam em 10.0
5. **Evita duplicidade** - não refaz transferências já realizadas (exceto com `--force`)

---

## 📝 Como Usar

### Uso Manual (Linha de Comando)

```bash
# Transferir do 1º para o 2º bimestre de 2025
python -m scripts.pontuacao_rotinas transferir_saldo_entre_bimestres 2025 1

# Transferir do 4º bimestre de 2025 para o 1º de 2026
python -m scripts.pontuacao_rotinas transferir_saldo_entre_bimestres 2025 4

# Forçar transferência mesmo que já exista
python -m scripts.pontuacao_rotinas transferir_saldo_entre_bimestres 2025 2 --force
```

### Uso Automático (Código Python)

```python
from scripts.pontuacao_rotinas import transferir_saldo_entre_bimestres

# Ao fechar o 1º bimestre
transferir_saldo_entre_bimestres(ano_origem=2025, bimestre_origem=1)

# Ao fechar o ano letivo (4º bimestre) - transfere para 1º/2026
transferir_saldo_entre_bimestres(ano_origem=2025, bimestre_origem=4)
```

---

## ⚙️ Integração com Sistema Automatizado

### Adicionar ao agendador (pontuacao_scheduler.py)

Você pode configurar para rodar automaticamente ao final de cada bimestre:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from scripts.pontuacao_rotinas import transferir_saldo_entre_bimestres
from datetime import datetime

scheduler = BackgroundScheduler()

# Exemplo: rodar no último dia de cada bimestre
# Ajuste as datas conforme seu calendário escolar

# Fim do 1º bimestre (exemplo: 28/fevereiro)
scheduler.add_job(
    lambda: transferir_saldo_entre_bimestres(2025, 1),
    'cron', month=2, day=28, hour=23, minute=59
)

# Fim do 2º bimestre (exemplo: 30/abril)
scheduler.add_job(
    lambda: transferir_saldo_entre_bimestres(2025, 2),
    'cron', month=4, day=30, hour=23, minute=59
)

# E assim por diante...
```

---

## 🔄 Fluxo Recomendado

### Ao Fechar um Bimestre:

1. **Executar bonificações finais**
   ```bash
   python -m scripts.pontuacao_rotinas apply_bimestral_bonus 2025 1
   ```

2. **Transferir saldo para próximo bimestre**
   ```bash
   python -m scripts.pontuacao_rotinas transferir_saldo_entre_bimestres 2025 1
   ```

3. **Verificar no dashboard** se as pontuações iniciais do próximo bimestre estão corretas

---

## 📊 O que Acontece nos Bastidores

### Exemplo Prático:

**Aluno: João Silva**
- **1º Bimestre:**
  - Início: 8.0
  - Bonificação média ≥8: +0.5
  - Bonificação 60 dias: +1.0
  - **Saldo final: 9.5**

- **2º Bimestre (ANTES da função):**
  - ❌ Início: 8.0 (RESETAVA!)
  - João perdia 1.5 pontos de mérito

- **2º Bimestre (DEPOIS da função):**
  - ✅ Início: 9.5 (PRESERVA!)
  - João mantém seu mérito acumulado

### Registro no Banco de Dados:

**Tabela `pontuacao_bimestral`:**
```
aluno_id | ano  | bimestre | pontuacao_inicial | pontuacao_atual
---------|------|----------|-------------------|----------------
123      | 2025 | 2        | 9.5               | 9.5
```

**Tabela `pontuacao_historico`:**
```
aluno_id | ano  | bimestre | tipo_evento            | valor_delta | observacao
---------|------|----------|------------------------|-------------|---------------------------
123      | 2025 | 2        | TRANSFERENCIA_BIMESTRE | +1.5        | Transferência do saldo...
```

---

## 🛡️ Proteções Implementadas

1. ✅ **Anti-duplicidade**: Não refaz transferências já realizadas
2. ✅ **Validação de datas**: Verifica se bimestre de destino existe
3. ✅ **Respeito ao calendário**: Só transfere para alunos já matriculados
4. ✅ **Teto de 10.0**: Limita pontuação máxima
5. ✅ **Auditoria completa**: Todos os lançamentos ficam registrados

---

## 🔧 Correção Retroativa

Se você já tem bimestres sem transferência, pode corrigir:

```python
# Corrigir todas as transferências de 2025
transferir_saldo_entre_bimestres(2025, 1, force=True)
transferir_saldo_entre_bimestres(2025, 2, force=True)
transferir_saldo_entre_bimestres(2025, 3, force=True)
```

---

## 📌 Notas Importantes

1. **Execute ao final do bimestre**, depois das bonificações
2. **Antes de abrir próximo bimestre** para alunos/gestores
3. **Verifique os logs** para confirmar quantos alunos foram transferidos
4. A função considera apenas `PontuacaoHistorico` - não usa `medias_bimestrais` (que são notas escolares)

---

## ✅ Checklist de Implementação

- [ ] Substituir `/scripts/pontuacao_rotinas.py` pelo arquivo atualizado
- [ ] Testar em ambiente de desenvolvimento primeiro
- [ ] Executar para bimestre atual
- [ ] Verificar pontuações iniciais no dashboard
- [ ] Configurar agendamento automático (opcional)
- [ ] Treinar equipe sobre novo fluxo
- [ ] Documentar procedimento interno

---

## 🆘 Troubleshooting

### "Bimestre X/Y não encontrado"
- Verifique se o bimestre destino foi cadastrado na tabela `bimestres`

### "Nenhum aluno transferido"
- Confirme que há alunos matriculados antes do fim do bimestre origem
- Verifique se transferência já foi feita (use `--force` se necessário)

### "Pontuação errada"
- Use `--force` para recalcular
- Verifique se todas as bonificações foram aplicadas antes da transferência

---

## 📞 Suporte

Para dúvidas sobre a implementação, consulte:
- README.md principal do projeto
- Documentação em `/scripts/pontuacao_rotinas.py`
- Logs do sistema após execução

## Licença

(Adicione aqui sua licença, ex: MIT, GPLv3 etc)

---

> Dúvidas? Fale com o mantenedor oficial do projeto ou abra uma issue no GitHub!

---