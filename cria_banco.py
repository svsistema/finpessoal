import sqlite3

conn = sqlite3.connect('financas.db')
cursor = conn.cursor()
print("Conectado ao banco de dados.")

# --- Tabelas de Cadastros (Verificando) ---
cursor.execute('''CREATE TABLE IF NOT EXISTS instituicoes (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL UNIQUE);''')
cursor.execute('''CREATE TABLE IF NOT EXISTS cartoes_credito (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL, instituicao_id INTEGER NOT NULL, vencimento INTEGER NOT NULL, limite REAL NOT NULL, FOREIGN KEY (instituicao_id) REFERENCES instituicoes (id));''')
cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL UNIQUE, tipo TEXT NOT NULL CHECK(tipo IN ('Receita', 'Despesa')));''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tickers (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL UNIQUE, classe TEXT NOT NULL, tipo TEXT NOT NULL);''')
cursor.execute('''CREATE TABLE IF NOT EXISTS moedas (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT NOT NULL UNIQUE, descricao TEXT NOT NULL);''')
cursor.execute('''CREATE TABLE IF NOT EXISTS operacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL UNIQUE, natureza TEXT NOT NULL CHECK(natureza IN ('Entrada', 'Saida')));''')
cursor.execute('''CREATE TABLE IF NOT EXISTS movimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data_movimento TEXT NOT NULL, data_efetivacao TEXT,
        descricao TEXT NOT NULL, categoria_id INTEGER NOT NULL, instituicao_id INTEGER NOT NULL, cartao_id INTEGER,
        valor REAL NOT NULL, status TEXT NOT NULL, compartilhado TEXT NOT NULL,
        FOREIGN KEY (categoria_id) REFERENCES categorias (id), FOREIGN KEY (instituicao_id) REFERENCES instituicoes (id),
        FOREIGN KEY (cartao_id) REFERENCES cartoes_credito (id));''')
print("Tabelas existentes verificadas.")

# --- NOVA TABELA: Investimentos ---
try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS investimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_investimento TEXT NOT NULL,
        data_vencimento TEXT,
        ticker_id INTEGER NOT NULL,
        operacao_id INTEGER NOT NULL,
        moeda_id INTEGER NOT NULL,
        quantidade REAL NOT NULL,
        valor_total REAL NOT NULL, 
        FOREIGN KEY (ticker_id) REFERENCES tickers (id),
        FOREIGN KEY (operacao_id) REFERENCES operacoes (id),
        FOREIGN KEY (moeda_id) REFERENCES moedas (id)
    );
    ''')
    print("Tabela 'investimentos' criada com sucesso.")
except sqlite3.Error as e:
    print(f"Erro ao criar a tabela 'investimentos': {e}")

conn.commit()
conn.close()
print("Banco de dados atualizado e conexão fechada.")