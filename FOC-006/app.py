from flask import Flask, render_template_string, request, redirect, session, url_for, send_file, flash
import hashlib
import json
import os
from datetime import date, datetime
import io
import csv
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "SUA_CHAVE_SECRETA"
DATA_FILE = "foc006_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Garante que todas as listas existam
        if "problems" not in data:
            data["problems"] = []
        if "suppliers" not in data:
            data["suppliers"] = []
        if "notifications" not in data:
            data["notifications"] = []
        if "users" not in data:
            data["users"] = [
                {"username": "admin", "name": "Administrador", "password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"}
            ]
        return data
    else:
        return {
            "users": [
                {"username": "admin", "name": "Administrador", "password": hashlib.sha256("admin123".encode()).hexdigest(), "role": "admin"}
            ],
            "problems": [],
            "suppliers": [],
            "notifications": []
        }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

DARK_STYLE = """
<style>
body { background: #181b1f; color: #e6e6e6; font-family: Arial, sans-serif; margin: 0; }
.header { background: #23232b; padding: 20px 0 10px 0; text-align: center; font-size: 2em; font-weight: bold; color: #fff; letter-spacing: 1px; }
.tabs { display: flex; background: #23232b; border-bottom: 2px solid #444; flex-wrap: wrap;}
.tab { padding: 16px 32px; color: #fff; font-size: 1.2em; cursor: pointer; border: none; background: none; outline: none; }
.tab.active, .tab:hover { background: #282c34; color: #6c63ff; border-bottom: 4px solid #6c63ff; }
.container { max-width: 1100px; margin: 40px auto; background: #23232b; border-radius: 12px; box-shadow: 0 0 20px #111; padding: 32px; }
input, select, textarea { background: #181b1f; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 8px; margin: 4px 0 12px 0; font-size: 1em; }
button { background: #6c63ff; color: #fff; border: none; border-radius: 6px; padding: 10px 24px; font-size: 1em; font-weight: bold; cursor: pointer; margin-top: 10px; }
button:hover { background: #5146d8; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th, td { border: 1px solid #444; padding: 10px; text-align: center; }
th { background: #282c34; color: #6c63ff; font-size: 1.1em; }
a { color: #6c63ff; text-decoration: none; }
a:hover { text-decoration: underline; }
::-webkit-scrollbar { width: 8px; background: #23232b; }
::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
.success { color: #90ee90; font-weight: bold; }
.error { color: #ff5252; font-weight: bold; }
@media (max-width: 900px) {
    .container { padding: 8px; }
    .tab { padding: 8px 8px; font-size: 1em;}
    th, td { font-size: 0.9em; padding: 4px;}
}
</style>
"""

def render_with_tabs(user, active_tab, content):
    tabs = [
        ("dashboard", "Dashboard"),
        ("new_problem", "Novo Problema"),
        ("problems", "Lista de Problemas"),
        ("suppliers", "Fornecedores"),
        ("charts", "Gráficos"),
        ("notifications", "Notificações"),
        ("report", "Relatórios"),
    ]
    if user["role"] == "admin":
        tabs.append(("permissions", "Permissões"))
    tab_html = ''.join(
        f'<a href="{url_for(tab[0])}"><button class="tab{" active" if active_tab==tab[0] else ""}">{tab[1]}</button></a>'
        for tab in tabs
    )
    flashes = ""
    for msg in list(get_flashed_messages(with_categories=True)):
        flashes += f"<div class='{msg[0]}'>{msg[1]}</div>"
    return render_template_string(DARK_STYLE + f"""
    <div class="header">FOC006 - Sistema de Gerenciamento de Problemas</div>
    <div class="tabs">{tab_html}<a href="{{{{ url_for('logout') }}}}" style="margin-left:auto;"><button class="tab">Sair</button></a></div>
    <div class="container">{flashes}{content}</div>
    """, user=user)

from flask import get_flashed_messages

@app.route("/", methods=["GET", "POST"])
def login():
    data = load_data()
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        for user in data["users"]:
            if user["username"] == username and user["password"] == password:
                session["user"] = username
                return redirect(url_for("dashboard"))
        flash("Login inválido", "error")
    return DARK_STYLE + """
        <div class="header">FOC006 - Sistema de Gerenciamento de Problemas</div>
        <div class="container" style="max-width:400px;">
        <h2>Login</h2>
        <form method="post">
            Usuário:<br><input name="username"><br>
            Senha:<br><input name="password" type="password"><br>
            <button type="submit">Entrar</button>
        </form>
        <a href="{{ url_for('register') }}">Criar Conta</a>
        </div>
    """

@app.route("/register", methods=["GET", "POST"])
def register():
    data = load_data()
    if request.method == "POST":
        username = request.form["username"]
        name = request.form["name"]
        password = request.form["password"]
        confirm = request.form["confirm"]
        if not username or not name or not password:
            flash("Preencha todos os campos!", "error")
        elif password != confirm:
            flash("Senhas não coincidem!", "error")
        elif any(u["username"] == username for u in data["users"]):
            flash("Usuário já existe!", "error")
        else:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            data["users"].append({"username": username, "name": name, "password": hashed, "role": "comum"})
            save_data(data)
            flash("Conta criada com sucesso!", "success")
            return redirect(url_for("login"))
    return DARK_STYLE + """
        <div class="header">FOC006 - Sistema de Gerenciamento de Problemas</div>
        <div class="container" style="max-width:400px;">
        <h2>Registrar</h2>
        <form method="post">
            Usuário:<br><input name="username"><br>
            Nome:<br><input name="name"><br>
            Senha:<br><input name="password" type="password"><br>
            Confirmar:<br><input name="confirm" type="password"><br>
            <button type="submit">Registrar</button>
        </form>
        <a href="{{ url_for('login') }}">Voltar</a>
        </div>
    """

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    content = f"""
        <h2>Dashboard</h2>
        <b>Total de problemas registrados:</b> {len(data['problems'])}<br>
        <b>Total de fornecedores:</b> {len(data.get('suppliers', []))}<br>
        <b>Total de notificações:</b> {len(data.get('notifications', []))}<br>
    """
    return render_with_tabs(user, "dashboard", content)

@app.route("/problems", methods=["GET", "POST"])
def problems():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    filtro = request.form.get("filtro", "") if request.method == "POST" else ""
    problemas = data["problems"]
    if filtro:
        problemas = [p for p in problemas if filtro.lower() in p.get("description", "").lower()]
    table = """
        <h2>Lista de Problemas</h2>
        <form method="post" style="margin-bottom:10px;">
            <input name="filtro" placeholder="Buscar descrição..." value="{0}">
            <button type="submit">Buscar</button>
            <a href="{1}"><button type="button">Limpar</button></a>
        </form>
        <table>
            <tr><th>Tipo</th><th>Descrição</th><th>Data</th><th>Status</th><th>Prioridade</th><th>Responsável</th><th>Fornecedor</th><th>Relatório</th><th>Ações</th></tr>
    """.format(filtro, url_for("problems"))
    for idx, p in enumerate(problemas):
        table += f"<tr><td>{p.get('type','')}</td><td>{p.get('description','')}</td><td>{p.get('date','')}</td><td>{p.get('status','')}</td><td>{p.get('priority','')}</td><td>{p.get('responsible','')}</td><td>{p.get('supplier','')}</td>"
        table += f"<td><a href='{url_for('edit_report', idx=idx)}'>Ver/Editar</a></td>"
        table += f"<td><a href='{url_for('edit_problem', idx=idx)}'>Editar</a> | <a href='{url_for('delete_problem', idx=idx)}' onclick=\"return confirm('Tem certeza que deseja excluir?');\">Excluir</a></td></tr>"
    table += "</table>"
    return render_with_tabs(user, "problems", table)

@app.route("/new_problem", methods=["GET", "POST"])
def new_problem():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    if request.method == "POST":
        p = {
            "type": request.form["type"],
            "description": request.form["description"],
            "date": request.form["date"],
            "status": request.form["status"],
            "priority": request.form["priority"],
            "responsible": request.form["responsible"],
            "supplier": request.form.get("supplier", ""),
            "report": "",
            "report_signature": ""
        }
        data["problems"].append(p)
        save_data(data)
        flash("Problema cadastrado!", "success")
        return redirect(url_for("problems"))
    content = f"""
        <h2>Novo Problema</h2>
        <form method="post">
            Tipo:<br>
            <select name="type" id="type" onchange="document.getElementById('supplier').style.display = this.value=='Fornecedor'?'':'none';">
                <option>Fábrica/Linha</option>
                <option>Fornecedor</option>
            </select><br>
            <div id="supplier" style="display:none;">
                Fornecedor:<br><input name="supplier"><br>
            </div>
            Descrição:<br><input name="description"><br>
            Data:<br><input name="date" type="date" value="{date.today().isoformat()}"><br>
            Status:<br>
            <select name="status">
                <option>Em Aberto</option>
                <option>Em Análise</option>
                <option>Resolvido</option>
                <option>Cancelado</option>
            </select><br>
            Prioridade:<br>
            <select name="priority">
                <option>Baixa</option>
                <option>Média</option>
                <option>Alta</option>
                <option>Crítica</option>
            </select><br>
            Responsável:<br><input name="responsible"><br>
            <button type="submit">Salvar</button>
        </form>
        <script>
        document.getElementById('type').dispatchEvent(new Event('change'));
        </script>
    """
    return render_with_tabs(user, "new_problem", content)

@app.route("/edit_problem/<int:idx>", methods=["GET", "POST"])
def edit_problem(idx):
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    if idx < 0 or idx >= len(data["problems"]):
        flash("Problema não encontrado!", "error")
        return redirect(url_for("problems"))
    p = data["problems"][idx]
    if request.method == "POST":
        p["type"] = request.form["type"]
        p["description"] = request.form["description"]
        p["date"] = request.form["date"]
        p["status"] = request.form["status"]
        p["priority"] = request.form["priority"]
        p["responsible"] = request.form["responsible"]
        p["supplier"] = request.form.get("supplier", "")
        save_data(data)
        flash("Problema editado!", "success")
        return redirect(url_for("problems"))
    content = f"""
        <h2>Editar Problema</h2>
        <form method="post">
            Tipo:<br>
            <select name="type" id="type" onchange="document.getElementById('supplier').style.display = this.value=='Fornecedor'?'':'none';">
                <option {'selected' if p['type']=='Fábrica/Linha' else ''}>Fábrica/Linha</option>
                <option {'selected' if p['type']=='Fornecedor' else ''}>Fornecedor</option>
            </select><br>
            <div id="supplier" style="display:{'block' if p['type']=='Fornecedor' else 'none'};">
                Fornecedor:<br><input name="supplier" value="{p.get('supplier','')}"><br>
            </div>
            Descrição:<br><input name="description" value="{p.get('description','')}"><br>
            Data:<br><input name="date" type="date" value="{p.get('date','')}"><br>
            Status:<br>
            <select name="status">
                <option {'selected' if p['status']=='Em Aberto' else ''}>Em Aberto</option>
                <option {'selected' if p['status']=='Em Análise' else ''}>Em Análise</option>
                <option {'selected' if p['status']=='Resolvido' else ''}>Resolvido</option>
                <option {'selected' if p['status']=='Cancelado' else ''}>Cancelado</option>
            </select><br>
            Prioridade:<br>
            <select name="priority">
                <option {'selected' if p['priority']=='Baixa' else ''}>Baixa</option>
                <option {'selected' if p['priority']=='Média' else ''}>Média</option>
                <option {'selected' if p['priority']=='Alta' else ''}>Alta</option>
                <option {'selected' if p['priority']=='Crítica' else ''}>Crítica</option>
            </select><br>
            Responsável:<br><input name="responsible" value="{p.get('responsible','')}"><br>
            <button type="submit">Salvar</button>
        </form>
        <script>
        document.getElementById('type').dispatchEvent(new Event('change'));
        </script>
    """
    user = next(u for u in data["users"] if u["username"] == session["user"])
    return render_with_tabs(user, "problems", content)

@app.route("/delete_problem/<int:idx>")
def delete_problem(idx):
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    if 0 <= idx < len(data["problems"]):
        del data["problems"][idx]
        save_data(data)
        flash("Problema excluído!", "success")
    else:
        flash("Problema não encontrado!", "error")
    return redirect(url_for("problems"))

@app.route("/edit_report/<int:idx>", methods=["GET", "POST"])
def edit_report(idx):
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    if idx < 0 or idx >= len(data["problems"]):
        flash("Problema não encontrado!", "error")
        return redirect(url_for("problems"))
    problem = data["problems"][idx]
    msg = ""
    if request.method == "POST":
        texto = request.form["report"]
        problem["report"] = texto
        problem["report_signature"] = f"Assinado por {user['name']} em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        save_data(data)
        msg = "<b>Relatório salvo e assinado!</b>"
    content = f"""
        <h2>Relatório do Problema</h2>
        <form method="post">
            <textarea name="report" rows="8" style="width:100%;">{problem.get('report','')}</textarea><br>
            <button type="submit">Finalizar Relatório</button>
        </form>
        <div style="margin-top:20px;color:#ffd54f;">{problem.get('report_signature','')}</div>
        <a href="{url_for('problems')}">Voltar</a>
        {msg}
    """
    return render_with_tabs(user, "problems", content)

@app.route("/suppliers", methods=["GET", "POST"])
def suppliers():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    if request.method == "POST":
        if "add" in request.form:
            supplier = request.form["supplier"]
            if supplier and supplier not in data["suppliers"]:
                data["suppliers"].append(supplier)
                save_data(data)
                flash("Fornecedor adicionado!", "success")
        elif "edit" in request.form:
            idx = int(request.form["idx"])
            new_name = request.form["new_name"]
            if new_name and 0 <= idx < len(data["suppliers"]):
                data["suppliers"][idx] = new_name
                save_data(data)
                flash("Fornecedor editado!", "success")
        elif "delete" in request.form:
            idx = int(request.form["idx"])
            if 0 <= idx < len(data["suppliers"]):
                del data["suppliers"][idx]
                save_data(data)
                flash("Fornecedor excluído!", "success")
        return redirect(url_for("suppliers"))
    content = """
        <h2>Lista de Fornecedores</h2>
        <table id="suppliers_table"><tr><th>Nome</th><th>Ações</th></tr>
    """
    for idx, s in enumerate(data.get("suppliers", [])):
        content += f"<tr data-supplier='{s}'><td>{s}</td><td>"
        content += f"""
        <form method="post" style="display:inline;">
            <input type="hidden" name="idx" value="{idx}">
            <input name="new_name" value="{s}" style="width:120px;">
            <button name="edit" type="submit">Editar</button>
        </form>
        <form method="post" style="display:inline;" onsubmit="return confirm('Excluir fornecedor?');">
            <input type="hidden" name="idx" value="{idx}">
            <button name="delete" type="submit">Excluir</button>
        </form>
        """
        content += "</td></tr>"
    content += "</table>"
    content += """
        <form method="post" style="margin-top:20px;">
            <input name="supplier" placeholder="Novo fornecedor">
            <button name="add" type="submit">Adicionar</button>
        </form>
        <script>
        document.querySelectorAll("#suppliers_table tr[data-supplier]").forEach(function(row){
            row.ondblclick = function(){
                var supplier = encodeURIComponent(this.getAttribute("data-supplier"));
                window.location = "/supplier_charts/" + supplier;
            }
        });
        </script>
    """
    return render_with_tabs(user, "suppliers", content)

@app.route("/charts")
def charts():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    status_labels = ["Em Aberto", "Em Análise", "Resolvido", "Cancelado"]
    status_counts = [sum(1 for p in data["problems"] if p.get("status") == s) for s in status_labels]
    priority_labels = ["Baixa", "Média", "Alta", "Crítica"]
    priority_counts = [sum(1 for p in data["problems"] if p.get("priority") == s) for s in priority_labels]
    # Top 5 fornecedores
    fornecedores_dict = {}
    for p in data["problems"]:
        f = p.get("supplier", "")
        if f:
            fornecedores_dict[f] = fornecedores_dict.get(f, 0) + 1
    top5 = sorted(fornecedores_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    fornecedores = [x[0] for x in top5]
    forn_counts = [x[1] for x in top5]
    content = f"""
        <h2>Gráficos</h2>
        <div id="status_chart" style="width:100%;height:350px;"></div>
        <div id="priority_chart" style="width:100%;height:350px;"></div>
        <div id="forn_chart" style="width:100%;height:350px;"></div>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script>
        Plotly.newPlot('status_chart', [{{
            x: {status_labels},
            y: {status_counts},
            type: 'bar',
            marker: {{color: '#6c63ff'}},
        }}], {{
            title: 'Problemas por Status',
            plot_bgcolor: '#23232b',
            paper_bgcolor: '#23232b',
            font: {{color: '#fff'}}
        }});
        Plotly.newPlot('priority_chart', [{{
            labels: {priority_labels},
            values: {priority_counts},
            type: 'pie',
            marker: {{colors: ['#90caf9','#ffd54f','#ff7043','#ff5252']}},
        }}], {{
            title: 'Problemas por Prioridade',
            plot_bgcolor: '#23232b',
            paper_bgcolor: '#23232b',
            font: {{color: '#fff'}}
        }});
        Plotly.newPlot('forn_chart', [{{
            x: {fornecedores},
            y: {forn_counts},
            type: 'bar',
            marker: {{color: '#ffd54f'}},
        }}], {{
            title: 'Top 5 Fornecedores com Mais Problemas',
            plot_bgcolor: '#23232b',
            paper_bgcolor: '#23232b',
            font: {{color: '#fff'}}
        }});
        </script>
    """
    return render_with_tabs(user, "charts", content)

@app.route("/supplier_charts/<supplier>")
def supplier_charts(supplier):
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    problems = [p for p in data["problems"] if p.get("supplier", "") == supplier]
    status_labels = ["Em Aberto", "Em Análise", "Resolvido", "Cancelado"]
    status_counts = [sum(1 for p in problems if p.get("status") == s) for s in status_labels]
    priority_labels = ["Baixa", "Média", "Alta", "Crítica"]
    priority_counts = [sum(1 for p in problems if p.get("priority") == s) for s in priority_labels]
    content = f"""
        <h2>Gráficos do Fornecedor: {supplier}</h2>
        <div id="status_chart" style="width:100%;height:350px;"></div>
        <div id="priority_chart" style="width:100%;height:350px;"></div>
        <a href="{url_for('suppliers')}"><button>Voltar</button></a>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script>
        Plotly.newPlot('status_chart', [{{
            x: {status_labels},
            y: {status_counts},
            type: 'bar',
            marker: {{color: '#6c63ff'}},
        }}], {{
            title: 'Problemas por Status',
            plot_bgcolor: '#23232b',
            paper_bgcolor: '#23232b',
            font: {{color: '#fff'}}
        }});
        Plotly.newPlot('priority_chart', [{{
            labels: {priority_labels},
            values: {priority_counts},
            type: 'pie',
            marker: {{colors: ['#90caf9','#ffd54f','#ff7043','#ff5252']}},
        }}], {{
            title: 'Problemas por Prioridade',
            plot_bgcolor: '#23232b',
            paper_bgcolor: '#23232b',
            font: {{color: '#fff'}}
        }});
        </script>
    """
    return render_with_tabs(user, "suppliers", content)

@app.route("/notifications", methods=["GET", "POST"])
def notifications():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    if request.method == "POST":
        notif = request.form["notification"]
        if notif:
            data["notifications"].append(f"{user['name']}: {notif} ({datetime.now().strftime('%d/%m/%Y %H:%M')})")
            save_data(data)
            flash("Notificação enviada!", "success")
        return redirect(url_for("notifications"))
    content = "<h2>Notificações</h2><ul>"
    for n in reversed(data.get("notifications", [])):
        content += f"<li>{n}</li>"
    content += "</ul>"
    content += """
        <form method="post" style="margin-top:20px;">
            <input name="notification" placeholder="Nova notificação" style="width:70%;">
            <button type="submit">Enviar</button>
        </form>
    """
    return render_with_tabs(user, "notifications", content)

@app.route("/report")
def report():
    if "user" not in session:
        return redirect(url_for("login"))
    user = next(u for u in load_data()["users"] if u["username"] == session["user"])
    content = """
        <h2>Relatórios</h2>
        <a href="/download_report_csv"><button>Baixar CSV</button></a>
        <a href="/download_report_pdf"><button>Baixar PDF</button></a>
        <p>O relatório contém todos os problemas cadastrados.</p>
    """
    return render_with_tabs(user, "report", content)

@app.route("/download_report_csv")
def download_report_csv():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tipo", "Descrição", "Data", "Status", "Prioridade", "Responsável", "Fornecedor", "Relatório", "Assinatura"])
    for p in data["problems"]:
        writer.writerow([
            p.get("type",""), p.get("description",""), p.get("date",""), p.get("status",""),
            p.get("priority",""), p.get("responsible",""), p.get("supplier",""),
            p.get("report",""), p.get("report_signature","")
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype="text/csv", as_attachment=True, download_name="relatorio_problemas.csv")

@app.route("/download_report_pdf")
def download_report_pdf():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Relatório de Problemas - FOC006")
    y -= 30
    c.setFont("Helvetica", 10)
    for p in data["problems"]:
        if y < 80:
            c.showPage()
            y = height - 40
        c.drawString(40, y, f"Tipo: {p.get('type','')} | Descrição: {p.get('description','')}")
        y -= 15
        c.drawString(40, y, f"Data: {p.get('date','')} | Status: {p.get('status','')} | Prioridade: {p.get('priority','')}")
        y -= 15
        c.drawString(40, y, f"Responsável: {p.get('responsible','')} | Fornecedor: {p.get('supplier','')}")
        y -= 15
        c.drawString(40, y, f"Relatório: {p.get('report','')}")
        y -= 15
        c.drawString(40, y, f"Assinatura: {p.get('report_signature','')}")
        y -= 25
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="relatorio_problemas.pdf")

@app.route("/permissions", methods=["GET", "POST"])
def permissions():
    if "user" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user = next(u for u in data["users"] if u["username"] == session["user"])
    if user["role"] != "admin":
        return render_with_tabs(user, "permissions", "<b>Acesso negado</b>")
    if request.method == "POST":
        for i, u in enumerate(data["users"]):
            data["users"][i]["role"] = request.form.get(f"role_{i}", u["role"])
        save_data(data)
        flash("Permissões atualizadas!", "success")
        return redirect(url_for("dashboard"))
    table = """
        <h2>Permissões de Usuários</h2>
        <form method="post">
        <table>
            <tr><th>Usuário</th><th>Nome</th><th>Permissão</th></tr>
    """
    for i, u in enumerate(data["users"]):
        table += f"<tr><td>{u['username']}</td><td>{u['name']}</td><td><select name='role_{i}'>"
        table += f"<option value='comum' {'selected' if u['role']=='comum' else ''}>comum</option>"
        table += f"<option value='admin' {'selected' if u['role']=='admin' else ''}>admin</option>"
        table += "</select></td></tr>"
    table += "</table><button type='submit'>Salvar Permissões</button></form>"
    return render_with_tabs(user, "permissions", table)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)