"""Portal didático local. As três falhas são intencionais apenas em vulneravel.

O banco é recriado no início. Não há dados de pessoas reais neste aplicativo.
"""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from waitress import serve


def create_app(mode=None, database=None):
    mode = mode or os.environ.get("PORTAL_MODO", "seguro")
    if mode not in {"vulneravel", "seguro"}:
        raise ValueError("PORTAL_MODO deve ser vulneravel ou seguro")
    db_path = str(database or Path("/tmp/portal.sqlite"))
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        SESSION_COOKIE_NAME=f"portal_{mode}",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    app.json.ensure_ascii = False
    with sqlite3.connect(db_path) as db:
        db.executescript("""
            DROP TABLE IF EXISTS usuarios;
            DROP TABLE IF EXISTS cursos;
            DROP TABLE IF EXISTS perfis;
            DROP TABLE IF EXISTS documentos;
            CREATE TABLE usuarios(id INTEGER PRIMARY KEY, login TEXT UNIQUE,
                senha_hash TEXT, papel TEXT);
            CREATE TABLE cursos(id INTEGER PRIMARY KEY, nome TEXT, descricao TEXT);
            CREATE TABLE perfis(id INTEGER PRIMARY KEY, nome TEXT, email TEXT);
            CREATE TABLE documentos(id INTEGER PRIMARY KEY, dono_id INTEGER,
                titulo TEXT, conteudo TEXT);
        """)
        for uid, login, role in [(1, "ana", "aluno"), (2, "bruno", "aluno"), (3, "admin", "administrador")]:
            db.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)",
                       (uid, login, generate_password_hash("CampusLab!2026", method="pbkdf2:sha256:600000"), role))
        db.executemany("INSERT INTO cursos VALUES (?, ?, ?)", [
            (1, "Segurança de Redes", "Redes, protocolos e análise de exposição."),
            (2, "Desenvolvimento Web", "Aplicações, APIs e persistência de dados."),
            (3, "Banco de Dados", "Modelagem, consultas e integridade da informação."),
        ])
        db.executemany("INSERT INTO perfis VALUES (?, ?, ?)", [
            (1, "Ana — pessoa fictícia", "ana@campus.example"),
            (2, "Bruno — pessoa fictícia", "bruno@campus.example"),
            (3, "Administrador fictício", "admin@campus.example"),
        ])
        db.executemany("INSERT INTO documentos VALUES (?, ?, ?, ?)", [
            (101, 1, "Declaração de matrícula · Ana", "LAB_DOCUMENTO_ANA — Matrícula fictícia A-2026. Uso exclusivo no laboratório."),
            (102, 2, "Histórico acadêmico · Bruno", "LAB_DOCUMENTO_BRUNO — Histórico fictício B-2026. Este documento pertence apenas a Bruno."),
        ])

    def connection():
        if "db" not in g:
            # As operações web são somente leitura; a semente é criada acima.
            g.db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.before_request
    def start_request():
        g.started = time.monotonic()
        # Isola o login local de submissões feitas a partir de outras origens.
        if request.method == "POST" and request.headers.get("Origin"):
            if request.headers["Origin"].rstrip("/") != request.host_url.rstrip("/"):
                return jsonify(erro="Origem não permitida"), 403

    @app.after_request
    def audit(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        if request.path.startswith("/api/"):
            # Não registra cookies, senhas nem corpos de resposta.
            print(json.dumps({"evento": "http", "modo": mode, "metodo": request.method,
                              "caminho": request.path, "status": response.status_code,
                              "usuario_id": session.get("uid"),
                              "duracao_ms": round((time.monotonic() - g.started) * 1000, 2)}), flush=True)
        return response

    def current_user():
        return connection().execute("SELECT id, login, papel FROM usuarios WHERE id = ?",
                                    (session.get("uid"),)).fetchone()

    @app.get("/")
    def index():
        return render_template("index.html", mode=mode)

    @app.get("/health")
    def health():
        connection().execute("SELECT 1").fetchone()
        return jsonify(status="ok", modo=mode)

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("login"), str) or not isinstance(data.get("senha"), str):
            return jsonify(erro="Informe login e senha"), 400
        user = connection().execute("SELECT * FROM usuarios WHERE login = ?", (data["login"],)).fetchone()
        if not user or not check_password_hash(user["senha_hash"], data["senha"]):
            return jsonify(erro="Credenciais inválidas"), 401
        session.clear()
        session["uid"] = user["id"]
        return jsonify(id=user["id"], login=user["login"], papel=user["papel"])

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(status="sessão encerrada")

    @app.get("/api/me")
    def me():
        user = current_user()
        return (jsonify(dict(user)), 200) if user else (jsonify(erro="Entre na sua conta"), 401)

    @app.get("/api/cursos")
    def courses():
        course_id = request.args.get("id")
        sql = "SELECT id, nome, descricao FROM cursos"
        try:
            if course_id is None:
                rows = connection().execute(sql).fetchall()
            elif mode == "vulneravel":
                # FALHA DIDÁTICA: entrada não confiável vira parte da instrução SQL.
                rows = connection().execute(sql + " WHERE id = " + course_id).fetchall()
            else:
                # A entrada permanece um valor, sem alterar a estrutura da consulta.
                rows = connection().execute(sql + " WHERE id = ?", (course_id,)).fetchall()
            return jsonify(cursos=[dict(row) for row in rows])
        except sqlite3.Error:
            return jsonify(erro="Consulta inválida", cursos=[]), 400

    @app.get("/api/documentos")
    def documents():
        user = current_user()
        if not user:
            return jsonify(erro="Autenticação necessária"), 401
        rows = connection().execute("SELECT id, titulo FROM documentos WHERE dono_id = ?", (user["id"],)).fetchall()
        return jsonify(documentos=[dict(row) for row in rows])

    @app.get("/api/documentos/<int:document_id>")
    def document(document_id):
        user = current_user()
        if not user:
            return jsonify(erro="Autenticação necessária"), 401
        row = connection().execute("SELECT * FROM documentos WHERE id = ?", (document_id,)).fetchone()
        if row is None or (mode == "seguro" and row["dono_id"] != user["id"]):
            return jsonify(erro="Documento não encontrado ou sem permissão"), 404
        # No cenário vulnerável, falta verificar a propriedade do objeto (IDOR/BOLA).
        return jsonify(dict(row))

    @app.get("/api/admin/resumo")
    def admin_summary():
        user = current_user()
        if not user:
            return jsonify(erro="Autenticação necessária"), 401
        if mode == "seguro" and user["papel"] != "administrador":
            return jsonify(erro="Área exclusiva da administração"), 403
        # No cenário vulnerável, a autenticação substitui indevidamente a autorização.
        rows = connection().execute("SELECT id, nome, email FROM perfis ORDER BY id").fetchall()
        return jsonify(marcador="LAB_ADMIN_EXPOSTO", perfis=[dict(row) for row in rows])

    return app


if __name__ == "__main__":
    serve(create_app(), host="0.0.0.0", port=8000, threads=4)
