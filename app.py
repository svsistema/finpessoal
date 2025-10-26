from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3
import pandas as pd
import os
from werkzeug.utils import secure_filename
import math
from datetime import datetime, date, timedelta #timedelta para calcular datas passadas
import io
import json # Para passar dados para o Chart.js

# --- Função para formatar como moeda BRL ---
def format_brl(value):
    if pd.isna(value) or value == 0:
         return "R$ 0,00"
    try:
         float_value = float(value)
         if float_value == 0.0 and math.copysign(1.0, float_value) == -1.0:
             return "R$ 0,00"
         return f"R$ {float_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
         return "Valor Inválido"

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_pode_ser_qualquer_coisa'
DATABASE = 'financas.db'

# --- Registra a função no Jinja ---
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
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index(): return redirect(url_for('dashboard')) # Rota principal vai para o dashboard

# --- ROTAS DE CADASTROS, MOVIMENTOS, INVESTIMENTOS, IMPORTAÇÃO, RELATÓRIOS ---
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
    try:
         cartoes_count = conn.execute('SELECT COUNT(*) FROM cartoes_credito WHERE instituicao_id = ?', (id,)).fetchone()[0]
         mov_count = conn.execute('SELECT COUNT(*) FROM movimentos WHERE instituicao_id = ?', (id,)).fetchone()[0]
         inv_count = conn.execute('SELECT COUNT(*) FROM investimentos WHERE instituicao_id = ?', (id,)).fetchone()[0]
         if cartoes_count > 0 or mov_count > 0 or inv_count > 0:
             flash('Não é possível excluir: Instituição está em uso.', 'error')
         else:
             conn.execute('DELETE FROM instituicoes WHERE id = ?', (id,))
             conn.commit()
             flash('Instituição excluída.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
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
    try:
         mov_count = conn.execute('SELECT COUNT(*) FROM movimentos WHERE cartao_id = ?', (id,)).fetchone()[0]
         if mov_count > 0: flash('Não é possível excluir: Cartão está em uso.', 'error')
         else:
             conn.execute('DELETE FROM cartoes_credito WHERE id = ?', (id,))
             conn.commit(); flash('Cartão excluído.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
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
    try:
        mov_count = conn.execute('SELECT COUNT(*) FROM movimentos WHERE categoria_id = ?', (id,)).fetchone()[0]
        if mov_count > 0 : flash('Não é possível excluir: Categoria está em uso.', 'error')
        else:
            conn.execute('DELETE FROM categorias WHERE id = ?', (id,)); conn.commit()
            flash('Categoria excluída.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
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
    try:
        inv_count = conn.execute('SELECT COUNT(*) FROM investimentos WHERE ticker_id = ?', (id,)).fetchone()[0]
        if inv_count > 0: flash('Não é possível excluir: Ticker está em uso.', 'error')
        else:
            conn.execute('DELETE FROM tickers WHERE id = ?', (id,)); conn.commit()
            flash('Ticker excluído.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
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
    try:
        inv_count = conn.execute('SELECT COUNT(*) FROM investimentos WHERE moeda_id = ?', (id,)).fetchone()[0]
        if inv_count > 0: flash('Não é possível excluir: Moeda está em uso.', 'error')
        else:
            conn.execute('DELETE FROM moedas WHERE id = ?', (id,)); conn.commit()
            flash('Moeda excluída.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
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
    try:
        inv_count = conn.execute('SELECT COUNT(*) FROM investimentos WHERE operacao_id = ?', (id,)).fetchone()[0]
        if inv_count > 0: flash('Não é possível excluir: Operação está em uso.', 'error')
        else:
            conn.execute('DELETE FROM operacoes WHERE id = ?', (id,)); conn.commit()
            flash('Operação excluída.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
    return redirect(url_for('operacoes'))

# --- ROTAS MOVIMENTOS ---
# ... (código existente sem alterações) ...
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
    def reload_edit_page():
        movimento_reload = conn.execute('SELECT * FROM movimentos WHERE id = ?', (id,)).fetchone()
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

    movimento = conn.execute('SELECT * FROM movimentos WHERE id = ?', (id,)).fetchone()
    if not movimento: return redirect(url_for('movimentos'))
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
# ... (código existente com os novos campos, sem alterações) ...
@app.route('/investimentos')
def investimentos():
    conn = get_db_connection()
    investimentos_list = conn.execute('''
        SELECT
            i.*, strftime('%d/%m/%Y', i.data_investimento) as data_inv_formatada,
            strftime('%d/%m/%Y', i.data_vencimento) as data_venc_formatada,
            t.descricao as ticker_nome, o.descricao as operacao_nome,
            o.natureza as operacao_natureza, m.codigo as moeda_codigo,
            inst.descricao as instituicao_nome
        FROM investimentos i
        JOIN tickers t ON i.ticker_id = t.id
        JOIN operacoes o ON i.operacao_id = o.id
        JOIN moedas m ON i.moeda_id = m.id
        LEFT JOIN instituicoes inst ON i.instituicao_id = inst.id
        ORDER BY i.data_investimento DESC, i.id DESC
    ''').fetchall()
    tickers_list = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
    operacoes_list = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
    moedas_list = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    conn.close()
    return render_template('investimentos.html',
                           investimentos=investimentos_list, tickers=tickers_list,
                           operacoes=operacoes_list, moedas=moedas_list,
                           instituicoes=instituicoes_list)

@app.route('/investimentos/add', methods=['POST'])
def add_investimento():
    conn = get_db_connection()
    data_investimento = request.form.get('data_investimento')
    data_vencimento = request.form.get('data_vencimento') or None
    ticker_id = request.form.get('ticker_id')
    operacao_id = request.form.get('operacao_id')
    moeda_id = request.form.get('moeda_id')
    instituicao_id = request.form.get('instituicao_id') or None
    quantidade_str = request.form.get('quantidade')
    valor_unitario_str = request.form.get('valor_unitario')
    valor_total_str = request.form.get('valor_total')
    custos_str = request.form.get('custos', '0')
    taxas_str = request.form.get('taxas', '0')
    irrf_str = request.form.get('irrf', '0')
    taxa_negociada_str = request.form.get('taxa_negociada') or None
    indexador = request.form.get('indexador') or None
    observacao = request.form.get('observacao') or None

    campos_obrigatorios = {'Data': data_investimento, 'Ticker': ticker_id, 'Operação': operacao_id,
                           'Moeda': moeda_id, 'Quantidade': quantidade_str, 'Valor Unitário': valor_unitario_str,
                           'Valor Total': valor_total_str}
    if not all(campos_obrigatorios.values()):
        campos_faltantes = [nome for nome, valor in campos_obrigatorios.items() if not valor]
        flash(f'Campos obrigatórios em falta: {", ".join(campos_faltantes)}', 'error')
        return redirect(url_for('investimentos')) # Simplificado

    try:
        quantidade = float(quantidade_str.replace(',', '.'))
        valor_unitario = float(valor_unitario_str.replace(',', '.'))
        valor_total_bruto = float(valor_total_str.replace(',', '.'))
        custos = float(custos_str.replace(',', '.')) if custos_str else 0.0
        taxas = float(taxas_str.replace(',', '.')) if taxas_str else 0.0
        irrf = float(irrf_str.replace(',', '.')) if irrf_str else 0.0
        taxa_negociada = float(taxa_negociada_str.replace(',', '.')) if taxa_negociada_str else None
    except ValueError:
        flash('Erro ao converter valores numéricos. Use ponto ou vírgula como decimal.', 'error')
        return redirect(url_for('investimentos'))

    operacao_natureza = conn.execute('SELECT natureza FROM operacoes WHERE id = ?', (operacao_id,)).fetchone()['natureza']
    valor_final_liquido = 0.0
    if operacao_natureza == 'Saida': valor_final_liquido = -abs(valor_total_bruto + custos + taxas)
    else: valor_final_liquido = abs(valor_total_bruto - custos - taxas - irrf)

    try:
        conn.execute('''
            INSERT INTO investimentos ( data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, instituicao_id,
                quantidade, valor_unitario, valor_total, custos, taxas, irrf, taxa_negociada, indexador, observacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, instituicao_id, quantidade, valor_unitario,
             valor_final_liquido, custos, taxas, irrf, taxa_negociada, indexador, observacao))
        conn.commit()
    except sqlite3.Error as e: flash(f"Erro DB: {e}", "error")
    finally: conn.close()
    return redirect(url_for('investimentos'))

@app.route('/investimentos/edit/<int:id>', methods=['GET', 'POST'])
def edit_investimento(id):
    conn = get_db_connection()
    def reload_edit_inv_page():
        investimento_reload = conn.execute('SELECT * FROM investimentos WHERE id = ?', (id,)).fetchone()
        if not investimento_reload: return redirect(url_for('investimentos'))
        tickers_list_reload = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
        operacoes_list_reload = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
        moedas_list_reload = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()
        instituicoes_list_reload = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
        return render_template('editar_investimento.html',
                               investimento=investimento_reload, tickers=tickers_list_reload,
                               operacoes=operacoes_list_reload, moedas=moedas_list_reload,
                               instituicoes=instituicoes_list_reload)

    if request.method == 'POST':
        data_investimento = request.form.get('data_investimento')
        data_vencimento = request.form.get('data_vencimento') or None
        ticker_id = request.form.get('ticker_id')
        operacao_id = request.form.get('operacao_id')
        moeda_id = request.form.get('moeda_id')
        instituicao_id = request.form.get('instituicao_id') or None
        quantidade_str = request.form.get('quantidade')
        valor_unitario_str = request.form.get('valor_unitario')
        valor_total_str = request.form.get('valor_total')
        custos_str = request.form.get('custos', '0')
        taxas_str = request.form.get('taxas', '0')
        irrf_str = request.form.get('irrf', '0')
        taxa_negociada_str = request.form.get('taxa_negociada') or None
        indexador = request.form.get('indexador') or None
        observacao = request.form.get('observacao') or None

        campos_obrigatorios = {'Data': data_investimento, 'Ticker': ticker_id, 'Operação': operacao_id,
                               'Moeda': moeda_id, 'Quantidade': quantidade_str, 'Valor Unitário': valor_unitario_str,
                               'Valor Total': valor_total_str}
        if not all(campos_obrigatorios.values()):
            flash(f'Campos obrigatórios em falta.', 'error'); return reload_edit_inv_page()
        try:
            quantidade = float(quantidade_str.replace(',', '.'))
            valor_unitario = float(valor_unitario_str.replace(',', '.'))
            valor_total_bruto = float(valor_total_str.replace(',', '.'))
            custos = float(custos_str.replace(',', '.')) if custos_str else 0.0
            taxas = float(taxas_str.replace(',', '.')) if taxas_str else 0.0
            irrf = float(irrf_str.replace(',', '.')) if irrf_str else 0.0
            taxa_negociada = float(taxa_negociada_str.replace(',', '.')) if taxa_negociada_str else None
        except ValueError: flash('Erro ao converter valores numéricos.', 'error'); return reload_edit_inv_page()

        operacao_natureza = conn.execute('SELECT natureza FROM operacoes WHERE id = ?', (operacao_id,)).fetchone()['natureza']
        valor_final_liquido = 0.0
        if operacao_natureza == 'Saida': valor_final_liquido = -abs(valor_total_bruto + custos + taxas)
        else: valor_final_liquido = abs(valor_total_bruto - custos - taxas - irrf)

        try:
            conn.execute('''
                UPDATE investimentos SET data_investimento = ?, data_vencimento = ?, ticker_id = ?, operacao_id = ?, moeda_id = ?,
                instituicao_id = ?, quantidade = ?, valor_unitario = ?, valor_total = ?, custos = ?, taxas = ?, irrf = ?,
                taxa_negociada = ?, indexador = ?, observacao = ? WHERE id = ?''',
                (data_investimento, data_vencimento, ticker_id, operacao_id, moeda_id, instituicao_id, quantidade, valor_unitario,
                 valor_final_liquido, custos, taxas, irrf, taxa_negociada, indexador, observacao, id))
            conn.commit()
        except sqlite3.Error as e: flash(f"Erro DB: {e}", "error")
        finally: conn.close()
        return redirect(url_for('investimentos'))

    investimento = conn.execute('SELECT * FROM investimentos WHERE id = ?', (id,)).fetchone()
    if not investimento: return redirect(url_for('investimentos'))
    tickers_list = conn.execute('SELECT * FROM tickers ORDER BY descricao').fetchall()
    operacoes_list = conn.execute('SELECT * FROM operacoes ORDER BY descricao').fetchall()
    moedas_list = conn.execute('SELECT * FROM moedas ORDER BY codigo').fetchall()
    instituicoes_list = conn.execute('SELECT * FROM instituicoes ORDER BY descricao').fetchall()
    conn.close()
    return render_template('editar_investimento.html',
                           investimento=investimento, tickers=tickers_list, operacoes=operacoes_list,
                           moedas=moedas_list, instituicoes=instituicoes_list)

@app.route('/investimentos/delete/<int:id>', methods=['POST'])
def delete_investimento(id):
    conn = get_db_connection()
    try:
         conn.execute('DELETE FROM investimentos WHERE id = ?', (id,)); conn.commit()
         flash('Investimento excluído.', 'success')
    except sqlite3.Error as e: flash(f'Erro ao excluir: {e}', 'error')
    finally: conn.close()
    return redirect(url_for('investimentos'))

# --- ROTAS DE IMPORTAÇÃO ---
# ... (código existente sem alterações) ...
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
                data_efetivacao = data_movimento if status == 'Efetivado' else None

                if not all([data_movimento, descricao, categoria_id, instituicao_id, valor_str, status, compartilhado]):
                    flash(f"Linha {i} ignorada: dados em falta.", 'error'); continue
                try: valor = float(valor_str)
                except ValueError: flash(f"Linha {i} ({descricao}) ignorada: valor inválido.", 'error'); continue
                try: categoria_id_int = int(categoria_id)
                except (ValueError, TypeError): flash(f"Linha {i} ({descricao}) ignorada: ID de categoria inválido.", 'error'); continue

                categoria_tipo = categorias_tipos.get(categoria_id_int)
                if not categoria_tipo: flash(f"Linha {i} ({descricao}) ignorada: tipo de categoria não encontrado.", 'error'); continue

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
# ... (código existente sem alterações) ...
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
        if conn: conn.close();
        flash(f"Erro ao buscar dados: {e}", "error")
        return render_template('relatorio_fluxo.html', tables={}, months=[], data_inicio=data_inicio, data_fim=data_fim, filtro_compartilhado=filtro_compartilhado, show_table=False)

    if df_base.empty:
        flash("Nenhum movimento encontrado.", "info")
        return render_template('relatorio_fluxo.html', tables={}, months=[], data_inicio=data_inicio, data_fim=data_fim, filtro_compartilhado=filtro_compartilhado, show_table=False)

    df_fluxo_filtrado = df_base.copy()
    df_banco_filtrado = df_base.copy()
    df_cartao_filtrado = df_base.copy()

    if data_inicio:
        data_inicio_dt = pd.to_datetime(data_inicio)
        df_fluxo_filtrado = df_fluxo_filtrado[df_fluxo_filtrado['data_movimento'] >= data_inicio_dt]
        df_banco_filtrado = df_banco_filtrado[df_banco_filtrado['data_efetivacao'].notna() & (df_banco_filtrado['data_efetivacao'] >= data_inicio_dt)]
        df_cartao_filtrado = df_cartao_filtrado[df_cartao_filtrado['data_efetivacao'].notna() & (df_cartao_filtrado['data_efetivacao'] >= data_inicio_dt)]
    if data_fim:
        data_fim_dt = pd.to_datetime(data_fim)
        df_fluxo_filtrado = df_fluxo_filtrado[df_fluxo_filtrado['data_movimento'] <= data_fim_dt]
        df_banco_filtrado = df_banco_filtrado[df_banco_filtrado['data_efetivacao'].notna() & (df_banco_filtrado['data_efetivacao'] <= data_fim_dt)]
        df_cartao_filtrado = df_cartao_filtrado[df_cartao_filtrado['data_efetivacao'].notna() & (df_cartao_filtrado['data_efetivacao'] <= data_fim_dt)]

    all_months = sorted(df_fluxo_filtrado['data_movimento'].dt.strftime('%Y-%m').unique()) if not df_fluxo_filtrado.empty else []
    all_cols_with_media = all_months + ['Média']

    pivot_fluxo = pd.DataFrame()
    resultado = pd.Series(0, index=all_cols_with_media)
    total_receitas = pd.Series(0, index=all_cols_with_media)
    total_despesas = pd.Series(0, index=all_cols_with_media)

    if not df_fluxo_filtrado.empty:
        df_fluxo_filtrado['MesAno'] = df_fluxo_filtrado['data_movimento'].dt.strftime('%Y-%m')
        pivot_fluxo = pd.pivot_table(df_fluxo_filtrado, values='valor', index=['categoria_tipo', 'categoria'], columns='MesAno', aggfunc='sum', fill_value=0)
        pivot_fluxo = pivot_fluxo.reindex(columns=all_months, fill_value=0)
        if not pivot_fluxo.empty:
            pivot_fluxo['Média'] = pivot_fluxo[all_months].mean(axis=1) if all_months else 0
            total_receitas = pivot_fluxo.loc['Receita'].sum() if 'Receita' in pivot_fluxo.index.get_level_values(0) else pd.Series(0, index=pivot_fluxo.columns)
            total_despesas = pivot_fluxo.loc['Despesa'].sum() if 'Despesa' in pivot_fluxo.index.get_level_values(0) else pd.Series(0, index=pivot_fluxo.columns)
            resultado = total_receitas + total_despesas

    df_banco_final = df_banco_filtrado[(df_banco_filtrado['status'] == 'Efetivado') & (df_banco_filtrado['cartao'].isna()) & (df_banco_filtrado['data_efetivacao'].notna())]
    pivot_banco = pd.DataFrame()
    total_bancos = pd.Series(0, index=all_cols_with_media)

    if not df_banco_final.empty:
        df_banco_final['MesAno'] = df_banco_final['data_efetivacao'].dt.strftime('%Y-%m')
        df_banco_final = df_banco_final[df_banco_final['MesAno'].isin(all_months)]
        pivot_banco = pd.pivot_table(df_banco_final, values='valor', index='instituicao', columns='MesAno', aggfunc='sum', fill_value=0)
        pivot_banco = pivot_banco.reindex(columns=all_months, fill_value=0)
        if not pivot_banco.empty:
            pivot_banco['Média'] = pivot_banco[all_months].mean(axis=1) if all_months else 0
            total_bancos = pivot_banco.sum()

    df_cartao_final = df_cartao_filtrado[df_cartao_filtrado['cartao'].notna() & df_cartao_filtrado['data_efetivacao'].notna()]
    pivot_cartao = pd.DataFrame()
    total_cartoes = pd.Series(0, index=all_cols_with_media)

    if not df_cartao_final.empty:
        df_cartao_final['MesAno'] = df_cartao_final['data_efetivacao'].dt.strftime('%Y-%m')
        df_cartao_final = df_cartao_final[df_cartao_final['MesAno'].isin(all_months)]
        pivot_cartao = pd.pivot_table(df_cartao_final, values='valor', index='cartao', columns='MesAno', aggfunc='sum', fill_value=0).abs()
        pivot_cartao = pivot_cartao.reindex(columns=all_months, fill_value=0)
        if not pivot_cartao.empty:
            pivot_cartao['Média'] = pivot_cartao[all_months].mean(axis=1) if all_months else 0
            total_cartoes = pivot_cartao.sum()

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

    has_months_data = bool(all_months)
    if not has_months_data and (data_inicio or data_fim):
         flash("Nenhum movimento encontrado para o período/filtro.", "info")

    return render_template('relatorio_fluxo.html', tables=tables, months=all_months,
                           data_inicio=data_inicio, data_fim=data_fim,
                           filtro_compartilhado=filtro_compartilhado, show_table=has_months_data)

# --- ROTA RELATÓRIO SALDOS BANCÁRIOS ---
# ... (código existente sem alterações) ...
@app.route('/relatorio/saldos')
def relatorio_saldos():
    conn = get_db_connection()
    data_saldo_str = request.args.get('data_saldo', date.today().strftime('%Y-%m-%d'))
    try: data_saldo = datetime.strptime(data_saldo_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Data inválida.", 'error'); data_saldo = date.today()
        data_saldo_str = data_saldo.strftime('%Y-%m-%d')

    sql = ''' SELECT i.descricao AS instituicao, SUM(m.valor) AS saldo
              FROM movimentos m JOIN instituicoes i ON m.instituicao_id = i.id
              WHERE m.status = 'Efetivado' AND m.cartao_id IS NULL
                AND m.data_efetivacao IS NOT NULL AND date(m.data_efetivacao) <= ?
              GROUP BY i.descricao '''
    params = [data_saldo_str]
    saldos_list = []
    saldo_total = 0.0
    try:
        saldos_calculados = conn.execute(sql, params).fetchall()
        instituicoes_todas = conn.execute("SELECT descricao FROM instituicoes ORDER BY descricao").fetchall()
        conn.close()
        saldos_dict = {s['instituicao']: s['saldo'] for s in saldos_calculados}
        for inst in instituicoes_todas:
             saldo = saldos_dict.get(inst['descricao'], 0.0)
             saldos_list.append({'instituicao': inst['descricao'], 'saldo': saldo})
             saldo_total += saldo
    except Exception as e:
        if conn: conn.close(); flash(f"Erro: {e}", "error")
        saldos_list = []; saldo_total = 0.0

    return render_template('relatorio_saldos.html', saldos=saldos_list,
                           data_saldo=data_saldo_str, saldo_total=saldo_total)

# --- ROTAS PLACEHOLDER para Dashboards e Relatórios Futuros ---
@app.route('/dashboard')
def dashboard():
    # Lógica futura do Dashboard Principal
    # Calculos básicos para o dashboard
    conn = get_db_connection()
    try:
        # 1. Saldo Bancário Atual (simplificado)
        sql_saldo = ''' SELECT SUM(m.valor) AS saldo_total
                       FROM movimentos m
                       WHERE m.status = 'Efetivado' AND m.cartao_id IS NULL AND m.data_efetivacao IS NOT NULL
                         AND date(m.data_efetivacao) <= ? '''
        saldo_bancario_total = conn.execute(sql_saldo, [date.today().strftime('%Y-%m-%d')]).fetchone()['saldo_total'] or 0.0

        # 2. Receita vs Despesa (Últimos 6 meses)
        hoje = date.today()
        seis_meses_atras = (hoje - timedelta(days=180)).strftime('%Y-%m-01') # Primeiro dia, 6 meses atrás aprox.

        sql_receita_despesa = '''
            SELECT strftime('%Y-%m', data_movimento) AS MesAno,
                   SUM(CASE WHEN c.tipo = 'Receita' THEN m.valor ELSE 0 END) as Receita,
                   SUM(CASE WHEN c.tipo = 'Despesa' THEN m.valor ELSE 0 END) as Despesa
            FROM movimentos m JOIN categorias c ON m.categoria_id = c.id
            WHERE data_movimento >= ?
            GROUP BY MesAno ORDER BY MesAno DESC LIMIT 6
        '''
        receita_despesa_data = conn.execute(sql_receita_despesa, [seis_meses_atras]).fetchall()
        # Preparar dados para Chart.js
        labels_rd = [row['MesAno'] for row in receita_despesa_data]
        receitas_rd = [row['Receita'] for row in receita_despesa_data]
        # Despesas são negativas, pegar o valor absoluto
        despesas_rd = [abs(row['Despesa']) for row in receita_despesa_data]

        # 3. Gastos por Categoria (Top 5, Últimos 30 dias)
        trinta_dias_atras = (hoje - timedelta(days=30)).strftime('%Y-%m-%d')
        sql_top_cat = '''
            SELECT c.descricao as Categoria, SUM(ABS(m.valor)) as Total
            FROM movimentos m JOIN categorias c ON m.categoria_id = c.id
            WHERE c.tipo = 'Despesa' AND m.data_movimento >= ?
            GROUP BY Categoria ORDER BY Total DESC LIMIT 5
        '''
        top_categorias_data = conn.execute(sql_top_cat, [trinta_dias_atras]).fetchall()
        labels_cat = [row['Categoria'] for row in top_categorias_data]
        valores_cat = [row['Total'] for row in top_categorias_data]

        # 4. Distribuição Compartilhado (Últimos 30 dias)
        sql_compartilhado = '''
            SELECT compartilhado, SUM(ABS(m.valor)) as Total
            FROM movimentos m JOIN categorias c ON m.categoria_id = c.id
            WHERE c.tipo = 'Despesa' AND m.data_movimento >= ?
            GROUP BY compartilhado ORDER BY Total DESC
        '''
        compartilhado_data = conn.execute(sql_compartilhado, [trinta_dias_atras]).fetchall()
        labels_comp = [row['compartilhado'] for row in compartilhado_data]
        valores_comp = [row['Total'] for row in compartilhado_data]

        conn.close()

        # Passa os dados para o template (convertidos para JSON para JS)
        return render_template('dashboard.html',
                               saldo_bancario_total=saldo_bancario_total,
                               chart_rd_labels=json.dumps(labels_rd),
                               chart_rd_receitas=json.dumps(receitas_rd),
                               chart_rd_despesas=json.dumps(despesas_rd),
                               chart_cat_labels=json.dumps(labels_cat),
                               chart_cat_valores=json.dumps(valores_cat),
                               chart_comp_labels=json.dumps(labels_comp),
                               chart_comp_valores=json.dumps(valores_comp)
                               )

    except Exception as e:
        if conn: conn.close()
        flash(f"Erro ao carregar dados do dashboard: {e}", "error")
        # Renderiza o placeholder em caso de erro grave
        return render_template('placeholder.html', title="Dashboard Principal - Erro")

# ==============================================================================
# CÓDIGO PARA SUBSTITUIR A ROTA dashboard_investimentos NO SEU app.py
# ==============================================================================
# 
# INSTRUÇÕES:
# 1. Abra seu app.py
# 2. Procure por: @app.route('/dashboard/investimentos')
# 3. DELETE a função dashboard_investimentos() atual (placeholder)
# 4. Cole este código no lugar
# 5. Salve
#
# ==============================================================================

@app.route('/dashboard/investimentos')
def dashboard_investimentos():
    conn = get_db_connection()
    
    # ===== 1. BUSCAR TODAS AS OPERAÇÕES DE INVESTIMENTOS =====
    sql_investimentos = '''
        SELECT 
            i.id,
            i.data_investimento,
            i.quantidade,
            i.valor_unitario,
            i.valor_total,
            i.custos,
            i.taxas,
            i.irrf,
            t.descricao as ticker,
            t.classe,
            t.tipo,
            o.descricao as operacao,
            o.natureza,
            m.codigo as moeda
        FROM investimentos i
        JOIN tickers t ON i.ticker_id = t.id
        JOIN operacoes o ON i.operacao_id = o.id
        JOIN moedas m ON i.moeda_id = m.id
        ORDER BY i.data_investimento
    '''
    
    investimentos_raw = conn.execute(sql_investimentos).fetchall()
    
    # ===== 2. CALCULAR POSIÇÃO ATUAL POR ATIVO =====
    # Agrupa por ticker e calcula saldo de quantidade e valor
    posicoes = {}
    
    for inv in investimentos_raw:
        ticker = inv['ticker']
        classe = inv['classe']
        natureza = inv['natureza']
        quantidade = inv['quantidade']
        valor_total = inv['valor_total']
        
        if ticker not in posicoes:
            posicoes[ticker] = {
                'ticker': ticker,
                'classe': classe,
                'quantidade': 0,
                'valor_investido': 0,
                'operacoes': []
            }
        
        # Se é entrada (compra), soma; se é saída (venda), subtrai
        if natureza == 'Entrada':
            posicoes[ticker]['quantidade'] += quantidade
            posicoes[ticker]['valor_investido'] += abs(valor_total)
        else:  # Saida
            posicoes[ticker]['quantidade'] -= quantidade
            posicoes[ticker]['valor_investido'] -= abs(valor_total)
        
        posicoes[ticker]['operacoes'].append(inv)
    
    # Remove ativos com quantidade zero (vendidos completamente)
    posicoes = {k: v for k, v in posicoes.items() if v['quantidade'] > 0}
    
    # ===== 3. CALCULAR KPIs PRINCIPAIS =====
    patrimonio_total = sum(pos['valor_investido'] for pos in posicoes.values())
    num_ativos = len(posicoes)
    
    # SIMULAÇÃO: Para rentabilidade real, você precisaria do preço atual
    # Por enquanto, vamos usar uma simulação baseada em dados históricos
    # Em produção, você conectaria com uma API de cotações
    
    # Simulação de valorização por classe de ativo
    valorizacao_simulada = {
        'Ações': 1.15,  # 15% de valorização
        'FII': 1.10,     # 10% de valorização
        'Renda Fixa': 1.12,  # 12% de valorização
        'Criptomoeda': 1.20  # 20% de valorização
    }
    
    valor_atual_total = 0
    for pos in posicoes.values():
        classe = pos['classe']
        fator = valorizacao_simulada.get(classe, 1.0)
        pos['valor_atual'] = pos['valor_investido'] * fator
        pos['rentabilidade'] = ((pos['valor_atual'] / pos['valor_investido']) - 1) * 100 if pos['valor_investido'] > 0 else 0
        pos['preco_medio'] = pos['valor_investido'] / pos['quantidade'] if pos['quantidade'] > 0 else 0
        valor_atual_total += pos['valor_atual']
    
    rentabilidade_total = ((valor_atual_total / patrimonio_total) - 1) * 100 if patrimonio_total > 0 else 0
    
    # ===== 4. ALOCAÇÃO POR CLASSE =====
    alocacao_por_classe = {}
    for pos in posicoes.values():
        classe = pos['classe']
        if classe not in alocacao_por_classe:
            alocacao_por_classe[classe] = 0
        alocacao_por_classe[classe] += pos['valor_atual']
    
    alocacao_labels = list(alocacao_por_classe.keys())
    alocacao_valores = list(alocacao_por_classe.values())
    
    # ===== 5. TOP 5 ATIVOS POR RENTABILIDADE =====
    lista_posicoes = list(posicoes.values())
    lista_posicoes.sort(key=lambda x: x['rentabilidade'], reverse=True)
    top_5_ativos = lista_posicoes[:5]
    
    top_5_labels = [p['ticker'] for p in top_5_ativos]
    top_5_valores = [p['rentabilidade'] for p in top_5_ativos]
    
    # ===== 6. EVOLUÇÃO DO PATRIMÔNIO (últimos 12 meses) =====
    # Calcula patrimônio acumulado mês a mês
    data_12_meses = (datetime.now() - pd.DateOffset(months=12)).strftime('%Y-%m-%d')
    
    sql_evolucao = '''
        SELECT 
            strftime('%Y-%m', i.data_investimento) as mes,
            SUM(CASE WHEN o.natureza = 'Entrada' THEN i.valor_total ELSE -i.valor_total END) as valor_liquido
        FROM investimentos i
        JOIN operacoes o ON i.operacao_id = o.id
        WHERE i.data_investimento >= ?
        GROUP BY mes
        ORDER BY mes
    '''
    
    df_evolucao = pd.read_sql_query(sql_evolucao, conn, params=[data_12_meses])
    
    if not df_evolucao.empty:
        df_evolucao['acumulado'] = df_evolucao['valor_liquido'].cumsum()
        evolucao_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%y') for m in df_evolucao['mes'].tolist()]
        evolucao_valores = df_evolucao['acumulado'].tolist()
    else:
        evolucao_labels = []
        evolucao_valores = []
    
    # ===== 7. DIVIDENDOS RECEBIDOS =====
    # Busca operações de dividendos (você precisa ter uma operação tipo "Dividendo")
    sql_dividendos = '''
        SELECT 
            strftime('%Y-%m', i.data_investimento) as mes,
            SUM(ABS(i.valor_total)) as total
        FROM investimentos i
        JOIN operacoes o ON i.operacao_id = o.id
        WHERE o.descricao LIKE '%Dividendo%' OR o.descricao LIKE '%Rendimento%'
        AND i.data_investimento >= ?
        GROUP BY mes
        ORDER BY mes
    '''
    
    data_6_meses = (datetime.now() - pd.DateOffset(months=6)).strftime('%Y-%m-%d')
    df_dividendos = pd.read_sql_query(sql_dividendos, conn, params=[data_6_meses])
    
    if not df_dividendos.empty:
        dividendos_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%y') for m in df_dividendos['mes'].tolist()]
        dividendos_valores = df_dividendos['total'].tolist()
        dividendos_total = df_dividendos['total'].sum()
    else:
        dividendos_labels = []
        dividendos_valores = []
        dividendos_total = 0
    
    # ===== 8. MONTAR TABELA DE POSIÇÕES =====
    tabela_posicoes = []
    for pos in lista_posicoes:
        percentual_carteira = (pos['valor_atual'] / valor_atual_total * 100) if valor_atual_total > 0 else 0
        tabela_posicoes.append({
            'ticker': pos['ticker'],
            'classe': pos['classe'],
            'quantidade': f"{pos['quantidade']:.2f}",
            'preco_medio': format_brl(pos['preco_medio']),
            'valor_investido': format_brl(pos['valor_investido']),
            'valor_atual': format_brl(pos['valor_atual']),
            'rentabilidade': f"{pos['rentabilidade']:.1f}%",
            'rentabilidade_num': pos['rentabilidade'],
            'percentual_carteira': f"{percentual_carteira:.1f}%"
        })
    
    conn.close()
    
    # ===== 9. MONTAR DADOS PARA O TEMPLATE =====
    dados = {
        'patrimonio_total': format_brl(patrimonio_total),
        'valor_atual_total': format_brl(valor_atual_total),
        'rentabilidade_total': f"{rentabilidade_total:.1f}%",
        'rentabilidade_total_num': rentabilidade_total,
        'dividendos_total': format_brl(dividendos_total),
        'num_ativos': num_ativos,
        
        # Dados para gráficos
        'alocacao_labels': alocacao_labels,
        'alocacao_valores': alocacao_valores,
        
        'evolucao_labels': evolucao_labels,
        'evolucao_valores': evolucao_valores,
        
        'top_5_labels': top_5_labels,
        'top_5_valores': top_5_valores,
        
        'dividendos_labels': dividendos_labels,
        'dividendos_valores': dividendos_valores,
        
        'tabela_posicoes': tabela_posicoes,
        
        # Benchmarks (você pode atualizar esses valores periodicamente)
        'cdi_12m': 13.65,
        'ipca_12m': 4.51,
        'ibov_12m': 12.8,
        
        # Status vs benchmarks
        'vs_cdi': rentabilidade_total - 13.65,
        'vs_ibov': rentabilidade_total - 12.8
    }
    
    return render_template('dashboard_investimentos.html', **dados)

# ==============================================================================
# CÓDIGO PARA SUBSTITUIR A ROTA relatorio_tendencias NO SEU app.py
# ==============================================================================

@app.route('/relatorio/tendencias')
def relatorio_tendencias():
    conn = get_db_connection()
    
    # Parâmetros de filtro
    periodo_meses = int(request.args.get('periodo', 12))
    compartilhado = request.args.get('compartilhado', 'Todos')
    
    # Filtro de compartilhado
    where_compartilhado = "" if compartilhado == 'Todos' else f"AND m.compartilhado = '{compartilhado}'"
    
    hoje = datetime.now()
    data_inicio = (hoje - pd.DateOffset(months=periodo_meses)).strftime('%Y-%m-%d')
    
    # ===== 1. BUSCAR MOVIMENTOS EFETIVADOS =====
    sql_movimentos = f'''
        SELECT 
            m.data_movimento,
            m.valor,
            c.descricao as categoria,
            c.tipo
        FROM movimentos m
        JOIN categorias c ON m.categoria_id = c.id
        WHERE m.status = 'Efetivado'
        AND m.data_movimento >= ?
        {where_compartilhado}
        ORDER BY m.data_movimento
    '''
    
    df = pd.read_sql_query(sql_movimentos, conn, params=[data_inicio], parse_dates=['data_movimento'])
    conn.close()
    
    if df.empty:
        return render_template('relatorio_tendencias.html',
                             sem_dados=True,
                             periodo=periodo_meses,
                             compartilhado=compartilhado)
    
    # Filtrar apenas despesas para análises
    df_despesas = df[df['tipo'] == 'Despesa'].copy()
    df_despesas['valor'] = df_despesas['valor'].abs()
    df_despesas['mes'] = df_despesas['data_movimento'].dt.to_period('M')
    df_despesas['mes_str'] = df_despesas['data_movimento'].dt.strftime('%Y-%m')
    
    # ===== 2. CALCULAR PREVISÃO PRÓXIMO MÊS =====
    media_mensal = df_despesas.groupby('mes')['valor'].sum().mean()
    desvio_padrao = df_despesas.groupby('mes')['valor'].sum().std()
    
    # Últimos 3 meses têm peso maior
    ultimos_3_meses = df_despesas[df_despesas['data_movimento'] >= (hoje - pd.DateOffset(months=3))]
    media_recente = ultimos_3_meses.groupby('mes')['valor'].sum().mean() if not ultimos_3_meses.empty else media_mensal
    
    # Previsão: 70% peso na média recente, 30% na média geral
    previsao_proximo_mes = (media_recente * 0.7) + (media_mensal * 0.3)
    
    # ===== 3. EVOLUÇÃO POR CATEGORIA (últimos 12 meses) =====
    df_12_meses = df_despesas[df_despesas['data_movimento'] >= (hoje - pd.DateOffset(months=12))]
    
    pivot_categorias = pd.pivot_table(
        df_12_meses,
        values='valor',
        index='categoria',
        columns='mes_str',
        aggfunc='sum',
        fill_value=0
    )
    
    # Ordenar colunas cronologicamente
    pivot_categorias = pivot_categorias.reindex(sorted(pivot_categorias.columns), axis=1)
    
    # Top 4 categorias por valor total
    totais_categoria = pivot_categorias.sum(axis=1).sort_values(ascending=False)
    top_4_categorias = totais_categoria.head(4).index.tolist()
    
    # Preparar dados para gráfico
    evolucao_labels = [datetime.strptime(m, '%Y-%m').strftime('%b/%y') for m in pivot_categorias.columns]
    evolucao_datasets = []
    
    cores = ['#10b981', '#667eea', '#f59e0b', '#ef4444']
    for i, cat in enumerate(top_4_categorias):
        evolucao_datasets.append({
            'label': cat,
            'data': pivot_categorias.loc[cat].tolist(),
            'color': cores[i]
        })
    
    # ===== 4. SAZONALIDADE - GASTOS POR MÊS =====
    gastos_por_mes = df_despesas.groupby('mes')['valor'].sum()
    
    sazonalidade_labels = [m.strftime('%b/%y') for m in gastos_por_mes.index]
    sazonalidade_valores = gastos_por_mes.tolist()
    
    # Identificar mês com maior e menor gasto
    mes_maior_gasto = gastos_por_mes.idxmax().strftime('%B/%Y') if not gastos_por_mes.empty else 'N/A'
    valor_maior_gasto = gastos_por_mes.max() if not gastos_por_mes.empty else 0
    mes_menor_gasto = gastos_por_mes.idxmin().strftime('%B/%Y') if not gastos_por_mes.empty else 'N/A'
    valor_menor_gasto = gastos_por_mes.min() if not gastos_por_mes.empty else 0
    
    # ===== 5. CATEGORIAS QUE CRESCERAM/REDUZIRAM =====
    # Comparar mês atual com média dos últimos 6 meses
    mes_atual = pd.Timestamp(hoje).to_period('M')
    
    # Gastos do mês atual por categoria
    gastos_mes_atual = df_despesas[df_despesas['mes'] == mes_atual].groupby('categoria')['valor'].sum()
    
    # Média dos 6 meses anteriores
    meses_anteriores = df_despesas[
        (df_despesas['mes'] < mes_atual) & 
        (df_despesas['mes'] >= (mes_atual - 6))
    ].groupby('categoria')['valor'].mean()
    
    # Calcular variação
    categorias_variacao = []
    for cat in gastos_mes_atual.index:
        gasto_atual = gastos_mes_atual[cat]
        media_anterior = meses_anteriores.get(cat, gasto_atual)
        
        if media_anterior > 0:
            variacao_pct = ((gasto_atual - media_anterior) / media_anterior) * 100
        else:
            variacao_pct = 100 if gasto_atual > 0 else 0
        
        categorias_variacao.append({
            'categoria': cat,
            'gasto_atual': gasto_atual,
            'variacao': variacao_pct
        })
    
    # Ordenar por variação
    categorias_variacao.sort(key=lambda x: x['variacao'], reverse=True)
    
    top_crescimento = [c for c in categorias_variacao if c['variacao'] > 5][:3]
    top_reducao = [c for c in categorias_variacao if c['variacao'] < -5][-3:]
    top_reducao.reverse()
    
    # ===== 6. COMPARATIVO ANO A ANO =====
    df_despesas['ano'] = df_despesas['data_movimento'].dt.year
    df_despesas['mes_num'] = df_despesas['data_movimento'].dt.month
    
    anos_disponiveis = df_despesas['ano'].unique()
    
    comparativo_datasets = []
    cores_anos = ['#cbd5e1', '#667eea', '#10b981']
    
    for i, ano in enumerate(sorted(anos_disponiveis)):
        df_ano = df_despesas[df_despesas['ano'] == ano]
        gastos_por_mes_ano = df_ano.groupby('mes_num')['valor'].sum()
        
        # Preencher meses faltantes com None
        valores_ano = []
        for mes in range(1, 13):
            if mes in gastos_por_mes_ano.index:
                valores_ano.append(float(gastos_por_mes_ano[mes]))
            else:
                valores_ano.append(None)
        
        comparativo_datasets.append({
            'label': str(ano),
            'data': valores_ano,
            'color': cores_anos[i % len(cores_anos)]
        })
    
    comparativo_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    # ===== 7. ANÁLISE DETALHADA POR CATEGORIA =====
    analise_categorias = []
    
    for cat in totais_categoria.head(5).index:
        gastos_cat = df_despesas[df_despesas['categoria'] == cat]['valor']
        
        media = gastos_cat.mean()
        minimo = gastos_cat.min()
        maximo = gastos_cat.max()
        variacao_pct = ((maximo - minimo) / media * 100) if media > 0 else 0
        
        # Tendência: comparar primeiros 50% com últimos 50%
        meio = len(gastos_cat) // 2
        primeira_metade = gastos_cat.iloc[:meio].mean() if meio > 0 else 0
        segunda_metade = gastos_cat.iloc[meio:].mean() if meio > 0 else 0
        
        if segunda_metade > primeira_metade * 1.1:
            tendencia = 'Subindo'
            tendencia_tipo = 'warning'
        elif segunda_metade < primeira_metade * 0.9:
            tendencia = 'Descendo'
            tendencia_tipo = 'success'
        else:
            tendencia = 'Estável'
            tendencia_tipo = 'success'
        
        # Volatilidade
        if variacao_pct > 50:
            volatilidade = 'Volátil'
            volatilidade_tipo = 'danger'
        elif variacao_pct > 30:
            volatilidade = 'Moderada'
            volatilidade_tipo = 'warning'
        else:
            volatilidade = 'Estável'
            volatilidade_tipo = 'success'
        
        analise_categorias.append({
            'categoria': cat,
            'media': format_brl(media),
            'minimo': format_brl(minimo),
            'maximo': format_brl(maximo),
            'variacao': f"{variacao_pct:.0f}%",
            'tendencia': tendencia,
            'tendencia_tipo': tendencia_tipo,
            'volatilidade': volatilidade,
            'volatilidade_tipo': volatilidade_tipo
        })
    
    # ===== 8. INSIGHTS E RECOMENDAÇÕES =====
    analises = []
    recomendacoes = []
    
    # Análise de sazonalidade
    if len(gastos_por_mes) >= 3:
        analises.append(f"Gastos mais altos: {mes_maior_gasto} ({format_brl(valor_maior_gasto)})")
        analises.append(f"Gastos mais baixos: {mes_menor_gasto} ({format_brl(valor_menor_gasto)})")
        
        diferenca_sazonal = valor_maior_gasto - valor_menor_gasto
        if diferenca_sazonal > media_mensal * 0.3:
            recomendacoes.append(f"Considere criar uma reserva para {mes_maior_gasto.split('/')[0]} ({format_brl(diferenca_sazonal)} a mais que a média)")
    
    # Categoria mais estável
    if analise_categorias:
        cat_estavel = min(analise_categorias, key=lambda x: float(x['variacao'].replace('%', '')))
        analises.append(f"Categoria mais estável: {cat_estavel['categoria']} (variação de apenas {cat_estavel['variacao']})")
    else:
        cat_estavel = {'categoria': '—', 'variacao': '0%'}

    # Categoria mais volátil
    if analise_categorias:
        cat_instavel = max(analise_categorias, key=lambda x: float(x['variacao'].replace('%', '')))
    else:
        cat_instavel = {'categoria': '—', 'variacao': '0%'}

    cat_volatil = cat_instavel

    if float(cat_volatil['variacao'].replace('%', '')) > 40:
        analises.append(f"Categoria mais volátil: {cat_volatil['categoria']} (variação de {cat_volatil['variacao']})")
        recomendacoes.append(f"Categoria '{cat_volatil['categoria']}' precisa de orçamento mais flexível")
    
    # Recomendações gerais
    if desvio_padrao > media_mensal * 0.2:
        recomendacoes.append("Seus gastos variam significativamente. Tente manter uma rotina mais consistente")
    
    if not recomendacoes:
        recomendacoes.append("Seus gastos estão bem controlados. Continue assim!")
    
    # ===== 9. PREPARAR DADOS PARA TEMPLATE =====
    dados = {
        'periodo': periodo_meses,
        'compartilhado': compartilhado,
        'sem_dados': False,
        
        # KPIs
        'previsao_proximo_mes': format_brl(previsao_proximo_mes),
        'media_mensal': format_brl(media_mensal),
        'desvio_padrao': format_brl(desvio_padrao),
        
        # Gráficos
        'evolucao_labels': evolucao_labels,
        'evolucao_datasets': evolucao_datasets,
        
        'sazonalidade_labels': sazonalidade_labels,
        'sazonalidade_valores': sazonalidade_valores,
        
        'comparativo_labels': comparativo_labels,
        'comparativo_datasets': comparativo_datasets,
        
        # Tabelas
        'top_crescimento': [{
            'categoria': c['categoria'],
            'crescimento': f"+{c['variacao']:.0f}%",
            'gasto_atual': format_brl(c['gasto_atual'])
        } for c in top_crescimento],
        
        'top_reducao': [{
            'categoria': c['categoria'],
            'reducao': f"{c['variacao']:.0f}%",
            'gasto_atual': format_brl(c['gasto_atual'])
        } for c in top_reducao],
        
        'analise_categorias': analise_categorias,
        
        # Insights
        'analises': analises,
        'recomendacoes': recomendacoes
    }
    
    return render_template('relatorio_tendencias.html', **dados)

@app.route('/relatorio/cartoes')
def relatorio_cartoes():
    return render_template('relatorio_cartoes.html', title="Análise de Cartões de Crédito")

@app.route('/relatorio/compartilhado')
def relatorio_compartilhado():
    return render_template('placeholder.html', title="Relatório Compartilhado")


if __name__ == '__main__':
    app.run(debug=True)