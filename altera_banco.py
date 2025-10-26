import sqlite3
import sys # Para mensagens de erro

DATABASE = 'financas.db'

# Lista de colunas a adicionar
# Cada item é uma tupla: (nome_coluna, tipo_coluna, [default_se_necessario])
colunas_para_adicionar = [
    ('custos', 'REAL', 'DEFAULT 0'),
    ('taxas', 'REAL', 'DEFAULT 0'),
    ('irrf', 'REAL', 'DEFAULT 0'),
    ('valor_unitario', 'REAL', 'DEFAULT 0'),
    ('instituicao_id', 'INTEGER', 'REFERENCES instituicoes(id)'), # Chave estrangeira
    ('taxa_negociada', 'REAL', None), # Sem default
    ('indexador', 'TEXT', None),
    ('observacao', 'TEXT', None)
]

print(f"Tentando conectar ao banco de dados: {DATABASE}")
conn = None # Inicializa conn como None
try:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    print("Conectado com sucesso.")

    # Habilita chaves estrangeiras (boa prática)
    cursor.execute("PRAGMA foreign_keys = ON;")

    print("\n--- Adicionando colunas à tabela 'investimentos' ---")

    # Verifica as colunas existentes para evitar erros
    cursor.execute("PRAGMA table_info(investimentos);")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    print(f"Colunas existentes: {colunas_existentes}")

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
                colunas_existentes.append(nome_coluna) # Adiciona à lista para próxima verificação
            except sqlite3.Error as e:
                # Verifica se o erro é "duplicate column name"
                if "duplicate column name" in str(e).lower():
                     print(f"Aviso: Coluna '{nome_coluna}' já existia (erro ignorado): {e}")
                     if nome_coluna not in colunas_existentes: # Garante que está na lista
                         colunas_existentes.append(nome_coluna)
                else:
                    print(f"!!! ERRO ao adicionar coluna '{nome_coluna}': {e}", file=sys.stderr)
                    # Decide se quer parar ou continuar
                    # raise e # Descomente esta linha se quiser parar a execução em caso de erro

    print("\n--- Alterações concluídas ---")
    conn.commit()
    print("Alterações salvas no banco de dados.")

except sqlite3.Error as e:
    print(f"!!! ERRO GERAL de banco de dados: {e}", file=sys.stderr)
    if conn:
        conn.rollback() # Desfaz qualquer alteração parcial
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