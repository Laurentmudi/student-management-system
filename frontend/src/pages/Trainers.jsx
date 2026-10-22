import { useState } from "react";
import api, { errMsg } from "../api";
import { Badge, Empty, ErrorBox, Field, Loading, Modal, PageHeader, useApi, useToast } from "../components/ui.jsx";

export default function Trainers() {
  const toast = useToast();
  const [role, setRole] = useState("trainer");
  const { data, loading, reload } = useApi("/users", { role });
  const [edit, setEdit] = useState(null);
  const toggle = async (u) => { try { await api.put(`/users/${u.id}`, { is_active: !u.is_active }); toast(u.is_active ? "Account disabled" : "Account enabled"); reload(); } catch (e) { toast(errMsg(e), "err"); } };
  return (
    <>
      <PageHeader title="Trainers & Users" sub="Manage trainer accounts and administrators"><button className="btn primary" onClick={() => setEdit({ role })}>+ Add {role}</button></PageHeader>
      <div className="tabs"><button className={role === "trainer" ? "on" : ""} onClick={() => setRole("trainer")}>Trainers</button><button className={role === "admin" ? "on" : ""} onClick={() => setRole("admin")}>Administrators</button></div>
      <div className="card flush">
        {loading ? <Loading /> : !data.items.length ? <Empty>No users.</Empty> : (
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Phone</th>{role === "trainer" && <th>Students</th>}<th>Status</th><th /></tr></thead>
            <tbody>{data.items.map((u) => <tr key={u.id}><td><b>{u.name}</b></td><td>{u.email}</td><td>{u.phone || "—"}</td>{role === "trainer" && <td>{u.student_count}</td>}
              <td><span className={`badge ${u.is_active ? "green" : "gray"}`}>{u.is_active ? "Active" : "Disabled"}</span></td>
              <td><div className="row-actions"><button className="btn sm" onClick={() => setEdit(u)}>Edit</button><button className="btn sm" onClick={() => toggle(u)}>{u.is_active ? "Disable" : "Enable"}</button></div></td></tr>)}</tbody></table></div>)}
      </div>
      {edit && <UserForm user={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload(); }} />}
    </>
  );
}

function UserForm({ user, onClose, onSaved }) {
  const toast = useToast();
  const [f, setF] = useState({ name: user.name || "", email: user.email || "", phone: user.phone || "", password: "", role: user.role });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    const body = { ...f }; if (user.id && !body.password) delete body.password;
    try { user.id ? await api.put(`/users/${user.id}`, body) : await api.post("/users", body); toast("Saved"); onSaved(); } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <Modal title={user.id ? "Edit user" : `Add ${f.role}`} onClose={onClose}>
      <form onSubmit={submit}><ErrorBox msg={err} /><div className="form-grid">
        <Field label="Full name" required><input required value={f.name} onChange={set("name")} /></Field>
        <Field label="Email (login)" required><input type="email" required value={f.email} onChange={set("email")} /></Field>
        <Field label="Phone"><input value={f.phone} onChange={set("phone")} /></Field>
        <Field label={user.id ? "New password" : "Password"} required={!user.id} hint={user.id ? "Leave blank to keep the current password" : "At least 8 characters"}><input type="password" minLength={8} required={!user.id} value={f.password} onChange={set("password")} autoComplete="new-password" /></Field>
      </div><div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn primary">Save</button></div></form>
    </Modal>
  );
}
