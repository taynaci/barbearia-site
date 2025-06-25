from flask import Flask, render_template, request, redirect, session
import psycopg2
from urllib.parse import urlparse
import os
import datetime

from functools import wraps

app = Flask(__name__)
app.secret_key = "chave_super_secreta"

HORARIOS_POSSIVEIS = [
    "09:00", "09:30", "10:00", "10:30",
    "11:00", "11:30", "12:00", "12:30",
    "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00"
]

# -------------------
# CONEXÃO COM POSTGRES
# -------------------
def conectar_bd():
    url = os.environ.get("DATABASE_URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://")
    result = urlparse(url)
    return psycopg2.connect(
        dbname=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )

# -------------------
# CRIAÇÃO DAS TABELAS
# -------------------
def criar_tabelas_postgres():
    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            telefone TEXT,
            data TEXT,
            horario TEXT,
            servico TEXT
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bloqueios (
            id SERIAL PRIMARY KEY,
            data TEXT,
            horario TEXT,
            motivo TEXT
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        );
    ''')

    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (username, senha) VALUES (%s, %s)", ('admin', '1234'))

    conn.commit()
    conn.close()

# -------------------
# LOGIN REQUERIDO
# -------------------
def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# -------------------
# ROTAS
# -------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["username"]
        senha = request.form["senha"]

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = %s AND senha = %s", (usuario, senha))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            session["usuario"] = usuario
            return redirect("/agendamentos")
        else:
            return render_template("login.html", erro="Usuário ou senha inválidos")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        data = request.form["data"]
        horario = request.form["horario"]
        servico = request.form["servico"]

        conn = conectar_bd()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM agendamentos WHERE data = %s AND horario = %s", (data, horario))
        agendado = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bloqueios WHERE data = %s AND horario = %s", (data, horario))
        bloqueado = cursor.fetchone()[0]

        if agendado > 0 or bloqueado > 0:
            conn.close()
            return "Horário indisponível. Por favor, escolha outro.", 400

        cursor.execute("INSERT INTO agendamentos (nome, telefone, data, horario, servico) VALUES (%s, %s, %s, %s, %s)",
                       (nome, telefone, data, horario, servico))
        conn.commit()
        conn.close()

        return render_template("confirmacao.html", nome=nome, telefone=telefone, data=data, horario=horario, servico=servico)
    else:
        data_selecionada = request.args.get('data') or datetime.date.today().isoformat()

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT horario FROM agendamentos WHERE data = %s", (data_selecionada,))
        agendados = {row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT horario FROM bloqueios WHERE data = %s", (data_selecionada,))
        bloqueados = {row[0] for row in cursor.fetchall()}
        conn.close()

        horarios_disponiveis = [h for h in HORARIOS_POSSIVEIS if h not in agendados and h not in bloqueados]

        return render_template("agendar.html", data=data_selecionada, horarios=horarios_disponiveis)

@app.route("/agendamentos")
@login_requerido
def listar_agendamentos():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, telefone, data, horario, servico FROM agendamentos ORDER BY data, horario")
    agendamentos = cursor.fetchall()
    conn.close()
    return render_template("agendamentos.html", agendamentos=agendamentos)

@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_requerido
def editar_agendamento(id):
    conn = conectar_bd()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        data = request.form["data"]
        horario = request.form["horario"]
        servico = request.form["servico"]

        cursor.execute('''
            UPDATE agendamentos
            SET nome = %s, telefone = %s, data = %s, horario = %s, servico = %s
            WHERE id = %s
        ''', (nome, telefone, data, horario, servico, id))
        conn.commit()
        conn.close()
        return redirect("/agendamentos")

    cursor.execute("SELECT * FROM agendamentos WHERE id = %s", (id,))
    agendamento = cursor.fetchone()
    conn.close()
    return render_template("editar.html", agendamento=agendamento)

@app.route("/excluir/<int:id>")
@login_requerido
def excluir_agendamento(id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agendamentos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect("/agendamentos")

@app.route("/bloqueios")
@login_requerido
def listar_bloqueios():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, data, horario, motivo FROM bloqueios ORDER BY data, horario")
    bloqueios = cursor.fetchall()
    conn.close()
    return render_template("bloqueios.html", bloqueios=bloqueios)

@app.route("/bloqueios/novo", methods=["GET", "POST"])
@login_requerido
def novo_bloqueio():
    horarios = HORARIOS_POSSIVEIS
    if request.method == "POST":
        data = request.form["data"]
        horario = request.form["horario"]
        motivo = request.form["motivo"]

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bloqueios (data, horario, motivo) VALUES (%s, %s, %s)", (data, horario, motivo))
        conn.commit()
        conn.close()
        return redirect("/bloqueios")

    return render_template("novo_bloqueio.html", horarios=horarios)

@app.route("/bloqueios/excluir/<int:id>")
@login_requerido
def excluir_bloqueio(id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bloqueios WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect("/bloqueios")

# -------------------
# INICIAR SERVIDOR
# -------------------
if __name__ == "__main__":
    criar_tabelas_postgres()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
