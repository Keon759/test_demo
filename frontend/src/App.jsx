import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

export default function App() {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const path = mode === "login" ? "/api/login" : "/api/register";

    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      setStatus(response.ok ? "ok" : "err");
      setMessage(data.message || "");
    } catch (error) {
      setStatus("err");
      setMessage(error.message);
    }
  }

  return (
    <main className="page">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="tabs">
          <button
            type="button"
            className={mode === "login" ? "tab active" : "tab"}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "register" ? "tab active" : "tab"}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <h1>{mode === "login" ? "Login" : "Register"}</h1>

        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit">{mode === "login" ? "Login" : "Register"}</button>
        {message ? <div className={`message ${status}`}>{message}</div> : null}
      </form>
    </main>
  );
}
