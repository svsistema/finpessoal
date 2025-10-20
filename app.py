from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_pode_ser_qualquer_coisa'
DATABASE = 'financas.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index(): return redirect(url_for('movimentos'))

# --- ROTAS INSTITUIÇÕES ---
@app.route('/instituicoes', methods=['GET', 'POST'])
def instituicoes():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('INSERT INTO instituicoes (descricao) VALUES (?)', (request.form['descricao'],))
            conn.commit()
        except sqlite3.IntegrityError: flash('Essa instituição já existe.', 'error')
        return redirect(url_for('instituicoes'))
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    conn.close()
    return render_template('instituicoes.html', instituicoes=instituicoes_list)

@app.route('/instituicoes/edit/<int:id>', methods=['GET', 'POST'])
def edit_instituicao(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('UPDATE instituicoes SET descricao = ? WHERE id = ?', (request.form['descricao'], id))
            conn.commit()
            return redirect(url_for('instituicoes'))
        except sqlite3.IntegrityError: flash('Já existe uma instituição com esse nome.', 'error')
    instituicao = conn.execute('SELECT * FROM instituicoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar_instituicao.html', instituicao=instituicao)

@app.route('/instituicoes/delete/<int:id>', methods=['POST'])
def delete_instituicao(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM instituicoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('instituicoes'))

# --- ROTAS CARTÕES ---
@app.route('/cartoes', methods=['GET', 'POST'])
def cartoes():
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('INSERT INTO cartoes_credito (descricao, instituicao_id, vencimento, limite) VALUES (?, ?, ?, ?)',(request.form['descricao'], request.form['instituicao_id'], request.form['vencimento'], request.form['limite']))
        conn.commit()
        return redirect(url_for('cartoes'))
    cartoes_list = conn.execute('SELECT c.*, i.descricao as instituicao_nome FROM cartoes_credito c JOIN instituicoes i ON c.instituicao_id = i.id ORDER BY c.descricao').fetchall()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    conn.close()
    return render_template('cartoes.html', cartoes=cartoes_list, instituicoes=instituicoes_list)

@app.route('/cartoes/edit/<int:id>', methods=['GET', 'POST'])
def edit_cartao(id):
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('UPDATE cartoes_credito SET descricao = ?, instituicao_id = ?, vencimento = ?, limite = ? WHERE id = ?', (request.form['descricao'], request.form['instituicao_id'], request.form['vencimento'], request.form['limite'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('cartoes'))
    cartao = conn.execute('SELECT * FROM cartoes_credito WHERE id = ?', (id,)).fetchone()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    conn.close()
    return render_template('editar_cartao.html', cartao=cartao, instituicoes=instituicoes_list)

@app.route('/cartoes/delete/<int:id>', methods=['POST'])
def delete_cartao(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM cartoes_credito WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('cartoes'))

# --- ROTAS CATEGORIAS ---
@app.route('/categorias', methods=['GET', 'POST'])
def categorias():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('INSERT INTO categorias (descricao, tipo) VALUES (?, ?)', (request.form['descricao'], request.form['tipo']))
            conn.commit()
        except sqlite3.IntegrityError: flash('Essa categoria já existe.', 'error')
        return redirect(url_for('categorias'))
    categorias_list = conn.execute('SELECT * FROM categorias ORDER BY tipo, descricao').fetchall()
    conn.close()
    return render_template('categorias.html', categorias=categorias_list)

@app.route('/categorias/edit/<int:id>', methods=['GET', 'POST'])
def edit_categoria(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('UPDATE categorias SET descricao = ?, tipo = ? WHERE id = ?', (request.form['descricao'], request.form['tipo'], id))
            conn.commit()
            return redirect(url_for('categorias'))
        except sqlite3.IntegrityError: flash('Já existe uma categoria com esse nome.', 'error')
    categoria = conn.execute('SELECT * FROM categorias WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar_categoria.html', categoria=categoria)

@app.route('/categorias/delete/<int:id>', methods=['POST'])
def delete_categoria(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM categorias WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('categorias'))

# --- ROTAS TICKERS ---
@app.route('/tickers', methods=['GET', 'POST'])
def tickers():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('INSERT INTO tickers (descricao, classe, tipo) VALUES (?, ?, ?)', (request.form['descricao'], request.form['classe'], request.form['tipo']))
            conn.commit()
        except sqlite3.IntegrityError: flash('Esse ticker já existe.', 'error')
        return redirect(url_for('tickers'))
    tickers_list = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
    conn.close()
    return render_template('tickers.html', tickers=tickers_list)

@app.route('/tickers/edit/<int:id>', methods=['GET', 'POST'])
def edit_ticker(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('UPDATE tickers SET descricao = ?, classe = ?, tipo = ? WHERE id = ?', (request.form['descricao'], request.form['classe'], request.form['tipo'], id))
            conn.commit()
            return redirect(url_for('tickers'))
        except sqlite3.IntegrityError: flash('Já existe um ticker com essa descrição.', 'error')
    ticker = conn.execute('SELECT * FROM tickers WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar_ticker.html', ticker=ticker)

@app.route('/tickers/delete/<int:id>', methods=['POST'])
def delete_ticker(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM tickers WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('tickers'))

# --- ROTAS MOEDAS ---
@app.route('/moedas', methods=['GET', 'POST'])
def moedas():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('INSERT INTO moedas (codigo, descricao) VALUES (?, ?)', (request.form['codigo'].upper(), request.form['descricao']))
            conn.commit()
        except sqlite3.IntegrityError: flash('Essa moeda já existe.', 'error')
        return redirect(url_for('moedas'))
    moedas_list = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()
    conn.close()
    return render_template('moedas.html', moedas=moedas_list)

@app.route('/moedas/edit/<int:id>', methods=['GET', 'POST'])
def edit_moeda(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('UPDATE moedas SET codigo = ?, descricao = ? WHERE id = ?', (request.form['codigo'].upper(), request.form['descricao'], id))
            conn.commit()
            return redirect(url_for('moedas'))
        except sqlite3.IntegrityError: flash('Já existe uma moeda com esse código.', 'error')
    moeda = conn.execute('SELECT * FROM moedas WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar_moeda.html', moeda=moeda)

@app.route('/moedas/delete/<int:id>', methods=['POST'])
def delete_moeda(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM moedas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('moedas'))

# --- ROTAS OPERAÇÕES ---
@app.route('/operacoes', methods=['GET', 'POST'])
def operacoes():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('INSERT INTO operacoes (descricao, natureza) VALUES (?, ?)', (request.form['descricao'], request.form['natureza']))
            conn.commit()
        except sqlite3.IntegrityError: flash('Essa operação já existe.', 'error')
        return redirect(url_for('operacoes'))
    operacoes_list = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
    conn.close()
    return render_template('operacoes.html', operacoes=operacoes_list)

@app.route('/operacoes/edit/<int:id>', methods=['GET', 'POST'])
def edit_operacao(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            conn.execute('UPDATE operacoes SET descricao = ?, natureza = ? WHERE id = ?', (request.form['descricao'], request.form['natureza'], id))
            conn.commit()
            return redirect(url_for('operacoes'))
        except sqlite3.IntegrityError: flash('Já existe uma operação com essa descrição.', 'error')
    operacao = conn.execute('SELECT * FROM operacoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar_operacao.html', operacao=operacao)

@app.route('/operacoes/delete/<int:id>', methods=['POST'])
def delete_operacao(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM operacoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('operacoes'))

# --- ROTAS MOVIMENTOS ---
@app.route('/movimentos')
def movimentos():
    conn = get_db_connection()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    base_query = '''
        SELECT 
            m.id, strftime('%d/%m/%Y', m.data_movimento) as data_mov_formatada, 
            strftime('%d/%m/%Y', m.data_efetivacao) as data_efet_formatada,
            m.descricao, m.valor, m.status, m.compartilhado,
            c.descricao as categoria_nome, cat.tipo as categoria_tipo,
            i.descricao as instituicao_nome, cc.descricao as cartao_nome
        FROM movimentos m
        JOIN categorias c ON m.categoria_id = c.id
        JOIN categorias cat ON m.categoria_id = cat.id
        JOIN instituicoes i ON m.instituicao_id = i.id
        LEFT JOIN cartoes_credito cc ON m.cartao_id = cc.id'''
    params = []
    where_clauses = []
    if data_inicio:
        where_clauses.append("m.data_movimento >= ?")
        params.append(data_inicio)
    if data_fim:
        where_clauses.append("m.data_movimento <= ?")
        params.append(data_fim)
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    base_query += " ORDER BY m.data_movimento DESC, m.id DESC"
    movimentos_list = conn.execute(base_query, params).fetchall()

    categorias_list = conn.execute('SELECT * FROM categorias ORDER BY descricao').fetchall()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    cartoes_list = conn.execute('SELECT * FROM cartoes_credito ORDER BY descricao').fetchall()
    conn.close()
    return render_template('movimentos.html', movimentos=movimentos_list, categorias=categorias_list,
                           instituicoes=instituicoes_list, cartoes=cartoes_list,
                           data_inicio=data_inicio, data_fim=data_fim)

@app.route('/movimentos/add', methods=['POST'])
def add_movimento():
    conn = get_db_connection()
    data_movimento = request.form['data_movimento']
    data_efetivacao = request.form.get('data_efetivacao') or None
    descricao = request.form['descricao']
    categoria_id = request.form['categoria_id']
    instituicao_id = request.form['instituicao_id']
    cartao_id = request.form.get('cartao_id') or None
    valor = request.form['valor']
    status = request.form['status']
    compartilhado = request.form['compartilhado']

    categoria_tipo = conn.execute('SELECT tipo FROM categorias WHERE id = ?', (categoria_id,)).fetchone()['tipo']
    valor_final = float(valor)
    if categoria_tipo == 'Despesa':
        valor_final = -abs(valor_final)

    conn.execute('INSERT INTO movimentos (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor, status, compartilhado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                 (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor_final, status, compartilhado))
    conn.commit()
    conn.close()
    return redirect(url_for('movimentos'))

@app.route('/movimentos/edit/<int:id>', methods=['GET', 'POST'])
def edit_movimento(id):
    conn = get_db_connection()
    if request.method == 'POST':
        data_movimento = request.form['data_movimento']
        data_efetivacao = request.form.get('data_efetivacao') or None
        descricao = request.form['descricao']
        categoria_id = request.form['categoria_id']
        instituicao_id = request.form['instituicao_id']
        cartao_id = request.form.get('cartao_id') or None
        valor = request.form['valor']
        status = request.form['status']
        compartilhado = request.form['compartilhado']

        categoria_tipo = conn.execute('SELECT tipo FROM categorias WHERE id = ?', (categoria_id,)).fetchone()['tipo']
        valor_final = float(valor)
        if categoria_tipo == 'Despesa':
            valor_final = -abs(valor_final)

        conn.execute('UPDATE movimentos SET data_movimento = ?, data_efetivacao = ?, descricao = ?, categoria_id = ?, instituicao_id = ?, cartao_id = ?, valor = ?, status = ?, compartilhado = ? WHERE id = ?',
                     (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor_final, status, compartilhado, id))
        conn.commit()
        conn.close()
        return redirect(url_for('movimentos'))

    movimento = conn.execute('SELECT * FROM movimentos WHERE id = ?', (id,)).fetchone()
    categorias_list = conn.execute('SELECT * FROM categorias ORDER BY descricao').fetchall()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    cartoes_list = conn.execute('SELECT * FROM cartoes_credito ORDER BY descricao').fetchall()
    conn.close()
    if movimento is None: return redirect(url_for('movimentos'))
    return render_template('editar_movimento.html', movimento=movimento, categorias=categorias_list,
                           instituicoes=instituicoes_list, cartoes=cartoes_list)

@app.route('/movimentos/delete/<int:id>', methods=['POST'])
def delete_movimento(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM movimentos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('movimentos'))

# --- NOVAS ROTAS PARA INVESTIMENTOS ---
@app.route('/investimentos')
def investimentos():
    conn = get_db_connection()

    # Lógica para listar os investimentos
    investimentos_list = conn.execute('''
        SELECT 
            i.id, strftime('%d/%m/%Y', i.data_investimento) as data_inv_formatada,
            strftime('%d/%m/%Y', i.data_vencimento) as data_venc_formatada,
            i.quantidade, i.valor_total,
            t.descricao as ticker_nome, t.classe as ticker_classe, t.tipo as ticker_tipo,
            o.descricao as operacao_nome, o.natureza as operacao_natureza,
            m.codigo as moeda_codigo
        FROM investimentos i
        JOIN tickers t ON i.ticker_id = t.id
        JOIN operacoes o ON i.operacao_id = o.id
        JOIN moedas m ON i.moeda_id = m.id
        ORDER BY i.data_investimento DESC, i.id DESC
    ''').fetchall()

    # Carrega dados para os formulários
    tickers_list = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
    operacoes_list = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
    moedas_list = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()

    conn.close()
    return render_template('investimentos.html',
                           investimentos=investimentos_list,
                           tickers=tickers_list,
                           operacoes=operacoes_list,
                           moedas=moedas_list)

@app.route('/investimentos/add', methods=['POST'])
def add_investimento():
    conn = get_db_connection()
    data_investimento = request.form['data_investimento']
    data_vencimento = request.form.get('data_vencimento') or None
    ticker_id = request.form['ticker_id']
    operacao_id = request.form['operacao_id']
    moeda_id = request.form['moeda_id']
    quantidade = request.form['quantidade']
    valor_total = request.form['valor_total']

    # Lógica do valor: "Saída" (Compra) é negativo, "Entrada" (Venda) é positivo
    operacao_natureza = conn.execute('SELECT natureza FROM operacoes WHERE id = ?', (operacao_id,)).fetchone()['natureza']
    valor_final = float(valor_total)
    if operacao_natureza == 'Saida': # Ex: Compra
        valor_final = -abs(valor_final)
    else: # Ex: Venda, Dividendo
        valor_final = abs(valor_final)

    conn.execute('''
        INSERT INTO investimentos (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, quantidade, valor_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, quantidade, valor_final))
    conn.commit()
    conn.close()
    return redirect(url_for('investimentos'))

@app.route('/investimentos/edit/<int:id>', methods=['GET', 'POST'])
def edit_investimento(id):
    conn = get_db_connection()

    if request.method == 'POST':
        data_investimento = request.form['data_investimento']
        data_vencimento = request.form.get('data_vencimento') or None
        ticker_id = request.form['ticker_id']
        operacao_id = request.form['operacao_id']
        moeda_id = request.form['moeda_id']
        quantidade = request.form['quantidade']
        valor_total = request.form['valor_total']

        operacao_natureza = conn.execute('SELECT natureza FROM operacoes WHERE id = ?', (operacao_id,)).fetchone()['natureza']
        valor_final = float(valor_total)
        if operacao_natureza == 'Saida':
            valor_final = -abs(valor_final)
        else:
            valor_final = abs(valor_final)

        conn.execute('''
            UPDATE investimentos SET
            data_investimento = ?, data_vencimento = ?, ticker_id = ?, operacao_id = ?,
            moeda_id = ?, quantidade = ?, valor_total = ?
            WHERE id = ?
        ''', (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, quantidade, valor_final, id))
        conn.commit()
        conn.close()
        return redirect(url_for('investimentos'))

    # GET: Carregar dados
    investimento = conn.execute('SELECT * FROM investimentos WHERE id = ?', (id,)).fetchone()
    tickers_list = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
    operacoes_list = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
    moedas_list = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()
    conn.close()

    if investimento is None: return redirect(url_for('investimentos'))

    return render_template('editar_investimento.html',
                           investimento=investimento,
                           tickers=tickers_list,
                           operacoes=operacoes_list,
                           moedas=moedas_list)

@app.route('/investimentos/delete/<int:id>', methods=['POST'])
def delete_investimento(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM investimentos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('investimentos'))

if __name__ == '__main__':
    app.run(debug=True)