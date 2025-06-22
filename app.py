from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# Banco de dados
def criar_banco():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            data TEXT,
            horario TEXT,
            servico TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/agendar", methods=["GET", "POST"])
def agendar():
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        data = request.form["data"]
        horario = request.form["horario"]
        servico = request.form["servico"]

        conn = sqlite3.connect('banco.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agendamentos (nome, telefone, data, horario, servico) VALUES (?, ?, ?, ?, ?)",
                       (nome, telefone, data, horario, servico))
        conn.commit()
        conn.close()
        return redirect("/agendamentos")  # redireciona para a lista

    return render_template("agendar.html")

@app.route("/agendamentos")
def listar_agendamentos():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, telefone, data, horario, servico FROM agendamentos ORDER BY data, horario")
    agendamentos = cursor.fetchall()
    conn.close()
    return render_template("agendamentos.html", agendamentos=agendamentos)

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_agendamento(id):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        data = request.form["data"]
        horario = request.form["horario"]
        servico = request.form["servico"]

        cursor.execute('''
            UPDATE agendamentos
            SET nome = ?, telefone = ?, data = ?, horario = ?, servico = ?
            WHERE id = ?
        ''', (nome, telefone, data, horario, servico, id))
        conn.commit()
        conn.close()
        return redirect("/agendamentos")

    cursor.execute("SELECT * FROM agendamentos WHERE id = ?", (id,))
    agendamento = cursor.fetchone()
    conn.close()
    return render_template("editar.html", agendamento=agendamento)

@app.route("/excluir/<int:id>")
def excluir_agendamento(id):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agendamentos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/agendamentos")

# Inicialização do app
if __name__ == "__main__":
    criar_banco()
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
