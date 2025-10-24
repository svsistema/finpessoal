from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3
import pandas as pd
import os
from werkzeug.utils import secure_filename
import math
from datetime import datetime, date # Adicionado 'date' para a data padrão
import io

# --- Função para formatar como moeda BRL (MOVIDA PARA CIMA) ---
def format_brl(value):
    if pd.isna(value) or value == 0:
         # Retorna 'R$ 0,00' explicitamente para evitar 'R$ -0,00'
         return "R$ 0,00"
    # Garante que seja float antes de formatar
    try:
         float_value = float(value)
         # Trata especificamente -0.0
         if float_value == 0.0 and math.copysign(1.0, float_value) == -1.0:
             return "R$ 0,00"
         return f"R$ {float_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
         return "Valor Inválido"

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_pode_ser_qualquer_coisa'
DATABASE = 'financas.db'

# --- Registra a função no Jinja AGORA que ela está definida ---
app.jinja_env.globals.update(format_brl=format_brl)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index(): return redirect(url_for('movimentos'))

# --- ROTAS DE CADASTROS, MOVIMENTOS, INVESTIMENTOS, IMPORTAÇÃO ---
# (O código de todas essas rotas continua aqui, exatamente como antes)
# --- ROTAS INSTITUIÇÕES ---
@app.route('/instituicoes', methods=['GET', 'POST'])
def instituicoes():
    conn = get_db_connection()
    if request.method == 'POST':
        descricao = request.form.get('descricao')
        if not descricao: flash('Descrição não pode estar vazia.', 'error')
        else:
            try:
                conn.execute('INSERT INTO instituicoes (descricao) VALUES (?)', (descricao,))
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
        descricao = request.form.get('descricao')
        if not descricao: flash('Descrição não pode estar vazia.', 'error')
        else:
            try:
                conn.execute('UPDATE instituicoes SET descricao = ? WHERE id = ?', (descricao, id))
                conn.commit()
                return redirect(url_for('instituicoes'))
            except sqlite3.IntegrityError: flash('Já existe uma instituição com esse nome.', 'error')
    instituicao = conn.execute('SELECT * FROM instituicoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not instituicao: return redirect(url_for('instituicoes'))
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
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall() # Para o form
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
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall() # Para o form
    conn.close()
    if not cartao: return redirect(url_for('cartoes'))
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
        descricao = request.form.get('descricao')
        tipo = request.form.get('tipo')
        if not descricao or not tipo : flash('Descrição e Tipo são obrigatórios.', 'error')
        else:
            try:
                conn.execute('INSERT INTO categorias (descricao, tipo) VALUES (?, ?)', (descricao, tipo))
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
        descricao = request.form.get('descricao')
        tipo = request.form.get('tipo')
        if not descricao or not tipo : flash('Descrição e Tipo são obrigatórios.', 'error')
        else:
            try:
                conn.execute('UPDATE categorias SET descricao = ?, tipo = ? WHERE id = ?', (descricao, tipo, id))
                conn.commit()
                return redirect(url_for('categorias'))
            except sqlite3.IntegrityError: flash('Já existe uma categoria com esse nome.', 'error')
    categoria = conn.execute('SELECT * FROM categorias WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not categoria: return redirect(url_for('categorias'))
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
        descricao = request.form.get('descricao')
        classe = request.form.get('classe')
        tipo = request.form.get('tipo')
        if not descricao or not classe or not tipo: flash('Todos os campos são obrigatórios.', 'error')
        else:
            try:
                conn.execute('INSERT INTO tickers (descricao, classe, tipo) VALUES (?, ?, ?)', (descricao, classe, tipo))
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
        descricao = request.form.get('descricao')
        classe = request.form.get('classe')
        tipo = request.form.get('tipo')
        if not descricao or not classe or not tipo: flash('Todos os campos são obrigatórios.', 'error')
        else:
            try:
                conn.execute('UPDATE tickers SET descricao = ?, classe = ?, tipo = ? WHERE id = ?', (descricao, classe, tipo, id))
                conn.commit()
                return redirect(url_for('tickers'))
            except sqlite3.IntegrityError: flash('Já existe um ticker com essa descrição.', 'error')
    ticker = conn.execute('SELECT * FROM tickers WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not ticker: return redirect(url_for('tickers'))
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
        codigo = request.form.get('codigo', '').upper()
        descricao = request.form.get('descricao')
        if not codigo or not descricao: flash('Código e Descrição são obrigatórios.', 'error')
        elif len(codigo) > 3 : flash('Código deve ter no máximo 3 caracteres.', 'error')
        else:
            try:
                conn.execute('INSERT INTO moedas (codigo, descricao) VALUES (?, ?)', (codigo, descricao))
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
        codigo = request.form.get('codigo', '').upper()
        descricao = request.form.get('descricao')
        if not codigo or not descricao: flash('Código e Descrição são obrigatórios.', 'error')
        elif len(codigo) > 3 : flash('Código deve ter no máximo 3 caracteres.', 'error')
        else:
            try:
                conn.execute('UPDATE moedas SET codigo = ?, descricao = ? WHERE id = ?', (codigo, descricao, id))
                conn.commit()
                return redirect(url_for('moedas'))
            except sqlite3.IntegrityError: flash('Já existe uma moeda com esse código.', 'error')
    moeda = conn.execute('SELECT * FROM moedas WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not moeda: return redirect(url_for('moedas'))
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
        descricao = request.form.get('descricao')
        natureza = request.form.get('natureza')
        if not descricao or not natureza: flash('Descrição e Natureza são obrigatórios.', 'error')
        else:
            try:
                conn.execute('INSERT INTO operacoes (descricao, natureza) VALUES (?, ?)', (descricao, natureza))
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
        descricao = request.form.get('descricao')
        natureza = request.form.get('natureza')
        if not descricao or not natureza: flash('Descrição e Natureza são obrigatórios.', 'error')
        else:
            try:
                conn.execute('UPDATE operacoes SET descricao = ?, natureza = ? WHERE id = ?', (descricao, natureza, id))
                conn.commit()
                return redirect(url_for('operacoes'))
            except sqlite3.IntegrityError: flash('Já existe uma operação com essa descrição.', 'error')
    operacao = conn.execute('SELECT * FROM operacoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not operacao: return redirect(url_for('operacoes'))
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
    if data_inicio: where_clauses.append("m.data_movimento >= ?"); params.append(data_inicio)
    if data_fim: where_clauses.append("m.data_movimento <= ?"); params.append(data_fim)
    if where_clauses: base_query += " WHERE " + " AND ".join(where_clauses)
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
    data_movimento = request.form.get('data_movimento')
    data_efetivacao = request.form.get('data_efetivacao') or None
    descricao = request.form.get('descricao')
    categoria_id = request.form.get('categoria_id')
    instituicao_id = request.form.get('instituicao_id')
    cartao_id = request.form.get('cartao_id') or None
    valor_str = request.form.get('valor')
    status = request.form.get('status')
    compartilhado = request.form.get('compartilhado')

    if not all([data_movimento, descricao, categoria_id, instituicao_id, valor_str, status, compartilhado]):
         flash('Todos os campos marcados são obrigatórios.', 'error'); return redirect(url_for('movimentos'))
    try: valor = float(valor_str)
    except ValueError: flash('Valor inválido.', 'error'); return redirect(url_for('movimentos'))

    categoria_tipo = conn.execute('SELECT tipo FROM categorias WHERE id = ?', (categoria_id,)).fetchone()['tipo']
    valor_final = abs(valor)
    if categoria_tipo == 'Despesa': valor_final = -valor_final
    if status == 'Efetivado' and not data_efetivacao: data_efetivacao = data_movimento

    conn.execute('INSERT INTO movimentos (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor, status, compartilhado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                 (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor_final, status, compartilhado))
    conn.commit()
    conn.close()
    return redirect(url_for('movimentos'))

@app.route('/movimentos/edit/<int:id>', methods=['GET', 'POST'])
def edit_movimento(id):
    conn = get_db_connection()
    # Função interna para recarregar dados da página de edição em caso de erro no POST
    def reload_edit_page():
        movimento_reload = conn.execute('SELECT * FROM movimentos WHERE id = ?', (id,)).fetchone()
        # Verifica se movimento existe antes de buscar o resto
        if not movimento_reload: return redirect(url_for('movimentos'))
        categorias_list_reload = conn.execute('SELECT * FROM categorias ORDER BY descricao').fetchall()
        instituicoes_list_reload = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
        cartoes_list_reload = conn.execute('SELECT * FROM cartoes_credito ORDER BY descricao').fetchall()
        return render_template('editar_movimento.html', movimento=movimento_reload, categorias=categorias_list_reload,
                                instituicoes=instituicoes_list_reload, cartoes=cartoes_list_reload)

    if request.method == 'POST':
        data_movimento = request.form.get('data_movimento')
        data_efetivacao = request.form.get('data_efetivacao') or None
        descricao = request.form.get('descricao')
        categoria_id = request.form.get('categoria_id')
        instituicao_id = request.form.get('instituicao_id')
        cartao_id = request.form.get('cartao_id') or None
        valor_str = request.form.get('valor')
        status = request.form.get('status')
        compartilhado = request.form.get('compartilhado')

        if not all([data_movimento, descricao, categoria_id, instituicao_id, valor_str, status, compartilhado]):
             flash('Todos os campos são obrigatórios.', 'error'); return reload_edit_page()
        try: valor = float(valor_str)
        except ValueError: flash('Valor inválido.', 'error'); return reload_edit_page()

        categoria_tipo = conn.execute('SELECT tipo FROM categorias WHERE id = ?', (categoria_id,)).fetchone()['tipo']
        valor_final = abs(valor)
        if categoria_tipo == 'Despesa': valor_final = -valor_final
        if status == 'Efetivado' and not data_efetivacao: data_efetivacao = data_movimento

        conn.execute('UPDATE movimentos SET data_movimento = ?, data_efetivacao = ?, descricao = ?, categoria_id = ?, instituicao_id = ?, cartao_id = ?, valor = ?, status = ?, compartilhado = ? WHERE id = ?',
                     (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor_final, status, compartilhado, id))
        conn.commit()
        conn.close()
        return redirect(url_for('movimentos'))

    # GET Request
    movimento = conn.execute('SELECT * FROM movimentos WHERE id = ?', (id,)).fetchone()
    if not movimento: return redirect(url_for('movimentos')) # Se o ID não existe
    categorias_list = conn.execute('SELECT * FROM categorias ORDER BY descricao').fetchall()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    cartoes_list = conn.execute('SELECT * FROM cartoes_credito ORDER BY descricao').fetchall()
    conn.close()
    return render_template('editar_movimento.html', movimento=movimento, categorias=categorias_list,
                           instituicoes=instituicoes_list, cartoes=cartoes_list)

@app.route('/movimentos/delete/<int:id>', methods=['POST'])
def delete_movimento(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM movimentos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('movimentos'))

# --- ROTAS INVESTIMENTOS ---
@app.route('/investimentos')
def investimentos():
    conn = get_db_connection()
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

    operacao_natureza = conn.execute('SELECT natureza FROM operacoes WHERE id = ?', (operacao_id,)).fetchone()['natureza']
    valor_final = float(valor_total)
    if operacao_natureza == 'Saida': valor_final = -abs(valor_final)
    else: valor_final = abs(valor_final)

    conn.execute('INSERT INTO investimentos (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, quantidade, valor_total) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, quantidade, valor_final))
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
        if operacao_natureza == 'Saida': valor_final = -abs(valor_final)
        else: valor_final = abs(valor_final)

        conn.execute('UPDATE investimentos SET data_investimento = ?, data_vencimento = ?, ticker_id = ?, operacao_id = ?, moeda_id = ?, quantidade = ?, valor_total = ? WHERE id = ?',
                     (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, quantidade, valor_final, id))
        conn.commit()
        conn.close()
        return redirect(url_for('investimentos'))

    investimento = conn.execute('SELECT * FROM investimentos WHERE id = ?', (id,)).fetchone()
    if not investimento: return redirect(url_for('investimentos'))
    tickers_list = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
    operacoes_list = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
    moedas_list = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()
    conn.close()
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

# --- ROTAS DE IMPORTAÇÃO ---
@app.route('/importar', methods=['GET', 'POST'])
def importar():
    if request.method == 'POST':
        if 'arquivo' not in request.files: flash('Nenhum ficheiro selecionado', 'error'); return redirect(request.url)
        file = request.files['arquivo']
        if file.filename == '': flash('Nenhum ficheiro selecionado', 'error'); return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(filepath)
                return redirect(url_for('validar_importacao', filename=filename))
            except Exception as e: flash(f'Erro ao salvar o ficheiro: {e}', 'error'); return redirect(request.url)
        else: flash('Tipo de ficheiro inválido.', 'error'); return redirect(request.url)
    return render_template('importar.html')

@app.route('/importar/validar/<filename>', methods=['GET'])
def validar_importacao(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath): flash('Ficheiro não encontrado.', 'error'); return redirect(url_for('importar'))

    conn = get_db_connection()
    categorias_db = conn.execute('SELECT id, descricao, tipo FROM categorias').fetchall()
    instituicoes_db = conn.execute('SELECT id, descricao FROM instituicoes').fetchall()
    cartoes_db = conn.execute('SELECT id, descricao FROM cartoes_credito').fetchall()
    conn.close()

    categorias_map = {c['descricao']: (c['id'], c['tipo']) for c in categorias_db}
    instituicoes_map = {i['descricao']: i['id'] for i in instituicoes_db}
    cartoes_map = {c['descricao']: c['id'] for c in cartoes_db}

    try:
        if filename.endswith('.csv'):
            try: df = pd.read_csv(filepath, sep=';', decimal=',')
            except Exception: df = pd.read_csv(filepath, sep=',', decimal='.')
        else: df = pd.read_excel(filepath)

        df.columns = df.columns.str.strip().str.lower()
        df = df.rename(columns={
            'data': 'data', 'descricao': 'descricao', 'descrição': 'descricao', 'descriçao': 'descricao',
            'categoria': 'categoria', 'conta': 'conta', 'cartao': 'cartao', 'cartão': 'cartao',
            'valor': 'valor', 'status': 'status', 'compartilhado': 'compartilhado'
        })

        colunas_obrigatorias = ['data', 'descricao', 'categoria', 'conta', 'valor', 'status', 'compartilhado']
        if not all(col in df.columns for col in colunas_obrigatorias):
            flash(f"Colunas obrigatórias em falta: {colunas_obrigatorias}", 'error'); return redirect(url_for('importar'))

    except Exception as e: flash(f"Erro ao ler o ficheiro: {e}", 'error'); return redirect(url_for('importar'))

    dados_validados = []
    has_errors = False
    for index, row in df.iterrows():
        linha_dados = {}
        erros = []
        data = str(row.get('data', '')).strip()
        try:
            if isinstance(row.get('data'), datetime): data = row.get('data').strftime('%Y-%m-%d')
            else:
                data_obj = pd.to_datetime(data, errors='coerce', dayfirst=True)
                if pd.isna(data_obj): data_obj = pd.to_datetime(data, errors='raise')
                data = data_obj.strftime('%Y-%m-%d')
        except Exception: erros.append(f"Data '{data}' inválida."); has_errors = True

        descricao = str(row.get('descricao', '')).strip()
        categoria_nome = str(row.get('categoria', '')).strip()
        conta_nome = str(row.get('conta', '')).strip()
        cartao_nome = str(row.get('cartao', '')).strip()
        if cartao_nome.lower() == 'nan': cartao_nome = ''

        valor_str = str(row.get('valor', '0')).replace(',', '.').strip()
        status = str(row.get('status', '')).strip().title()
        compartilhado = str(row.get('compartilhado', '')).strip()

        linha_dados['data'] = data
        linha_dados['descricao'] = descricao
        linha_dados['valor'] = valor_str
        linha_dados['status'] = status
        linha_dados['compartilhado'] = compartilhado
        linha_dados['cartao_nome_raw'] = cartao_nome

        if categoria_nome in categorias_map: linha_dados['categoria_id'] = categorias_map[categoria_nome][0]; linha_dados['categoria_nome'] = categoria_nome
        else: erros.append(f"Categoria '{categoria_nome}' ?"); linha_dados['categoria_nome_invalido'] = categoria_nome; has_errors = True

        if conta_nome in instituicoes_map: linha_dados['instituicao_id'] = instituicoes_map[conta_nome]; linha_dados['conta_nome'] = conta_nome
        else: erros.append(f"Conta '{conta_nome}' ?"); linha_dados['conta_nome_invalido'] = conta_nome; has_errors = True

        if cartao_nome:
            if cartao_nome in cartoes_map: linha_dados['cartao_id'] = cartoes_map[cartao_nome]; linha_dados['cartao_nome'] = cartao_nome
            else: erros.append(f"Cartão '{cartao_nome}' ?"); linha_dados['cartao_nome_invalido'] = cartao_nome; has_errors = True

        if status not in ['Pendente', 'Efetivado']: erros.append(f"Status '{status}' ?"); linha_dados['status_invalido'] = status; has_errors = True
        if compartilhado not in ['100% Silvia', '100% Nelson', '50/50']: erros.append(f"Compartilhado '{compartilhado}' ?"); linha_dados['compartilhado_invalido'] = compartilhado; has_errors = True
        try: float(valor_str)
        except ValueError: erros.append(f"Valor '{valor_str}' ?"); has_errors = True

        linha_dados['erros'] = erros
        dados_validados.append(linha_dados)

    return render_template('validar_importacao.html',
                           dados=dados_validados, filename=filename, has_errors=has_errors,
                           categorias_list=categorias_db, instituicoes_list=instituicoes_db, cartoes_list=cartoes_db)

@app.route('/importar/salvar', methods=['POST'])
def salvar_importacao():
    total_rows = int(request.form.get('total_rows', 0))
    if total_rows == 0: flash("Nenhum dado para importar.", 'error'); return redirect(url_for('importar'))
    filename = request.form.get('filename_original') # Recupera o nome do arquivo original

    conn = get_db_connection()
    try:
        count_sucesso = 0
        categorias_tipos = {c['id']: c['tipo'] for c in conn.execute('SELECT id, tipo FROM categorias').fetchall()}

        with conn:
            for i in range(1, total_rows + 1):
                data_movimento = request.form.get(f'data_{i}')
                descricao = request.form.get(f'descricao_{i}')
                categoria_id = request.form.get(f'categoria_id_{i}')
                instituicao_id = request.form.get(f'instituicao_id_{i}')
                cartao_id = request.form.get(f'cartao_id_{i}') or None
                valor_str = request.form.get(f'valor_{i}')
                status = request.form.get(f'status_{i}')
                compartilhado = request.form.get(f'compartilhado_{i}')

                # Define data_efetivacao SOMENTE se status for 'Efetivado', senão NULL
                data_efetivacao = data_movimento if status == 'Efetivado' else None

                if not all([data_movimento, descricao, categoria_id, instituicao_id, valor_str, status, compartilhado]):
                    flash(f"Linha {i} ignorada: dados em falta.", 'error'); continue
                try: valor = float(valor_str)
                except ValueError: flash(f"Linha {i} ({descricao}) ignorada: valor inválido.", 'error'); continue

                # Converte categoria_id para int ANTES de usar no dict
                try:
                     categoria_id_int = int(categoria_id)
                     categoria_tipo = categorias_tipos.get(categoria_id_int)
                except (ValueError, TypeError):
                     categoria_tipo = None # Categoria ID inválido vindo do form?

                if not categoria_tipo: flash(f"Linha {i} ({descricao}) ignorada: tipo de categoria não encontrado para ID {categoria_id}.", 'error'); continue

                valor_final = abs(valor)
                if categoria_tipo == 'Despesa': valor_final = -valor_final

                conn.execute('INSERT INTO movimentos (data_movimento, data_efetivacao, descricao, categoria_id, instituicao_id, cartao_id, valor, status, compartilhado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                             (data_movimento, data_efetivacao, descricao, categoria_id_int, instituicao_id, cartao_id, valor_final, status, compartilhado))
                count_sucesso += 1

        flash(f"{count_sucesso} de {total_rows} movimentos importados com sucesso!", 'success')

    except sqlite3.Error as e: flash(f"Erro DB: {e}. Nenhuma linha salva.", 'error')
    except Exception as e: flash(f"Erro inesperado: {e}", 'error')
    finally:
        if filename:
             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
             if os.path.exists(filepath): os.remove(filepath)
        conn.close()

    return redirect(url_for('movimentos'))

# --- ROTA RELATÓRIO FLUXO ---
@app.route('/relatorio/fluxo')
def relatorio_fluxo():
    conn = get_db_connection()
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    filtro_compartilhado = request.args.get('compartilhado', 'Todos')

    sql = '''
        SELECT 
            m.data_movimento, m.data_efetivacao, m.valor, m.compartilhado, m.status,
            c.descricao AS categoria, c.tipo AS categoria_tipo,
            i.descricao AS instituicao, cc.descricao AS cartao
        FROM movimentos m
        JOIN categorias c ON m.categoria_id = c.id
        JOIN instituicoes i ON m.instituicao_id = i.id
        LEFT JOIN cartoes_credito cc ON m.cartao_id = cc.id
        WHERE 1=1 '''
    params = []
    if filtro_compartilhado != 'Todos': sql += " AND m.compartilhado = ?"; params.append(filtro_compartilhado)

    try:
        df_base = pd.read_sql_query(sql, conn, params=params, parse_dates=['data_movimento'])
        conn.close()
        df_base['data_efetivacao'] = pd.to_datetime(df_base['data_efetivacao'], errors='coerce')
    except Exception as e:
        conn.close(); flash(f"Erro ao buscar dados: {e}", "error")
        return render_template('relatorio_fluxo.html', tables={}, months=[], data_inicio=data_inicio, data_fim=data_fim, filtro_compartilhado=filtro_compartilhado, show_table=False)

    if df_base.empty:
        flash("Nenhum movimento encontrado para o filtro compartilhado.", "info")
        return render_template('relatorio_fluxo.html', tables={}, months=[], data_inicio=data_inicio, data_fim=data_fim, filtro_compartilhado=filtro_compartilhado, show_table=False)

    # Filtro de DATA aplicado DEPOIS
    # Cria cópias filtradas para cada bloco
    df_fluxo_filtrado = df_base.copy()
    df_banco_filtrado = df_base.copy()
    df_cartao_filtrado = df_base.copy()

    if data_inicio: 
        df_fluxo_filtrado = df_fluxo_filtrado[df_fluxo_filtrado['data_movimento'] >= pd.to_datetime(data_inicio)]
        df_banco_filtrado = df_banco_filtrado[df_banco_filtrado['data_efetivacao'] >= pd.to_datetime(data_inicio)]
        df_cartao_filtrado = df_cartao_filtrado[df_cartao_filtrado['data_efetivacao'] >= pd.to_datetime(data_inicio)]
    if data_fim: 
        df_fluxo_filtrado = df_fluxo_filtrado[df_fluxo_filtrado['data_movimento'] <= pd.to_datetime(data_fim)]
        df_banco_filtrado = df_banco_filtrado[df_banco_filtrado['data_efetivacao'] <= pd.to_datetime(data_fim)]
        df_cartao_filtrado = df_cartao_filtrado[df_cartao_filtrado['data_efetivacao'] <= pd.to_datetime(data_fim)]

    # Define os meses baseado na DATA DE MOVIMENTO do DF de fluxo filtrado
    all_months = sorted(df_fluxo_filtrado['data_movimento'].dt.strftime('%Y-%m').unique()) if not df_fluxo_filtrado.empty else []
    all_cols_with_media = all_months + ['Média']

    # --- 1. Fluxo (Receitas/Despesas) ---
    pivot_fluxo = pd.DataFrame()
    resultado = pd.Series(0, index=all_cols_with_media)
    total_receitas = pd.Series(0, index=all_cols_with_media)
    total_despesas = pd.Series(0, index=all_cols_with_media)

    if not df_fluxo_filtrado.empty:
        df_fluxo_filtrado['MesAno'] = df_fluxo_filtrado['data_movimento'].dt.strftime('%Y-%m')
        pivot_fluxo = pd.pivot_table(df_fluxo_filtrado, values='valor', index=['categoria_tipo', 'categoria'], columns='MesAno', aggfunc='sum', fill_value=0)
        pivot_fluxo = pivot_fluxo.reindex(columns=all_months, fill_value=0)
        if not pivot_fluxo.empty:
            pivot_fluxo['Média'] = pivot_fluxo[all_months].mean(axis=1) if all_months else 0 # Evita erro se all_months for vazio
            total_receitas = pivot_fluxo.loc['Receita'].sum() if 'Receita' in pivot_fluxo.index.get_level_values(0) else pd.Series(0, index=pivot_fluxo.columns)
            total_despesas = pivot_fluxo.loc['Despesa'].sum() if 'Despesa' in pivot_fluxo.index.get_level_values(0) else pd.Series(0, index=pivot_fluxo.columns)
            resultado = total_receitas + total_despesas

    # --- 2. Saldos por Banco ---
    df_banco_final = df_banco_filtrado[(df_banco_filtrado['status'] == 'Efetivado') & (df_banco_filtrado['cartao'].isna()) & (df_banco_filtrado['data_efetivacao'].notna())]
    pivot_banco = pd.DataFrame()
    total_bancos = pd.Series(0, index=all_cols_with_media)

    if not df_banco_final.empty:
        df_banco_final['MesAno'] = df_banco_final['data_efetivacao'].dt.strftime('%Y-%m')
        # Filtra novamente pelos meses do cabeçalho
        df_banco_final = df_banco_final[df_banco_final['MesAno'].isin(all_months)] 

        pivot_banco = pd.pivot_table(df_banco_final, values='valor', index='instituicao', columns='MesAno', aggfunc='sum', fill_value=0)
        pivot_banco = pivot_banco.reindex(columns=all_months, fill_value=0)
        if not pivot_banco.empty:
            pivot_banco['Média'] = pivot_banco[all_months].mean(axis=1) if all_months else 0
            total_bancos = pivot_banco.sum()

    # --- 3. Gastos por Cartão ---
    df_cartao_final = df_cartao_filtrado[df_cartao_filtrado['cartao'].notna() & df_cartao_filtrado['data_efetivacao'].notna()]
    pivot_cartao = pd.DataFrame()
    total_cartoes = pd.Series(0, index=all_cols_with_media)

    if not df_cartao_final.empty:
        df_cartao_final['MesAno'] = df_cartao_final['data_efetivacao'].dt.strftime('%Y-%m')
        # Filtra novamente pelos meses do cabeçalho
        df_cartao_final = df_cartao_final[df_cartao_final['MesAno'].isin(all_months)] 

        pivot_cartao = pd.pivot_table(df_cartao_final, values='valor', index='cartao', columns='MesAno', aggfunc='sum', fill_value=0).abs()
        pivot_cartao = pivot_cartao.reindex(columns=all_months, fill_value=0)
        if not pivot_cartao.empty:
            pivot_cartao['Média'] = pivot_cartao[all_months].mean(axis=1) if all_months else 0
            total_cartoes = pivot_cartao.sum()

    # --- Montar Dicionário para Template ---
    def prepare_total_dict(series_data):
        dict_data = series_data.to_dict()
        for col in all_cols_with_media:
            if col not in dict_data: dict_data[col] = 0
        return {key: format_brl(value) for key, value in dict_data.items()}

    tables = {
        'Resultado': prepare_total_dict(resultado),
        'Receitas': pivot_fluxo.loc['Receita'].applymap(format_brl).reset_index().to_dict('records') if not pivot_fluxo.empty and 'Receita' in pivot_fluxo.index.get_level_values(0) else [],
        'Total_Receitas': prepare_total_dict(total_receitas),
        'Despesas': pivot_fluxo.loc['Despesa'].applymap(format_brl).reset_index().to_dict('records') if not pivot_fluxo.empty and 'Despesa' in pivot_fluxo.index.get_level_values(0) else [],
        'Total_Despesas': prepare_total_dict(total_despesas),
        'Saldos_Banco': pivot_banco.applymap(format_brl).reset_index().to_dict('records') if not pivot_banco.empty else [],
        'Total_Saldos_Banco': prepare_total_dict(total_bancos),
        'Gastos_Cartao': pivot_cartao.applymap(format_brl).reset_index().to_dict('records') if not pivot_cartao.empty else [],
        'Total_Gastos_Cartao': prepare_total_dict(total_cartoes)
    }

    # Só mostra a tabela se houver meses (ou seja, se o filtro de fluxo retornou algo)
    show_table = bool(all_months) 
    if not show_table and (data_inicio or data_fim): # Se filtrou mas não achou nada no fluxo
         flash("Nenhum movimento (receita/despesa) encontrado para o período e filtro selecionados.", "info")


    return render_template('relatorio_fluxo.html',
                           tables=tables,
                           months=all_months,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           filtro_compartilhado=filtro_compartilhado,
                           show_table=show_table)

# --- ROTA RELATÓRIO SALDOS BANCÁRIOS ---
@app.route('/relatorio/saldos')
def relatorio_saldos():
    conn = get_db_connection()
    data_saldo_str = request.args.get('data_saldo', date.today().strftime('%Y-%m-%d'))

    try:
        data_saldo = datetime.strptime(data_saldo_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Formato de data inválido. Use AAAA-MM-DD.", 'error')
        data_saldo = date.today()
        data_saldo_str = data_saldo.strftime('%Y-%m-%d')

    sql = '''
        SELECT 
            i.descricao AS instituicao,
            SUM(m.valor) AS saldo
        FROM movimentos m
        JOIN instituicoes i ON m.instituicao_id = i.id
        WHERE 
            m.status = 'Efetivado'
            AND m.cartao_id IS NULL
            AND m.data_efetivacao IS NOT NULL 
            AND date(m.data_efetivacao) <= ? -- Usa date() para comparar apenas a data
        GROUP BY i.descricao
        ORDER BY i.descricao
    '''
    params = [data_saldo_str]

    try:
        saldos = conn.execute(sql, params).fetchall()
        # Adiciona instituições com saldo zero
        instituicoes_todas = conn.execute("SELECT descricao FROM instituicoes").fetchall()
        instituicoes_com_saldo = {s['instituicao'] for s in saldos}
        saldos_list = [dict(s) for s in saldos] # Converte para lista de dicionários mutáveis
        for inst in instituicoes_todas:
             if inst['descricao'] not in instituicoes_com_saldo:
                 saldos_list.append({'instituicao': inst['descricao'], 'saldo': 0})
        # Reordena alfabeticamente
        saldos_list.sort(key=lambda x: x['instituicao'])

        conn.close()
    except Exception as e:
        conn.close()
        flash(f"Erro ao calcular saldos: {e}", "error")
        saldos_list = []

    saldo_total = sum(s['saldo'] for s in saldos_list) if saldos_list else 0

    return render_template('relatorio_saldos.html', 
                           saldos=saldos_list, 
                           data_saldo=data_saldo_str,
                           saldo_total=saldo_total)

if __name__ == '__main__':
    app.run(debug=True)