import { useState } from "react";
import api, { errMsg } from "../api";
import { useAuth } from "../auth.jsx";
import { ErrorBox, Field, PageHeader, useToast } from "../components/ui.jsx";

export default function Account() {
  const { user } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ current_password: "", new_password: "", confirm: "" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault(); setErr("");
    if (f.new_password !== f.confirm) return setErr("New passwords do not match");
    try { await api.post("/auth/change-password", { current_password: f.current_password, new_password: f.new_password }); toast("Password changed"); setF({ current_password: "", new_password: "", confirm: "" }); } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <>
      <PageHeader title="My Account" sub={`${user.name} · ${user.email} · ${user.role}`} />
      <form className="card" style={{ maxWidth: 480 }} onSubmit={submit}>
        <h2>Change password</h2><ErrorBox msg={err} />
        <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
          <Field label="Current password"><input type="password" required value={f.current_password} onChange={set("current_password")} autoComplete="current-password" /></Field>
          <Field label="New password" hint="At least 8 characters"><input type="password" minLength={8} required value={f.new_password} onChange={set("new_password")} autoComplete="new-password" /></Field>
          <Field label="Confirm new password"><input type="password" required value={f.confirm} onChange={set("confirm")} autoComplete="new-password" /></Field>
        </div>
        <div className="form-actions"><button className="btn primary">Update password</button></div>
      </form>
    </>
  );
}
