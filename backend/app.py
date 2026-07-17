from datetime import datetime, timezone
import os
import sqlite3

try:
    from flask import Flask, g, jsonify, render_template_string, request
    from flask_cors import CORS
    from werkzeug.security import check_password_hash, generate_password_hash
except ModuleNotFoundError as exc:
    raise SystemExit(
        f"Missing Python dependency: {getattr(exc, 'name', 'required package')}. "
        "Run this with the backend virtual environment:\n"
        "  cd E:\\ai_test_demo\\backend\n"
        "  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
        "  .\\.venv\\Scripts\\python.exe app.py"
    ) from exc


DATABASE = os.environ.get(
    "AUTH_DEMO_DB",
    os.path.join(os.path.dirname(__file__), "auth_demo.db"),
)


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Login / Register</title>
  <style>
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; }
    body {
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      background: #f3f5f9;
      display: grid;
      place-items: center;
    }
    .card {
      width: min(360px, calc(100% - 32px));
      padding: 24px;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      background: #fff;
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
      display: grid;
      gap: 14px;
    }
    .tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .tab {
      border: 1px solid #d1d5db;
      border-radius: 8px;
      padding: 10px 12px;
      background: #f9fafb;
      cursor: pointer;
      font-size: 14px;
    }
    .tab.active {
      background: #eaf2ff;
      border-color: #8db2ff;
      color: #1454c7;
      font-weight: 700;
    }
    h1 { margin: 0 0 6px; font-size: 28px; }
    label { display: grid; gap: 6px; font-size: 14px; color: #374151; }
    input {
      width: 100%;
      padding: 12px 14px;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      font-size: 15px;
    }
    button[type="submit"] {
      margin-top: 4px;
      border: 0;
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 15px;
      background: #1463e8;
      color: #fff;
      cursor: pointer;
    }
    .message {
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 14px;
      min-height: 20px;
    }
    .ok { background: #e8f7ec; color: #166534; }
    .err { background: #fef2f2; color: #b91c1c; }
    form { display: none; }
    form.active { display: grid; gap: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="tabs">
      <button class="tab active" id="tab-login" type="button">Login</button>
      <button class="tab" id="tab-register" type="button">Register</button>
    </div>

    <form id="login-form" class="active">
      <h1>Login</h1>
      <label>Username
        <input id="login-username" autocomplete="username" />
      </label>
      <label>Password
        <input id="login-password" type="password" autocomplete="current-password" />
      </label>
      <button type="submit">Login</button>
    </form>

    <form id="register-form">
      <h1>Register</h1>
      <label>Username
        <input id="register-username" autocomplete="username" />
      </label>
      <label>Password
        <input id="register-password" type="password" autocomplete="new-password" />
      </label>
      <button type="submit">Register</button>
    </form>

    <div id="message" class="message"></div>
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
    const message = document.getElementById("message");

    function setMode(mode) {
      Object.entries(tabs).forEach(([key, el]) => el.classList.toggle("active", key === mode));
      Object.entries(forms).forEach(([key, el]) => el.classList.toggle("active", key === mode));
      message.className = "message";
      message.textContent = "";
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
        message.className = "message " + (response.ok ? "ok" : "err");
        message.textContent = data.message || "";
      } catch (error) {
        message.className = "message err";
        message.textContent = error.message;
      }
    };

    forms.register.onsubmit = async (event) => {
      event.preventDefault();
      try {
        const { response, data } = await postJson("/api/register", {
          username: document.getElementById("register-username").value,
          password: document.getElementById("register-password").value,
        });
        message.className = "message " + (response.ok ? "ok" : "err");
        message.textContent = data.message || "";
      } catch (error) {
        message.className = "message err";
        message.textContent = error.message;
      }
    };
  </script>
</body>
</html>
"""


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or DATABASE
    CORS(app)

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

    @app.post("/api/register")
    def register():
        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""

        if not username or not password:
            return jsonify({"message": "Username and password cannot be empty"}), 400

        if len(password) < 6:
            return jsonify({"message": "Password must be at least 6 characters"}), 400

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
            return jsonify({"message": "Username already exists"}), 409

        return jsonify({"message": "Register success", "username": username}), 201

    @app.post("/api/login")
    def login():
        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""

        if not username or not password:
            return jsonify({"message": "Username and password cannot be empty"}), 400

        user = g.db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Invalid username or password"}), 401

        return jsonify(
            {
                "message": "Login success",
                "user": {"id": user["id"], "username": user["username"]},
            }
        )

    init_database(app)
    return app


def init_database(app):
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as db:
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
    create_app().run(host="127.0.0.1", port=5000, debug=True)
