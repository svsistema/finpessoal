import sqlite3
import sys

DATABASE = "financas.db"

print(f"🔍 Conectando ao banco de dados: {DATABASE}")

try:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    print("✅ Conectado com sucesso.")

    # Verifica se a tabela antiga já existe
    tabelas = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    tabelas = [t[0] for t in tabelas]
    if "transferencias_old" in tabelas:
        print("⚠️  A tabela 'transferencias_old' já existe. Abortando para evitar sobrescrever.")
        sys.exit(1)

    print("\n🚧 Etapa 1: Renomeando tabela antiga para 'transferencias_old'...")
    cursor.execute("ALTER TABLE transferencias RENAME TO transferencias_old;")
    print("✅ Tabela renomeada com sucesso.")

    print("\n🚧 Etapa 2: Criando nova tabela 'transferencias' com CHECK atualizado...")
    cursor.execute("""
    CREATE TABLE transferencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_transferencia TEXT NOT NULL,
        data_efetivacao TEXT,
        descricao TEXT NOT NULL,
        conta_origem_id INTEGER NOT NULL,
        conta_destino_id INTEGER,
        cartao_id INTEGER,
        valor REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Pendente', 'Efetivado')),
        tipo_transferencia TEXT NOT NULL CHECK(
            tipo_transferencia IN ('Entre Contas', 'Para Investimento', 'De Investimento', 'Pagamento Fatura')
        ),
        investimento_id INTEGER,
        compartilhado TEXT NOT NULL CHECK(
            compartilhado IN ('100% Silvia', '100% Nelson', '50/50')
        ),
        FOREIGN KEY (conta_origem_id) REFERENCES instituicoes (id),
        FOREIGN KEY (conta_destino_id) REFERENCES instituicoes (id),
        FOREIGN KEY (cartao_id) REFERENCES cartoes_credito (id),
        FOREIGN KEY (investimento_id) REFERENCES investimentos (id)
    );
    """)
    print("✅ Nova tabela criada com sucesso.")

    print("\n🚧 Etapa 3: Copiando dados da tabela antiga...")
    cursor.execute("""
    INSERT INTO transferencias (
        id, data_transferencia, data_efetivacao, descricao, 
        conta_origem_id, conta_destino_id, cartao_id, valor, 
        status, tipo_transferencia, investimento_id, compartilhado
    )
    SELECT
        id, data_transferencia, data_efetivacao, descricao, 
        conta_origem_id, conta_destino_id, cartao_id, valor, 
        status, tipo_transferencia, investimento_id, compartilhado
    FROM transferencias_old;
    """)
    print("✅ Dados copiados com sucesso.")

    print("\n🚧 Etapa 4: Apagando tabela antiga...")
    cursor.execute("DROP TABLE transferencias_old;")
    print("✅ Tabela antiga removida com sucesso.")

    conn.commit()
    print("\n🎉 Correção concluída com sucesso!")
    print("Agora o campo 'tipo_transferencia' aceita 'Pagamento Fatura' também. ✅")

except sqlite3.Error as e:
    print(f"❌ ERRO de banco de dados: {e}")
    conn.rollback()
except Exception as e:
    print(f"❌ ERRO inesperado: {e}")
    conn.rollback()
finally:
    if conn:
        conn.close()
        print("🔒 Conexão fechada.")
