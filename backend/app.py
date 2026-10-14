from datetime import datetime, timezone
from contextlib import closing
import os
import sqlite3

from flask import Flask, g, jsonify, render_template_string, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash


DATABASE = os.environ.get("AUTH_DEMO_DB", os.path.join(os.path.dirname(__file__), "auth_demo.db"))


INDEX_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>登录注册 Demo</title>
  <style>
    :root {
      --bg: #f4f6fb;
      --panel: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --primary: #1677ff;
      --border: #e5e7eb;
      --success: #16a34a;
      --error: #dc2626;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      background: linear-gradient(120deg, rgba(22,119,255,.10), transparent 35%), var(--bg);
      color: var(--text);
    }
    .wrap {
      width: min(980px, calc(100% - 32px));
      margin: 0 auto;
      min-height: 100vh;
      display: grid;
      grid-template-columns: 1.05fr .95fr;
      gap: 28px;
      align-items: center;
    }
    .hero h1 {
      margin: 0 0 12px;
      font-size: 42px;
      line-height: 1.1;
    }
    .hero p {
      margin: 0 0 10px;
      color: var(--muted);
      line-height: 1.75;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 24px;
      box-shadow: 0 18px 45px rgba(15, 23, 42, .08);
    }
    .tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 18px;
    }
    .tab {
      border: 1px solid var(--border);
      background: #f9fafb;
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
    }
    .tab.active {
      background: rgba(22,119,255,.10);
      border-color: rgba(22,119,255,.3);
      color: var(--primary);
      font-weight: 700;
    }
    form { display: none; }
    form.active { display: block; }
    label {
      display: block;
      margin: 12px 0 6px;
      font-size: 14px;
      color: #374151;
    }
    input {
      width: 100%;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 15px;
      outline: none;
    }
    input:focus { border-color: var(--primary); }
    button.submit {
      width: 100%;
      margin-top: 18px;
      border: 0;
      border-radius: 8px;
      background: var(--primary);
      color: #fff;
      padding: 12px 14px;
      font-size: 15px;
      cursor: pointer;
    }
    .hint {
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .result {
      margin-top: 16px;
      padding: 12px 14px;
      border-radius: 8px;
      background: #f9fafb;
      border: 1px solid var(--border);
      min-height: 48px;
      white-space: pre-wrap;
      line-height: 1.6;
    }
    .result.ok { border-color: rgba(22,163,74,.25); color: var(--success); }
    .result.err { border-color: rgba(220,38,38,.25); color: var(--error); }
    @media (max-width: 860px) {
      .wrap { grid-template-columns: 1fr; padding: 24px 0; }
      .hero h1 { font-size: 34px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>登录注册 Demo</h1>
    </section>
    <section class="panel">
      <div class="tabs">
        <button class="tab active" id="tab-login" type="button">登录</button>
        <button class="tab" id="tab-register" type="button">注册</button>
      </div>
      <form id="login-form" class="active">
        <label for="login-username">用户名</label>
        <input id="login-username" placeholder="请输入用户名" />
        <label for="login-password">密码</label>
        <input id="login-password" type="password" placeholder="请输入密码" />
        <button class="submit" type="submit">登录</button>
      </form>
      <form id="register-form">
        <label for="register-username">用户名</label>
        <input id="register-username" placeholder="至少 6 位" />
        <label for="register-password">密码</label>
        <input id="register-password" type="password" placeholder="至少 6 位" />
        <button class="submit" type="submit">注册</button>
      </form>
      <div id="result" class="result">等待操作...</div>
      <div class="hint">接口地址：<code>/api/register</code>、<code>/api/login</code>。你可以先注册，再登录验证。</div>
    </section>
  </div>
  <script>
    const tabs = {
      login: document.getElementById("tab-login"),
      register: document.getElementById("tab-register"),
    };
    const forms = {
      login: document.getElementById("login-form"),
      register: document.getElementById("register-form"),
    };
    const result = document.getElementById("result");
    function setMode(mode) {
      Object.entries(tabs).forEach(([key, el]) => el.classList.toggle("active", key === mode));
      Object.entries(forms).forEach(([key, el]) => el.classList.toggle("active", key === mode));
      result.className = "result";
      result.textContent = "等待操作...";
    }
    tabs.login.onclick = () => setMode("login");
    tabs.register.onclick = () => setMode("register");
    async function postJson(url, payload) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      return { response, data };
    }
    forms.login.onsubmit = async (event) => {
      event.preventDefault();
      try {
        const { response, data } = await postJson("/api/login", {
          username: document.getElementById("login-username").value,
          password: document.getElementById("login-password").value,
        });
        result.className = "result " + (response.ok ? "ok" : "err");
        result.textContent = data.message || "登录完成";
      } catch (error) {
        result.className = "result err";
        result.textContent = "登录失败：" + error.message;
      }
    };
    forms.register.onsubmit = async (event) => {
      event.preventDefault();
      try {
        const { response, data } = await postJson("/api/register", {
          username: document.getElementById("register-username").value,
          password: document.getElementById("register-password").value,
        });
        result.className = "result " + (response.ok ? "ok" : "err");
        result.textContent = data.message || "注册完成";
      } catch (error) {
        result.className = "result err";
        result.textContent = "注册失败：" + error.message;
      }
    };
  </script>
</body>
</html>
"""


def create_app(database_path=None, *, inject_bug=True, enable_demo=True):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or DATABASE
    app.config["INJECT_USERNAME_BUG"] = inject_bug
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    CORS(app, origins=["http://127.0.0.1:5173", "http://localhost:5173"])

    @app.get("/")
    def index():
        return render_template_string(INDEX_HTML)

    @app.before_request
    def open_db():
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row

    @app.teardown_request
    def close_db(_error=None):
        db = getattr(g, "db", None)
        if db is not None:
            db.close()

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "inject_bug": app.config["INJECT_USERNAME_BUG"]})

    def credentials():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return None
        username, password = payload.get("username"), payload.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            return None
        if len(username) > 128 or len(password) > 128:
            return None
        return username.strip(), password

    @app.post("/api/register")
    def register():
        values = credentials()
        if values is None:
            return jsonify({"message": "请提供字符串类型的用户名和密码"}), 400
        username, password = values

        if not username or not password:
            return jsonify({"message": "用户名和密码不能为空"}), 400

        # The default intentionally omits this PRD rule; fixed mode verifies the same plan.
        if not app.config["INJECT_USERNAME_BUG"] and len(username) < 6:
            return jsonify({"message": "用户名长度不能少于6位"}), 400
        if len(password) < 6:
            return jsonify({"message": "密码长度不能少于6位"}), 400

        try:
            g.db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (
                    username,
                    generate_password_hash(password),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            g.db.commit()
        except sqlite3.IntegrityError:
            return jsonify({"message": "用户名已存在"}), 409

        return jsonify({"message": "注册成功", "username": username}), 201

    @app.post("/api/login")
    def login():
        values = credentials()
        if values is None:
            return jsonify({"message": "请提供字符串类型的用户名和密码"}), 400
        username, password = values

        if not username or not password:
            return jsonify({"message": "用户名和密码不能为空"}), 400

        user = g.db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "用户名或密码错误"}), 401

        return jsonify(
            {
                "message": "登录成功",
                "user": {"id": user["id"], "username": user["username"]},
            }
        )

    if enable_demo:
        @app.post("/api/demo/run")
        def demo_run():
            # This browser entry point is offline only and never spends API credits.
            from backend.pipeline import run_pipeline
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict) or type(payload.get("inject_bug", True)) is not bool:
                return jsonify({"message": "inject_bug 必须为布尔值"}), 400
            return jsonify(run_pipeline(inject_bug=payload.get("inject_bug", True)))

    init_database(app)
    return app


def init_database(app):
    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)
    with closing(sqlite3.connect(app.config["DATABASE"])) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        db.commit()


if __name__ == "__main__":
    create_app(inject_bug=os.environ.get("DEMO_INJECT_BUG", "1") != "0").run(
        host="127.0.0.1", port=5000
    )
