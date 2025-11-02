import sqlite3
import sys

DATABASE = 'financas.db'

print(f"Tentando conectar ao banco de dados: {DATABASE}")
conn = None

try:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    print("Conectado com sucesso.")

    cursor.execute("PRAGMA foreign_keys = ON;")

    # ===== CRIA TABELA DE TRANSFERÊNCIAS =====
    print("\n--- Criando tabela 'transferencias' ---")
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transferencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_transferencia TEXT NOT NULL,
        data_efetivacao TEXT,
        descricao TEXT NOT NULL,
        conta_origem_id INTEGER NOT NULL,
        conta_destino_id INTEGER,
        cartao_id INTEGER,
        valor REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Pendente', 'Efetivado')),
        tipo_transferencia TEXT NOT NULL CHECK(tipo_transferencia IN ('Entre Contas', 'Para Investimento', 'De Investimento', 'Pagamento Fatura')),
        investimento_id INTEGER,
        compartilhado TEXT NOT NULL CHECK(compartilhado IN ('100% Silvia', '100% Nelson', '50/50')),
        FOREIGN KEY (conta_origem_id) REFERENCES instituicoes (id),
        FOREIGN KEY (conta_destino_id) REFERENCES instituicoes (id),
        FOREIGN KEY (cartao_id) REFERENCES cartoes_credito (id),
        FOREIGN KEY (investimento_id) REFERENCES investimentos (id)
    );
    ''')
    print("Tabela 'transferencias' criada/verificada com sucesso.")

    # ===== ADICIONA COLUNAS AOS INVESTIMENTOS (se ainda não tiver) =====
    print("\n--- Verificando colunas da tabela 'investimentos' ---")
    
    cursor.execute("PRAGMA table_info(investimentos);")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    print(f"Colunas existentes: {colunas_existentes}")

    colunas_para_adicionar = [
        ('custos', 'REAL', 'DEFAULT 0'),
        ('taxas', 'REAL', 'DEFAULT 0'),
        ('irrf', 'REAL', 'DEFAULT 0'),
        ('valor_unitario', 'REAL', 'DEFAULT 0'),
        ('instituicao_id', 'INTEGER', 'REFERENCES instituicoes(id)'),
        ('taxa_negociada', 'REAL', None),
        ('indexador', 'TEXT', None),
        ('observacao', 'TEXT', None)
    ]

    for coluna_info in colunas_para_adicionar:
        nome_coluna = coluna_info[0]
        tipo_coluna = coluna_info[1]
        extras = coluna_info[2]

        if nome_coluna in colunas_existentes:
            print(f"Coluna '{nome_coluna}' já existe. Ignorando.")
        else:
            sql = f"ALTER TABLE investimentos ADD COLUMN {nome_coluna} {tipo_coluna}"
            if extras:
                sql += f" {extras}"
            sql += ";"

            try:
                print(f"Executando: {sql}")
                cursor.execute(sql)
                print(f"Coluna '{nome_coluna}' adicionada com sucesso.")
            except sqlite3.Error as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Aviso: Coluna '{nome_coluna}' já existia: {e}")
                else:
                    print(f"!!! ERRO ao adicionar coluna '{nome_coluna}': {e}", file=sys.stderr)

    print("\n--- Alterações concluídas ---")
    conn.commit()
    print("Alterações salvas no banco de dados.")

except sqlite3.Error as e:
    print(f"!!! ERRO GERAL de banco de dados: {e}", file=sys.stderr)
    if conn:
        conn.rollback()
        print("Rollback realizado.")
except Exception as e:
    print(f"!!! ERRO INESPERADO: {e}", file=sys.stderr)
    if conn:
        conn.rollback()
        print("Rollback realizado.")
finally:
    if conn:
        conn.close()
        print("Conexão com o banco de dados fechada.")
    else:
        print("Não foi possível conectar ao banco de dados.")