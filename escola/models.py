# =============================================================================
# AVISO: Arquivo LEGADO!
# N�o usar para novos desenvolvimentos.
# Sistema migrado para SQLAlchemy (ver models_sqlalchemy.py).
# Este arquivo permanece apenas por refer�ncia/hist�rico.
# =============================================================================

import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime
from flask import current_app, g
from escola.database import get_db

import os
DB_NAME = os.environ.get("DATABASE_FILE", "escola.db")

def criar_tabela_recuperacao_senha():
    import sqlite3
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recuperacao_senha_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                expiracao DATETIME,
                usado INTEGER DEFAULT 0,
                data_uso DATETIME,
                FOREIGN KEY(user_id) REFERENCES usuarios(id)
            );
        ''')
        conn.commit()
    except Exception as e:
        print(f"[ERRO] criando tabela de tokens: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_proximo_rfo_id(incrementar=False):
    ano_atual = str(datetime.now().year)
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()

        rfo_sequencia = c.execute(
            'SELECT numero FROM rfo_sequencia WHERE ano = ?', (ano_atual,)
        ).fetchone()

        proximo_numero = rfo_sequencia['numero'] + 1 if rfo_sequencia else 1
        # NOVO FORMATO: RFO-NNNN/AAAA
        rfo_id = f"RFO-{proximo_numero:04d}/{ano_atual}"

        if incrementar:
            if rfo_sequencia:
                c.execute(
                    'UPDATE rfo_sequencia SET numero = ? WHERE ano = ?',
                    (proximo_numero, ano_atual)
                )
            else:
                c.execute(
                    'INSERT INTO rfo_sequencia (ano, numero) VALUES (?, ?)',
                    (ano_atual, proximo_numero)
                )
            conn.commit()
        return rfo_id
    except sqlite3.Error as e:
        print(f"Erro ao obter/incrementar RFO ID: {e}")
        if conn:
            conn.rollback()
        return f"RFO-ERRO/{ano_atual}"

def get_proximo_fmd_id(incrementar=False):
    ano_atual = str(datetime.now().year)
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()

        fmd_sequencia = c.execute(
            "SELECT numero FROM fmd_sequencia WHERE ano = ?", (ano_atual,)
        ).fetchone()

        proximo_numero = fmd_sequencia["numero"] + 1 if fmd_sequencia else 1
        # NOVO FORMATO: FMD-NNNN/AAAA
        fmd_id = f"FMD-{proximo_numero:04d}/{ano_atual}"

        if incrementar:
            if fmd_sequencia:
                c.execute(
                    "UPDATE fmd_sequencia SET numero = ? WHERE ano = ?",
                    (proximo_numero, ano_atual)
                )
            else:
                c.execute(
                    "INSERT INTO fmd_sequencia (ano, numero) VALUES (?, ?)",
                    (ano_atual, proximo_numero)
                )
            conn.commit()
        return fmd_id
    except sqlite3.Error as e:
        print(f"Erro ao obter/incrementar FMD ID: {e}")
        if conn:
            conn.rollback()
        return f"FMD-ERRO/{ano_atual}"

def criar_tabelas():
    """
    Cria todas as tabelas necess�rias e executa migra��es simples.
    Esta fun��o usa uma conex�o local (sqlite3.connect) e fecha no final.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')

    try:
        # Usu�rios
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                email TEXT,
                nivel INTEGER NOT NULL,
                cargo TEXT,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        # Migra��o autom�tica: garante que coluna 'cargo' exista
        try:
            conn.execute("ALTER TABLE usuarios ADD COLUMN cargo TEXT;")
        except Exception:
            pass

        # Migra��o segura: adicionar coluna email se n�o existir
        try:
            c = conn.execute("PRAGMA table_info(usuarios);")
            colunas = [col[1] for col in c.fetchall()]
            if 'email' not in colunas:
                conn.execute("ALTER TABLE usuarios ADD COLUMN email TEXT;")
                print("   [MIGRA��O] Coluna 'email' adicionada � tabela 'usuarios'.")
        except sqlite3.OperationalError:
            pass

        # Migra��o segura: adicionar coluna data_criacao se n�o existir
        try:
            c = conn.execute("PRAGMA table_info(usuarios);")
            colunas = [col[1] for col in c.fetchall()]
            if 'data_criacao' not in colunas:
                conn.execute("ALTER TABLE usuarios ADD COLUMN data_criacao TEXT DEFAULT CURRENT_TIMESTAMP;")
                print("   [MIGRA��O] Coluna 'data_criacao' adicionada � tabela 'usuarios'.")
        except sqlite3.OperationalError:
            # Se pragma falhar por algum motivo, n�o interrompe todo processo
            pass

        # Alunos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                serie TEXT,
                turma TEXT,
                turno TEXT,
                pai TEXT,
                mae TEXT,
                responsavel TEXT,
                email TEXT,
                rua TEXT,
                numero TEXT,
                complemento TEXT,
                bairro TEXT,
                cidade TEXT,
                estado TEXT,
                data_cadastro TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                usuario_cadastro_id INTEGER,
                telefone TEXT,
                FOREIGN KEY (usuario_cadastro_id) REFERENCES usuarios(id)
            );
        ''')

        # Migra��o: coluna telefone se necess�rio
        try:
            c = conn.execute("PRAGMA table_info(alunos);")
            colunas = [col[1] for col in c.fetchall()]
            if 'telefone' not in colunas:
                conn.execute("ALTER TABLE alunos ADD COLUMN telefone TEXT DEFAULT '';")
                conn.commit()
                print("   [MIGRA��O] Coluna 'telefone' adicionada � tabela 'alunos'.")
        except sqlite3.OperationalError:
            pass

        # Telefones auxiliares
        conn.execute('''
            CREATE TABLE IF NOT EXISTS telefones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aluno_id INTEGER NOT NULL,
                numero TEXT NOT NULL,
                FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
                UNIQUE (aluno_id, numero)
            );
        ''')

        # Sequ�ncias
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rfo_sequencia (
                ano TEXT PRIMARY KEY,
                numero INTEGER NOT NULL
            );
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS fmd_sequencia (
                ano TEXT PRIMARY KEY,
                numero INTEGER NOT NULL
            );
        ''')

        # Tipos de ocorr�ncia
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tipos_ocorrencia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            );
        ''')

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tipos_ocorrencia")
        if cursor.fetchone()[0] == 0:
            tipos_padrao = [
                ('Agress�o F�sica',),
                ('Agress�o Verbal',),
                ('Atraso',),
                ('Comportamento Inadequado',),
                ('Dano ao Patrim�nio',),
                ('Desrespeito',),
                ('Uso Indevido de Celular',),
                ('Uniforme Inadequado',),
                ('Outros',),
            ]
            conn.executemany("INSERT INTO tipos_ocorrencia (nome) VALUES (?)", tipos_padrao)
            print("   [INFO] Tipos de ocorr�ncia padr�o inseridos na tabela 'tipos_ocorrencia'.")

        # Faltas disciplinares
        conn.execute('''
            CREATE TABLE IF NOT EXISTS faltas_disciplinares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                natureza TEXT NOT NULL,
                descricao TEXT NOT NULL,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM faltas_disciplinares")
        if cursor.fetchone()[0] == 0:
            faltas_padrao = [
                ('LEVE', 'Apresentar-se com uniforme diferente do estabelecido pelo regulamento do uniforme;'),
                ('LEVE', 'Apresentar-se com barba ou bigode sem fazer;'),
                ('LEVE', 'Comparecer � EECM com cabelo em desalinho ou fora do padr�o estabelecido pelas diretrizes dos Uniformes;'),
                ('LEVE', 'Chegar atrasado a EECM para o in�cio das aulas, instru��o, treinamento, formatura ou atividade escolar;'),
                ('LEVE', 'Comparecer a EECM sem levar o material necess�rio;'),
                ('LEVE', 'Adentrar ou permanecer em qualquer depend�ncia da EECM, sem autoriza��o;'),
                ('LEVE', 'Consumir alimentos, balas, doces l�quidos ou mascar chicletes durante a aula, instru��o, treinamento, formatura, atividade escolar, e nas depend�ncias da EECM, salvo quando devidamente autorizado;'),
                ('LEVE', 'Conversar ou se mexer quando estiver em forma;'),
                ('LEVE', 'Deixar de entregar � Monitoria, Secretaria ou a Coordena��o, qualquer objeto que n�o lhe perten�a que tenha encontrado na EECM.'),
                ('LEVE', 'Deixar de retribuir cumprimentos ou de prestar sinais de respeito regulamentares, previstos no Manual do Aluno.'),
                ('LEVE', 'Deixar material escolar, objetos ou pe�as de uniforme em locais inapropriados dentro ou fora da unidade escolar;'),
                ('LEVE', 'Descartar pap�is, restos de comida, embalagens ou qualquer objeto no ch�o ou fora de locais apropriados.'),
                ('LEVE', 'Dobrar qualquer pe�a de uniforme para diminuir seu tamanho, desfigurando sua originalidade.'),
                ('LEVE', 'Debru�ar-se sobre a carteira e dormir durante o hor�rio das aulas ou instru��es.'),
                ('LEVE', 'Executar movimentos de ordem unida de forma displicente ou desatenciosa.'),
                ('LEVE', 'Fazer ou provocar excessivo barulho em qualquer depend�ncia da EECM, durante o hor�rio de aula.'),
                ('LEVE', 'N�o levar ao conhecimento de autoridade competente falta ou irregularidade que presenciar ou de que tiver ci�ncia.'),
                ('LEVE', 'Perturbar o estudo do(s) colega(s), com ru�dos ou brincadeiras.'),
                ('LEVE', 'Utilizar-se, na sala, de qualquer publica��o estranha a sua atividade escolar, salvo quando autorizado.'),
                ('LEVE', 'Retardar ou contribuir para o atraso da execu��o de qualquer atividade sem justo motivo.'),
                ('LEVE', 'Sentar-se no ch�o, atentando contra a postura e compostura, estando uniformizado, exceto quando em aula de educa��o F�sica'),
                ('LEVE', 'Utilizar qualquer tipo de jogo, brinquedo, figurinhas, cole��es no interior da EECM.'),
                ('LEVE', 'Usar, a aluna, piercings, brinco fora do padr�o estabelecido, mais de um brinco em cada orelha, alargador ou similares, quando uniformizado, durante a aula, instru��o, treinamento, formatura ou atividade escolar.'),
                ('LEVE', 'Usar, o aluno, piercings, brinco, alargador ou similares, quando uniformizado, durante a aula, instru��o, treinamento, formatura ou atividade escolar.'),
                ('LEVE', 'Usar, quando uniformizado, bon�, capuz ou outros adornos, durante a atividade escolar.'),
                ('LEVE', 'Ficar na sala de aula durante os intervalos e as formaturas di�rias.'),
                ('M�DIA', 'Atrasar ou deixar de atender ao chamado da Diretoria, coordena��o, Oficial de Gest�o Educacional-Militar, o Oficial de Gest�o C�vico-Militar, Monitores, professores ou servidores no exerc�cio de sua fun��o.'),
                ('M�DIA', 'Deixar de comparecer a qualquer atividade extraclasse para a qual tenha sido designado, exceto quando devidamente justificado.'),
                ('M�DIA', 'Deixar de comparecer �s atividades escolares, formaturas, ou delas se ausentar, sem autoriza��o.'),
                ('M�DIA', 'Deixar de cumprir ou esquivar-se de medidas disciplinares impostas pelo Gestor Educacional-Militar.'),
                ('M�DIA', 'Deixar de devolver � EECM, dentro do prazo estipulado, documentos devidamente assinados pelo seu respons�vel.'),
                ('M�DIA', 'Deixar de devolver, no prazo fixado, livros da biblioteca ou outros materiais pertencentes �s EECM;'),
                ('M�DIA', 'Deixar de entregar ao pai ou respons�vel, documento que lhe foi encaminhado pela EECM.'),
                ('M�DIA', 'Deixar de executar tarefas atribu�das da Diretoria, coordena��o, Oficial de Gest�o Educacional-Militar, o Oficial de Gest�o C�vico-Militar, Monitores, professores ou servidores no exerc�cio de sua fun��o.'),
                ('M�DIA', 'Deixar de zelar por sua apresenta��o pessoal.'),
                ('M�DIA', 'Dirigir memoriais ou peti��es a qualquer autoridade, sobre assuntos da al�ada da Diretoria e do Oficial de Gest�o Educacional-Militar.'),
                ('M�DIA', 'Entrar ou sair da EECM por locais n�o permitidos.'),
                ('M�DIA', 'Espalhar boatos ou not�cias tendenciosas por qualquer meio.'),
                ('M�DIA', 'Tocar a sirene, sem ordem para tal.'),
                ('M�DIA', 'Fumar dentro ou nas imedia��es da EECM ou quando uniformizado.'),
                ('M�DIA', 'Ingressar ou sair da EECM sem estar com o uniforme regulamentar, bem como trocar de roupa (trajes civis) dentro da EECM ou em suas media��es.'),
                ('M�DIA', 'Ler ou distribuir, dentro da EECM, publica��es estampas ou jornais que atentem contra a disciplina, a moral e a ordem p�blica.'),
                ('M�DIA', 'Manter contato f�sico que denote envolvimento de cunho amoroso (namoro, beijos, etc.) quando devidamente uniformizado, dentro da EECM ou fora dele.'),
                ('M�DIA', 'N�o zelar pelo nome da Institui��o que representa, deixando de portar-se adequadamente em qualquer ambiente, quando uniformizado ou em atividades relacionadas a EECM.'),
                ('M�DIA', 'Negar-se a colaborar ou participar nos eventos, formaturas, solenidades, desfiles oficiais da EECM.'),
                ('M�DIA', 'Ofender o moral de colegas ou de qualquer membro da Comunidade Escolar por atos, gestos ou palavras.'),
                ('M�DIA', 'Portar-se de forma inconveniente em sala de aula ou outro local de instru��o/recrea��o, bem como transportes de uso coletivo.'),
                ('M�DIA', 'Portar-se de maneira desrespeitosa ou inconveniente nos eventos sociais ou esportivos, promovidos ou com a participa��o da EECM ou fora dela.'),
                ('M�DIA', 'Proferir palavras de baixo cal�o, incompat�veis com as normas da boa educa��o, ou graf�-las em qualquer lugar.'),
                ('M�DIA', 'Propor ou aceitar transa��o pecuni�ria de qualquer natureza, no interior da EECM, sem a devida autoriza��o.'),
                ('M�DIA', 'Provocar ou disseminar a disc�rdia entre colegas.'),
                ('M�DIA', 'Publicar ou contribuir para que sejam publicadas mensagens, fotos, v�deos ou qualquer outro documento, na Internet ou qualquer outro meio de comunica��o, que possam expor a integrante da EECM.'),
                ('M�DIA', 'Retirar ou tentar retirar objeto, de qualquer depend�ncia da EECM, ou mesmo deles servir-se, sem ordem do respons�vel e/ou do propriet�rio.'),
                ('M�DIA', 'Sair de forma sem autoriza��o.'),
                ('M�DIA', 'Sair, entrar ou permanecer na sala de aula sem permiss�o.'),
                ('M�DIA', 'Ser retirado, por mau comportamento, de sala de aula ou qualquer ambiente em que esteja sendo realizada atividade.'),
                ('M�DIA', 'Simular doen�a para esquivar-se ao atendimento de obriga��es e de atividades escolares.'),
                ('M�DIA', 'Tomar parte em jogos de azar ou em apostas na unidade escolar ou fora dela, uniformizados ou n�o.'),
                ('M�DIA', 'Usar as instala��es ou equipamentos esportivos do EECM, sem uniformes adequados, ou sem autoriza��o.'),
                ('M�DIA', 'Usar o uniforme ou o nome do EECM em ambiente inapropriado'),
                ('M�DIA', 'Utilizar, sem autoriza��o, telefones celulares ou quaisquer aparelhos eletr�nicos ou n�o, durante as atividades escolares.'),
                ('M�DIA', 'Usar indevidamente distintivos ou ins�gnias.'),
                ('GRAVE', 'Assinar pelo respons�vel, documento que deva ser entregue � unidade escolar.'),
                ('GRAVE', 'Causar danos ao patrim�nio da unidade escolar.'),
                ('GRAVE', 'Causar ou contribuir para a ocorr�ncia de acidentes de qualquer natureza.'),
                ('GRAVE', 'Comunicar-se com outro aluno ou utilizar-se de qualquer meio n�o permitido durante qualquer instrumento de avalia��o.'),
                ('GRAVE', 'Denegrir o nome da EECM e/ou de qualquer de seus membros atrav�s de procedimentos desrespeitosos, seja por palavras, gestos, meio virtual ou outros.'),
                ('GRAVE', 'Desrespeitar, desobedecer ou desafiar a Diretoria, coordena��o, Oficial de gest�o Educacional-Militar, o Oficial de Gest�o C�vico-Militar, Monitores, professores ou servidores unidade escolar.'),
                ('GRAVE', 'Divulgar, ou concorrer para que isso aconte�a, qualquer imagem ou mat�ria que induza a apologia �s drogas, � viol�ncia e/ou pornografia.'),
                ('GRAVE', 'Entrar na unidade escolar, ou dela se ausentar, sem autoriza��o.'),
                ('GRAVE', 'Extraviar documentos que estejam sob sua responsabilidade.'),
                ('GRAVE', 'Faltar com a verdade e/ou utilizar-se do anonimato para a pr�tica de qualquer falta disciplinar.'),
                ('GRAVE', 'Fazer uso, portar, distribuir, estar sob a��o ou induzir outrem ao uso de bebida alco�lica, entorpecentes, t�xicos ou produtos alucin�genos, no interior da EECM, em suas imedia��es estando ou n�o uniformizado.'),
                ('GRAVE', 'Hastear ou arriar bandeiras e estandartes, sem autoriza��o.'),
                ('GRAVE', 'Instigar colegas a cometer faltas disciplinares e/ou a��es delituosas que comprometam o bom nome da EECM.'),
                ('GRAVE', 'Manter contato f�sico com denota��o libidinosa no ambiente da EECM ou fora dela.'),
                ('GRAVE', 'Obter ou fazer uso de imagens, v�deos, �udios ou de qualquer tipo de publica��o difamat�ria contra qualquer membro da Comunidade Escolar.'),
                ('GRAVE', 'Ofender membros da Comunidade Escolar com a pr�tica de Bullying e Cyberbullying.'),
                ('GRAVE', 'Pichar ou causar qualquer polui��o visual ou sonora dentro e nas proximidades da EECM.'),
                ('GRAVE', 'Portar objetos que ameacem a seguran�a individual e/ou da coletividade.'),
                ('GRAVE', 'Praticar atos contr�rios ao culto e ao respeito aos s�mbolos nacionais;'),
                ('GRAVE', 'Promover ou tomar parte de qualquer manifesta��o coletiva que venha a macular o nome da EECM e/ou que prejudique o bom andamento das aulas e/ou avalia��es;'),
                ('GRAVE', 'Promover trote de qualquer natureza.'),
                ('GRAVE', 'Promover, incitar ou envolver-se em rixa, inclusive luta corporal, dentro ou fora da EECM, estando ou n�o uniformizado;'),
                ('GRAVE', 'Provocar ou tomar parte, uniformizado ou estando na EECM, em manifesta��es de natureza pol�tica.'),
                ('GRAVE', 'Rasurar, violar ou alterar documento ou o conte�do dos mesmos.'),
                ('GRAVE', 'Representar a EECM e/ou por ela tomar compromisso, sem estar para isso autorizado.'),
                ('GRAVE', 'Ter em seu poder, introduzir, ler ou distribuir, dentro da EECM, cartazes, jornais ou publica��es que atentem contra a disciplina e/ou o moral ou de cunho pol�tico-partid�rio.'),
                ('GRAVE', 'Utilizar ou subtrair indevidamente objetos ou valores alheios.'),
                ('GRAVE', 'Utilizar-se de processos fraudulentos na realiza��o de trabalhos pedag�gicos.'),
                ('GRAVE', 'Utilizar-se indevidamente e/ou causar avariar e/ou destrui��o do patrim�nio pertencente a EECM.'),
            ]
            conn.executemany("INSERT INTO faltas_disciplinares (natureza, descricao) VALUES (?, ?)", faltas_padrao)
            print("   [INFO] Faltas disciplinares padr�o inseridas.")

        # Elogios
        conn.execute('''
            CREATE TABLE IF NOT EXISTS elogios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        cursor.execute("SELECT COUNT(*) FROM elogios")
        if cursor.fetchone()[0] == 0:
            elogios_padrao = [
                ('INDIVIDUAL', 'Comportamento exemplar em sala'),
                ('INDIVIDUAL', 'Destaque em desempenho acad�mico'),
                ('INDIVIDUAL', 'Atitude solid�ria com colegas'),
                ('COLETIVO', 'Melhor turma em organiza��o'),
                ('COLETIVO', 'Turma destaque em atividades culturais'),
                ('COLETIVO', 'Engajamento coletivo em projetos'),
            ]
            conn.executemany("INSERT INTO elogios (tipo, descricao) VALUES (?, ?)", elogios_padrao)
            print("   [INFO] Elogios padr�o inseridos.")

        # Ocorr�ncias
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfo_id TEXT NOT NULL,
                aluno_id INTEGER NOT NULL,
                tipo_ocorrencia_id INTEGER NOT NULL,
                data_ocorrencia TEXT NOT NULL,
                observador_id INTEGER NOT NULL,
                relato_observador TEXT NOT NULL,
                advertencia_oral TEXT NOT NULL,
                material_recolhido TEXT,
                data_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                hora_ocorrencia TEXT,
                local_ocorrencia TEXT,
                tipo_ocorrencia INTEGER,
                infracao_id INTEGER,
                descricao_detalhada TEXT,
                status TEXT NOT NULL DEFAULT 'AGUARDANDO TRATAMENTO',
                data_tratamento TEXT,
                tipo_falta TEXT,
                falta_disciplinar_id INTEGER,
                medida_aplicada TEXT,
                observacao_tratamento TEXT,
                reincidencia INTEGER DEFAULT 0,
                relato_estudante TEXT,
                despacho_gestor TEXT,
                data_despacho TEXT,
                responsavel_registro_id INTEGER,
                observador_nome TEXT,
                FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
                FOREIGN KEY (responsavel_registro_id) REFERENCES usuarios(id),
                FOREIGN KEY (tipo_ocorrencia_id) REFERENCES tipos_ocorrencia(id),
                FOREIGN KEY (falta_disciplinar_id) REFERENCES faltas_disciplinares(id)
            );
        ''')

        # MIGRA��O: colunas novas na tabela ocorrencias
        try:
            c = conn.execute("PRAGMA table_info(ocorrencias);")
            colunas = [col[1] for col in c.fetchall()]

            if 'falta_disciplinar_id' not in colunas:
                conn.execute("ALTER TABLE ocorrencias ADD COLUMN falta_disciplinar_id INTEGER REFERENCES faltas_disciplinares(id);")
                print("   [MIGRA��O] Coluna 'falta_disciplinar_id' adicionada � tabela 'ocorrencias'.")

            if 'relato_estudante' not in colunas:
                conn.execute("ALTER TABLE ocorrencias ADD COLUMN relato_estudante TEXT;")
                print("   [MIGRA��O] Coluna 'relato_estudante' adicionada � tabela 'ocorrencias'.")

            if 'despacho_gestor' not in colunas:
                conn.execute("ALTER TABLE ocorrencias ADD COLUMN despacho_gestor TEXT;")
                print("   [MIGRA��O] Coluna 'despacho_gestor' adicionada � tabela 'ocorrencias'.")

            if 'data_despacho' not in colunas:
                conn.execute("ALTER TABLE ocorrencias ADD COLUMN data_despacho TEXT;")
                print("   [MIGRA��O] Coluna 'data_despacho' adicionada � tabela 'ocorrencias'.")

            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"   [AVISO] Tentativa de migra��o de colunas de tratamento falhou: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        # Ficha de Medida Disciplinar (FMD)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ficha_medida_disciplinar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fmd_id TEXT NOT NULL UNIQUE,
                aluno_id INTEGER NOT NULL,
                rfo_id TEXT,
                data_fmd TEXT NOT NULL,
                tipo_falta TEXT NOT NULL,
                medida_aplicada TEXT NOT NULL,
                descricao_falta TEXT NOT NULL,
                observacoes TEXT,
                responsavel_id INTEGER NOT NULL,
                data_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ATIVA',
                FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE,
                FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
            );
        ''')

        # Criar tabelas auxiliares (comportamentos/circunst�ncias)
        criar_tabela_comportamento()
        criar_tabela_circunstancias()

        # Atualizar estrutura da FMD - migra��es adicionais (colunas opcionais)
        try:
            c = conn.execute("PRAGMA table_info(ficha_medida_disciplinar);")
            colunas = [col[1] for col in c.fetchall()]

            if 'nmd_id' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN nmd_id TEXT UNIQUE;")
                print("   [MIGRA��O] Coluna 'nmd_id' adicionada � tabela 'ficha_medida_disciplinar'.")

            if 'data_falta' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN data_falta TEXT;")
                print("   [MIGRA��O] Coluna 'data_falta' adicionada.")

            if 'comportamento_id' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN comportamento_id INTEGER;")
                print("   [MIGRA��O] Coluna 'comportamento_id' adicionada.")

            if 'pontuacao' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN pontuacao INTEGER;")
                print("   [MIGRA��O] Coluna 'pontuacao' adicionada.")

            if 'responsavel_comparecimento' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN responsavel_comparecimento TEXT;")
                print("   [MIGRA��O] Coluna 'responsavel_comparecimento' adicionada.")

            if 'prazo_comparecimento' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN prazo_comparecimento TEXT;")
                print("   [MIGRA��O] Coluna 'prazo_comparecimento' adicionada.")

            if 'circunstancias_atenuantes' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN circunstancias_atenuantes TEXT;")
                print("   [MIGRA��O] Coluna 'circunstancias_atenuantes' adicionada.")

            if 'circunstancias_agravantes' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN circunstancias_agravantes TEXT;")
                print("   [MIGRA��O] Coluna 'circunstancias_agravantes' adicionada.")

            if 'faltas_ids' not in colunas:
                conn.execute("ALTER TABLE ficha_medida_disciplinar ADD COLUMN faltas_ids TEXT;")
                print("   [MIGRA��O] Coluna 'faltas_ids' adicionada (para m�ltiplas faltas).")

            conn.commit()
            print("   ? Migra��o/atualiza��o da estrutura FMD conclu�da com sucesso.")
        except sqlite3.OperationalError as e:
            print(f"   [AVISO] Tentativa de migra��o de FMD falhou (operational): {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        except sqlite3.Error as e:
            print(f"   [ERRO] Erro ao atualizar estrutura da FMD: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        # confirma tabelas e altera��es principais
        conn.commit()

    except sqlite3.Error as e:
        print(f"Erro ao criar/atualizar tabelas: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def criar_admin_inicial(db_conn):
    admin_username = 'admin_ti'
    admin_password = generate_password_hash('admin123')
    admin_nivel = 1
    user = db_conn.execute(
        'SELECT id FROM usuarios WHERE nivel = ?', (admin_nivel,)
    ).fetchone()
    if user is None:
        try:
            db_conn.execute('''
                INSERT INTO usuarios (username, password, nivel, data_criacao)
                VALUES (?, ?, ?, ?)
            ''', (admin_username, admin_password, admin_nivel, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            db_conn.commit()
            print(f"   [INFO] Usu�rio administrador inicial '{admin_username}' criado com sucesso!")
        except sqlite3.Error as e:
            print(f"   ? Erro ao criar usu�rio administrador: {e}")
            db_conn.rollback()


def migrar_estrutura_antiga_ocorrencias():
    migracao_info = {'ocorrencias_migradas': 0, 'sequencia_atualizada': False}
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.execute("PRAGMA table_info(ocorrencias);")
        colunas = [col[1] for col in c.fetchall()]
        if 'data_tratamento' in colunas:
            return migracao_info

        try:
            conn.execute("ALTER TABLE ocorrencias ADD COLUMN status TEXT DEFAULT 'TRATADO';")
            conn.execute("ALTER TABLE ocorrencias ADD COLUMN data_tratamento TEXT;")
            conn.execute("ALTER TABLE ocorrencias ADD COLUMN observador_nome TEXT;")
            conn.execute("ALTER TABLE ocorrencias ADD COLUMN rfo_id TEXT;")
            conn.commit()
            print("   [MIGRA��O] Colunas de tratamento adicionadas � tabela 'ocorrencias'.")
        except sqlite3.OperationalError:
            pass

        ocorrencias_antigas = conn.execute('''
            SELECT id, responsavel_registro_id, tipo_falta
            FROM ocorrencias
            WHERE rfo_id IS NULL
        ''').fetchall()

        if not ocorrencias_antigas:
            return migracao_info

        ano_atual = str(datetime.now().year)
        rfo_sequencia_db = conn.execute(
            'SELECT numero FROM rfo_sequencia WHERE ano = ?', (ano_atual,)
        ).fetchone()
        rfo_counter = rfo_sequencia_db['numero'] if rfo_sequencia_db else 0

        for ocorrencia in ocorrencias_antigas:
            rfo_counter += 1
            rfo_id = f"RFO-{ano_atual}-{str(rfo_counter).zfill(4)}"
            user = conn.execute(
                'SELECT username FROM usuarios WHERE id = ?',
                (ocorrencia['responsavel_registro_id'],)
            ).fetchone()
            observador_nome = user['username'] if user else 'USU�RIO EXCLU�DO'
            status_novo = 'TRATADO' if ocorrencia['tipo_falta'] else 'AGUARDANDO TRATAMENTO'

            conn.execute('''
                UPDATE ocorrencias
                SET rfo_id = ?,
                    observador_nome = ?,
                    data_tratamento = ?,
                    status = ?
                WHERE id = ?
            ''', (rfo_id, observador_nome, datetime.now().strftime('%Y-%m-%d'), status_novo, ocorrencia['id']))
            migracao_info['ocorrencias_migradas'] += 1

        if rfo_counter > 0:
            if rfo_sequencia_db:
                conn.execute(
                    'UPDATE rfo_sequencia SET numero = ? WHERE ano = ?',
                    (rfo_counter, ano_atual)
                )
            else:
                conn.execute(
                    'INSERT INTO rfo_sequencia (ano, numero) VALUES (?, ?)',
                    (ano_atual, rfo_counter)
                )
            migracao_info['sequencia_atualizada'] = True

        conn.commit()
    except sqlite3.Error as e:
        print(f"   ? Erro durante a migra��o: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return migracao_info


def get_tipos_ocorrencia():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM tipos_ocorrencia ORDER BY nome")
    return cursor.fetchall()


def get_faltas_disciplinares():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, natureza, descricao FROM faltas_disciplinares ORDER BY natureza, descricao")
    return cursor.fetchall()


def get_elogios():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, tipo, descricao FROM elogios ORDER BY tipo, descricao")
    return cursor.fetchall()


def get_faltas_por_natureza(natureza):
    """Retorna faltas de uma natureza espec�fica com ID e descri��o"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, descricao 
        FROM faltas_disciplinares 
        WHERE natureza = ?
        ORDER BY id, descricao
    """, (natureza,))
    return cursor.fetchall()


def criar_tabela_comportamento():
    """Cria tabela de comportamentos se n�o existir"""
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comportamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL UNIQUE,
                pontuacao INTEGER NOT NULL,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Inserir comportamentos padr�o
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM comportamentos")
        if cursor.fetchone()[0] == 0:
            comportamentos_padrao = [
                ('Excelente', 5),
                ('�timo', 4),
                ('Bom', 3),
                ('Regular', 2),
                ('Insatisfat�rio', 1),
            ]
            conn.executemany(
                "INSERT INTO comportamentos (descricao, pontuacao) VALUES (?, ?)",
                comportamentos_padrao
            )

        conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela comportamentos: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def criar_tabela_circunstancias():
    """Cria tabela de circunst�ncias atenuantes/agravantes"""
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS circunstancias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL CHECK(tipo IN ('ATENUANTE', 'AGRAVANTE')),
                descricao TEXT NOT NULL,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Inserir circunst�ncias padr�o
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM circunstancias")
        if cursor.fetchone()[0] == 0:
            circunstancias_padrao = [
                ('ATENUANTE', 'Primeiro registro de falta'),
                ('ATENUANTE', 'Bom hist�rico de comportamento'),
                ('ATENUANTE', 'Colabora��o durante apura��o'),
                ('ATENUANTE', 'Confiss�o espont�nea'),
                ('AGRAVANTE', 'Reincid�ncia'),
                ('AGRAVANTE', 'Falta cometida em grupo'),
                ('AGRAVANTE', 'Desrespeito durante apura��o'),
                ('AGRAVANTE', 'Tentativa de ocultar fatos'),
            ]
            conn.executemany(
                "INSERT INTO circunstancias (tipo, descricao) VALUES (?, ?)",
                circunstancias_padrao
            )

        conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela circunstancias: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_comportamentos():
    """Retorna todos os comportamentos cadastrados"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao, pontuacao FROM comportamentos ORDER BY pontuacao DESC")
    return cursor.fetchall()

from datetime import datetime, timedelta, date
import calendar

def _end_of_bimestre(ano, bimestre):
    # mapeamento simples: 1->fev, 2->abr, 3->jun, 4->ago
    mapping = {1: 2, 2: 4, 3: 6, 4: 8}
    month = mapping.get(int(bimestre), 8)
    last_day = calendar.monthrange(int(ano), month)[1]
    return date(int(ano), month, last_day)

def _infer_comportamento_por_faixa(p):
    try:
        p = float(p)
    except Exception:
        return None
    if p >= 10.0:
        return "Excepcional"
    elif p >= 9.0:
        return "�timo"
    elif p >= 7.0:
        return "Bom"
    elif p >= 5.0:
        return "Regular"
    elif p >= 2.0:
        return "Insuficiente"
    else:
        return "Incompat�vel"

def compute_pontuacao_corrente(aluno_id, as_of=None):
    """
    Calcula a pontua��o corrente conforme regras 8,9 e 10:
     - base = pontuacao_atual do �ltimo bimestre encerrado (se houver) ou 8.0
     - soma FMDs posteriores ao fim desse bimestre (ou todas, se n�o houver)
     - bonus8: +0.5 se bimestre imediatamente anterior ao last_closed_bimestre teve pontua��o >= 8.0
     - bonus9: ap�s 60 dias sem perda (desde matr�cula ou �ltima perda), +0.2 por dia a partir do dia 61
     - clamp 0.0..10.0 e round(,2)
    Retorna dict {'pontuacao': float, 'comportamento': str, 'detalhes': {...}}
    """
    from flask import current_app
    try:
        if as_of is None:
            as_of = datetime.utcnow()
        conn = get_db()

        # 1) localizar �ltimo pontuacao_bimestral (assumido como �ltimo bimestre fechado)
        pb = conn.execute(
            "SELECT id, ano, bimestre, pontuacao_inicial, pontuacao_atual, atualizado_em FROM pontuacao_bimestral WHERE aluno_id = ? ORDER BY ano DESC, bimestre DESC LIMIT 1",
            (aluno_id,)
        ).fetchone()

        if pb:
            try:
                base = float(pb['pontuacao_atual'])
            except Exception:
                base = 8.0
            # determinar cutoff_date (fim do bimestre)
            cutoff_date = None
            try:
                ae = pb.get('atualizado_em') if isinstance(pb, dict) else None
                if ae:
                    try:
                        cutoff_date = datetime.fromisoformat(ae) if isinstance(ae, str) else ae
                    except Exception:
                        try:
                            cutoff_date = datetime.strptime(ae, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            cutoff_date = None
                if cutoff_date is None:
                    end_date = _end_of_bimestre(int(pb['ano']), int(pb['bimestre']))
                    cutoff_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
            except Exception:
                cutoff_date = None
        else:
            base = 8.0
            cutoff_date = None

        # 2) soma pontos_aplicados das FMDs posteriores ao cutoff_date (ou todas se None)
        soma_fmd = 0.0
        try:
            if cutoff_date:
                q = "SELECT SUM(COALESCE(pontos_aplicados,0.0)) as soma FROM ficha_medida_disciplinar WHERE aluno_id = ? AND datetime(data_registro) > datetime(?)"
                r = conn.execute(q, (aluno_id, cutoff_date.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()
            else:
                r = conn.execute("SELECT SUM(COALESCE(pontos_aplicados,0.0)) as soma FROM ficha_medida_disciplinar WHERE aluno_id = ?", (aluno_id,)).fetchone()
            soma_fmd = float(r['soma']) if r and r['soma'] is not None else 0.0
        except Exception:
            current_app.logger.debug("compute_pontuacao_corrente: erro ao somar FMDs", exc_info=True)
            soma_fmd = 0.0

        # 3) bonus8: checar bimestre imediatamente anterior ao last_closed_bimestre
        bonus8 = 0.0
        try:
            if pb:
                ano = int(pb['ano'])
                b = int(pb['bimestre'])
                if b > 1:
                    prev_b, prev_ano = b - 1, ano
                else:
                    prev_b, prev_ano = 4, ano - 1
                prev = conn.execute(
                    "SELECT pontuacao_atual FROM pontuacao_bimestral WHERE aluno_id = ? AND ano = ? AND bimestre = ? LIMIT 1",
                    (aluno_id, prev_ano, prev_b)
                ).fetchone()
                if prev and prev['pontuacao_atual'] is not None:
                    try:
                        if float(prev['pontuacao_atual']) >= 8.0:
                            bonus8 = 0.5
                    except Exception:
                        pass
        except Exception:
            current_app.logger.debug("compute_pontuacao_corrente: erro ao calcular bonus8", exc_info=True)

        # 4) bonus9: identificar �ltima perda (<0) ou usar data_matricula; contar 60 dias e aplicar +0.2 por dia a partir do dia 61
        bonus9 = 0.0
        try:
            last_loss_row = conn.execute(
                "SELECT MAX(datetime(data_registro)) as last_loss FROM ficha_medida_disciplinar WHERE aluno_id = ? AND pontos_aplicados < 0",
                (aluno_id,)
            ).fetchone()
            last_loss = None
            if last_loss_row and last_loss_row['last_loss']:
                try:
                    last_loss = datetime.fromisoformat(last_loss_row['last_loss'])
                except Exception:
                    try:
                        last_loss = datetime.strptime(last_loss_row['last_loss'], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        last_loss = None
            if last_loss is None:
                adm_row = conn.execute("SELECT data_matricula FROM alunos WHERE id = ? LIMIT 1", (aluno_id,)).fetchone()
                dm = adm_row['data_matricula'] if adm_row else None
                if dm:
                    try:
                        last_loss = datetime.fromisoformat(dm)
                    except Exception:
                        try:
                            last_loss = datetime.strptime(dm, "%Y-%m-%d")
                        except Exception:
                            last_loss = None
            if last_loss:
                grace_end = last_loss + timedelta(days=60)
                if as_of > grace_end:
                    days_eligible = (as_of.date() - grace_end.date()).days
                    if days_eligible > 0:
                        bonus9 = days_eligible * 0.2
        except Exception:
            current_app.logger.debug("compute_pontuacao_corrente: erro ao calcular bonus9", exc_info=True)
            bonus9 = 0.0

        total = base + soma_fmd + bonus8 + bonus9
        try:
            total = round(float(total), 2)
        except Exception:
            total = float(base)
        if total > 10.0:
            total = 10.0
        if total < 0.0:
            total = 0.0

        comportamento = _infer_comportamento_por_faixa(total)

        detalhes = {
            'base': base,
            'soma_fmd': soma_fmd,
            'bonus8': round(bonus8, 2),
            'bonus9': round(bonus9, 2),
            'total_raw': total,
            'cutoff_date': cutoff_date.isoformat() if cutoff_date else None
        }
        return {'pontuacao': total, 'comportamento': comportamento, 'detalhes': detalhes}
    except Exception:
        try:
            current_app.logger.debug("compute_pontuacao_corrente: erro inesperado", exc_info=True)
        except Exception:
            pass
        return {'pontuacao': None, 'comportamento': None, 'detalhes': {}}

def get_aluno_estado_atual(aluno_id):
    """
    Retorna {'comportamento': str, 'pontuacao': float}
    Agora devolve a pontua��o corrente calculada por compute_pontuacao_corrente (regra 10).
    Em caso de erro, faz um fallback para comportamento compat�vel com a vers�o anterior.
    """
    from flask import current_app
    try:
        res = compute_pontuacao_corrente(aluno_id)
        # se c�lculo falhar, tentar fallback � l�gica antiga m�nima
        if res.get('pontuacao') is None:
            # fallback: vers�o compat�vel com a fun��o antiga
            db = get_db()
            pontuacao = None
            try:
                pb = db.execute(
                    "SELECT pontuacao_atual FROM pontuacao_bimestral WHERE aluno_id = ? ORDER BY ano DESC, bimestre DESC LIMIT 1",
                    (aluno_id,)
                ).fetchone()
                if pb and pb.get('pontuacao_atual') is not None:
                    pontuacao = pb['pontuacao_atual']
                else:
                    srow = db.execute("SELECT SUM(COALESCE(pontos_aplicados,0.0)) AS soma_pontos FROM ficha_medida_disciplinar WHERE aluno_id = ?", (aluno_id,)).fetchone()
                    soma_pontos = srow['soma_pontos'] if srow else None
                    inicial = 8.0
                    if soma_pontos is not None:
                        pontuacao = round(float(inicial) + float(soma_pontos), 2)
                    else:
                        pontuacao = round(float(inicial), 2)
            except Exception:
                current_app.logger.debug("get_aluno_estado_atual: fallback erro ao somar pontos_aplicados", exc_info=True)
                pontuacao = None
            # inferir comportamento pela faixa
            comportamento = _infer_comportamento_por_faixa(pontuacao) if pontuacao is not None else None
            return {'comportamento': comportamento, 'pontuacao': pontuacao}
        # retorno normal
        return {'comportamento': res.get('comportamento'), 'pontuacao': res.get('pontuacao')}
    except Exception:
        try:
            current_app.logger.debug("get_aluno_estado_atual: erro ao calcular estado atual", exc_info=True)
        except Exception:
            pass
        return {'comportamento': None, 'pontuacao': None}

def get_circunstancias(tipo):
    """Retorna circunst�ncias por tipo"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, descricao 
        FROM circunstancias 
        WHERE tipo = ?
        ORDER BY descricao
    """, (tipo,))
    return cursor.fetchall()


def get_proximo_nmd_id(incrementar=False):
    """Gera o pr�ximo ID de Notifica��o de Medida Disciplinar"""
    ano_atual = str(datetime.now().year)
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()

        # Verificar se existe sequ�ncia para NMD
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nmd_sequencia'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE IF NOT EXISTS nmd_sequencia (
                    ano TEXT PRIMARY KEY,
                    numero INTEGER NOT NULL
                )
            ''')

        nmd_sequencia = c.execute(
            'SELECT numero FROM nmd_sequencia WHERE ano = ?', (ano_atual,)
        ).fetchone()

        proximo_numero = nmd_sequencia['numero'] + 1 if nmd_sequencia else 1
        nmd_id = f"NMD-{ano_atual}-{str(proximo_numero).zfill(4)}"

        if incrementar:
            if nmd_sequencia:
                c.execute(
                    'UPDATE nmd_sequencia SET numero = ? WHERE ano = ?',
                    (proximo_numero, ano_atual)
                )
            else:
                c.execute(
                    'INSERT INTO nmd_sequencia (ano, numero) VALUES (?, ?)',
                    (ano_atual, proximo_numero)
                )
            conn.commit()
        return nmd_id
    except sqlite3.Error as e:
        print(f"Erro ao obter/incrementar NMD ID: {e}")
        if conn:
            conn.rollback()
        return f"NMD-{ano_atual}-ERRO"
    
# Nota: este � um patch/adi��o ao seu m�dulo models.py existente.
# Inserir as fun��es abaixo em models.py (ou mesclar com as existentes).
# Objetivo: garantir migra��es seguras para o m�dulo disciplinar (ocorrencias_alunos + colunas novas).
#
# N�O sobrescreva outras fun��es j� presentes no seu models.py sem revisar.
# A fun��o ensure_disciplinar_migrations(db_conn) � idempotente e pode ser chamada
# durante o registro do blueprint disciplinar.

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _table_has_column(db_conn, table, column):
    """Retorna True se a tabela existir e tiver a coluna informada."""
    try:
        rows = db_conn.execute(f"PRAGMA table_info({table})").fetchall()
        cols = [r[1] if isinstance(r, (list, tuple)) else (r.get('name') if isinstance(r, dict) else None) for r in rows]
        return column in cols
    except Exception:
        return False


def column_exists(db_conn, table, column):
    """
    Retorna True se a coluna j� existe na tabela (usando PRAGMA table_info).
    """
    try:
        cur = db_conn.execute(f"PRAGMA table_info({table});")
        rows = cur.fetchall()
        for row in rows:
            # row[1] � o nome da coluna retornado pelo PRAGMA table_info
            if row[1] == column:
                return True
    except Exception:
        try:
            import logging
            logging.getLogger('disciplinar').warning("N�o foi poss�vel verificar exist�ncia da coluna %s.%s", table, column)
        except Exception:
            pass
    return False
def ensure_disciplinar_migrations(db_conn):
    """
    Cria/atualiza objetos do banco necess�rios para o m�dulo disciplinar (RFO/FMD).
    - Cria tabela ocorrencias_alunos (m:n entre ocorrencias e alunos)
    - Garante colunas adicionais na tabela ocorrencias de forma segura (ALTER TABLE ADD COLUMN)
    - Cria tabela fmd_sequencia se ausente (usada para gerar FMD-XXXX/ANO)
    Idempotente: pode ser chamada em cada inicializa��o sem efeitos colaterais.
    """
    try:
        # 1) criar tabela ocorrencias_alunos (muitos-para-muitos)
        try:
            db_conn.execute('''
                CREATE TABLE IF NOT EXISTS ocorrencias_alunos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocorrencia_id INTEGER NOT NULL,
                    aluno_id INTEGER NOT NULL,
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ocorrencia_id) REFERENCES ocorrencias(id) ON DELETE CASCADE,
                    FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE CASCADE
                );
            ''')
        except Exception:
            # tentativa robusta - ignorar falha mas logar
            logger.exception("Falha criando ocorrencias_alunos (ignorando)")

        # 2) adicionar colunas em ocorrencias se n�o existirem
        extra_cols = {
            'tipo_ocorrencia_text': "TEXT",
            'subtipo_elogio': "TEXT",
            'tratamento_tipo': "TEXT",
            'observador_advertencia_oral': "TEXT",
            'pontos_aplicados': "REAL DEFAULT 0.0",
            'falta_ids_csv': "TEXT",
            'circunstancias_atenuantes': "TEXT",
            'circunstancias_agravantes': "TEXT",
        }

        try:
            cur = db_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ocorrencias'").fetchone()
            if cur:
                for col, coltype in extra_cols.items():
                    if not _table_has_column(db_conn, 'ocorrencias', col):
                        if not column_exists(db_conn, 'ocorrencias', col):
                            try:
                                db_conn.execute(f'ALTER TABLE ocorrencias ADD COLUMN {col} {coltype};')
                                try:
                                    import logging
                                    logging.getLogger('disciplinar').info("Adicionada coluna %s (%s) em ocorrencias", col, coltype)
                                except Exception:
                                    pass
                            except Exception as e:
                                try:
                                    import logging
                                    logging.getLogger('disciplinar').warning("Erro ao adicionar coluna %s em ocorrencias (ignorando): %s", col, e)
                                except Exception:
                                    pass
                        else:
                            try:
                                import logging
                                logging.getLogger('disciplinar').info("Coluna %s j� existe em ocorrencias � pulando.", col)
                            except Exception:
                                pass
            else:
                # tabela ocorrencias n�o existe � pular tentativa de migra��o de colunas
                logging.getLogger('disciplinar').info("Tabela ocorrencias n�o existe; pulando migra��es de coluna.")
        except Exception:
            logger.exception("Falha ao verificar/executar ALTER TABLE ocorrencias")
        try:
            db_conn.execute('''
                CREATE TABLE IF NOT EXISTS fmd_sequencia (
                    ano INTEGER PRIMARY KEY,
                    seq INTEGER NOT NULL
                );
            ''')
        except Exception:
            logger.exception("Falha criando fmd_sequencia (ignorando)")

        # 4) (opcional) garantir pontuacao_bimestral e pontuacao_historico
        try:
            db_conn.execute('''
                CREATE TABLE IF NOT EXISTS pontuacao_bimestral (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id INTEGER NOT NULL,
                    ano INTEGER NOT NULL,
                    bimestre INTEGER NOT NULL,
                    pontuacao_inicial REAL,
                    pontuacao_atual REAL,
                    atualizado_em DATETIME
                );
            ''')
        except Exception:
            logger.exception("Falha criando pontuacao_bimestral (ignorando)")

        try:
            db_conn.execute('''
                CREATE TABLE IF NOT EXISTS pontuacao_historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id INTEGER,
                    ano INTEGER,
                    bimestre INTEGER,
                    ocorrencia_id INTEGER,
                    tipo_evento TEXT,
                    valor_delta REAL,
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        except Exception:
            logger.exception("Falha criando pontuacao_historico (ignorando)")

        try:
            db_conn.commit()
        except Exception:
            pass

        logger.info("ensure_disciplinar_migrations: finalizado (idempotente).")

    except Exception:
        logger.exception("Erro inesperado em ensure_disciplinar_migrations")


def next_fmd_seq_and_year(db_conn):
    """
    Retorna (seq, ano) pr�ximo baseado em fmd_sequencia; cria entrada se faltante.
    """
    ano = datetime.now().year
    try:
        row = db_conn.execute('SELECT seq FROM fmd_sequencia WHERE ano = ?', (ano,)).fetchone()
        if row and row[0] is not None:
            seq = int(row[0]) + 1
            db_conn.execute('UPDATE fmd_sequencia SET seq = ? WHERE ano = ?', (seq, ano))
            return seq, ano
    except Exception:
        pass

    maxseq = 0
    try:
        rows = db_conn.execute("SELECT fmd_id FROM ficha_medida_disciplinar WHERE fmd_id LIKE ?", (f"FMD-%/{ano}",)).fetchall()
        for r in rows:
            fid = r[0] if isinstance(r, (list, tuple)) else (r.get('fmd_id') if isinstance(r, dict) else None)
            if not fid:
                continue
            import re
            m = re.match(r'^FMD-(\d{1,})/' + str(ano) + r'$', fid)
            if m:
                try:
                    n = int(m.group(1))
                    if n > maxseq:
                        maxseq = n
                except Exception:
                    pass
    except Exception:
        maxseq = 0

    seq = maxseq + 1
    try:
        db_conn.execute('INSERT OR REPLACE INTO fmd_sequencia (ano, seq) VALUES (?, ?)', (ano, seq))
    except Exception:
        pass
    return seq, ano

# End of additions for disciplinar migrations    

# Fun��o adicionada: create_or_update_fmd_for_rfo
from datetime import datetime

def create_or_update_fmd_for_rfo(rfo_id, aluno_id, medida_aplicada, pontos_aplicados,
                                 data_registro=None, responsavel_id=None, comportamento_id=None):
    """
    Cria ou atualiza (idempotente) um registro em ficha_medida_disciplinar para o par (rfo_id, aluno_id).
    - Se j� existir uma ficha com este rfo_id e aluno_id, atualiza campos essenciais.
    - Caso contr�rio, insere uma nova ficha com fmd_id gerado no formato FMD-XXXX/AAAA.
    Retorna dict { 'ok': True, 'action': 'insert'|'update', 'fmd_rowid': <rowid> } ou {'ok': False, 'error': str}.
    Observa��es:
    - Esta fun��o usa apenas colunas comumente presentes: fmd_id, rfo_id, aluno_id, medida_aplicada,
      pontos_aplicados, data_registro, responsavel_id, comportamento_id, criado_em, atualizado_em.
    - N�o altera pontuacao_bimestral (persist�ncia de bimestre fica por conta do fechamento).
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        # normalizar data_registro
        if data_registro is None:
            data_registro_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        else:
            if isinstance(data_registro, str):
                data_registro_str = data_registro
            else:
                data_registro_str = data_registro.strftime('%Y-%m-%d %H:%M:%S')

        # 1) verificar exist�ncia (idempot�ncia)
        existing = cur.execute(
            "SELECT id FROM ficha_medida_disciplinar WHERE rfo_id = ? AND aluno_id = ? LIMIT 1",
            (rfo_id, aluno_id)
        ).fetchone()

        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        if existing:
            fmd_id = existing['id'] if 'id' in existing.keys() else existing[0]
            # Atualiza somente os campos principais; mant�m demais campos como est�o
            cur.execute("""
                UPDATE ficha_medida_disciplinar
                SET medida_aplicada = ?,
                    pontos_aplicados = ?,
                    data_registro = ?,
                    responsavel_id = ?,
                    comportamento_id = ?,
                    atualizado_em = ?
                WHERE id = ?
            """, (medida_aplicada, pontos_aplicados, data_registro_str, responsavel_id, comportamento_id, now_str, fmd_id))
            conn.commit()
            return {'ok': True, 'action': 'update', 'fmd_rowid': fmd_id}
        else:
            # gerar fmd_id sequencial por ano (formato compat�vel com migra��es anteriores)
            ano = datetime.utcnow().year
            try:
                row = cur.execute("SELECT COUNT(*) as c FROM ficha_medida_disciplinar WHERE fmd_id LIKE ?", (f"FMD-%/{ano}",)).fetchone()
                seq = int(row['c']) if row and row['c'] is not None else 0
            except Exception:
                seq = 0
            seq += 1
            fmd_code = f"FMD-{str(seq).zfill(4)}/{ano}"

            cur.execute("""
                INSERT INTO ficha_medida_disciplinar (fmd_id, rfo_id, aluno_id, medida_aplicada, pontos_aplicados, data_registro, responsavel_id, comportamento_id, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fmd_code, rfo_id, aluno_id, medida_aplicada, pontos_aplicados, data_registro_str, responsavel_id, comportamento_id, now_str, now_str))
            conn.commit()
            new_id = cur.lastrowid
            return {'ok': True, 'action': 'insert', 'fmd_rowid': new_id, 'fmd_id': fmd_code}
    except Exception as e:
        try:
            # tentar rollback para manter DB consistente
            conn.rollback()
        except Exception:
            pass
        from flask import current_app
        try:
            current_app.logger.debug("create_or_update_fmd_for_rfo: erro", exc_info=True)
        except Exception:
            pass
        return {'ok': False, 'error': str(e)}











