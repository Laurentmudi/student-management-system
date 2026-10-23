import { useState } from "react";
import { errMsg } from "../api";
import { useAuth } from "../auth.jsx";
import { LogoImg } from "../components/ui.jsx";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try { await login(email, password); } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };
  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <LogoImg />
        <h1>Tu-Code Academy</h1>
        
        <p className="muted">Sign in to the Student Management System</p>
        {err && <div className="alert err">{err}</div>}
        <label className="field"><span>Email</span><input type="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></label>
        <label className="field"><span>Password</span><input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
        <button className="btn primary" style={{ width: "100%" }} disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}
