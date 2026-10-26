import { useEffect, useState } from "react";
import api, { errMsg } from "../api";
import { ErrorBox, Field, Loading, LogoImg, PageHeader, useApi, useToast } from "../components/ui.jsx";

export default function Settings() {
  const toast = useToast();
  const { data, loading } = useApi("/settings");
  const [f, setF] = useState(null);
  const [err, setErr] = useState("");
  const [logoKey, setLogoKey] = useState(0);
  useEffect(() => { if (data) setF(data.settings); }, [data]);
  if (loading || !f) return <Loading />;
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.type === "checkbox" ? (e.target.checked ? "1" : "0") : e.target.value }));
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try { const { logo, ...body } = f; const r = await api.put("/settings", body); setF(r.data.settings); toast("Settings saved"); } catch (x) { setErr(errMsg(x)); }
  };
  const logo = async (e) => {
    const fd = new FormData(); fd.append("logo", e.target.files[0]);
    try { await api.post("/settings/logo", fd); setLogoKey((k) => k + 1); toast("Logo updated — used on receipts & certificates"); } catch (x) { toast(errMsg(x), "err"); }
  };
  const runNow = async () => {
    try { const r = await api.post("/settings/run-reminders"); toast(`Reminder run complete: ${r.data.messages} message(s) sent/logged, ${r.data.overdue_students} overdue student(s)`); } catch (x) { toast(errMsg(x), "err"); }
  };
  return (
    <form onSubmit={save}>
      <PageHeader title="System Settings" sub="Academy details, receipts, certificates and messaging" />
      <ErrorBox msg={err} />
      <fieldset><legend>Academy details</legend><div className="form-grid">
        <Field label="Academy name"><input value={f.academy_name} onChange={set("academy_name")} /></Field>
        <Field label="Address"><input value={f.academy_address} onChange={set("academy_address")} /></Field>
        <Field label="Phone"><input value={f.academy_phone} onChange={set("academy_phone")} /></Field>
        <Field label="Email"><input value={f.academy_email} onChange={set("academy_email")} /></Field>
        <Field label="Currency label"><input value={f.currency} onChange={set("currency")} /></Field>
        <Field label="Logo (receipts, certificates, login)" hint="PNG/JPG, square works best"><div style={{ display: "flex", gap: ".8rem", alignItems: "center" }}><LogoImg key={logoKey} className="avatar-img" /><input type="file" accept="image/*" onChange={logo} /></div></Field>
      </div></fieldset>
      <fieldset><legend>Certificate signature</legend><div className="form-grid">
        <Field label="Authorized signatory name"><input value={f.signatory_name} onChange={set("signatory_name")} /></Field>
        <Field label="Title under signature"><input value={f.signatory_title} onChange={set("signatory_title")} /></Field>
      </div></fieldset>
      <fieldset><legend>Payment reminders</legend><div className="form-grid">
        <Field label="Send reminder N days before due date"><input type="number" min="0" value={f.remind_days_before} onChange={set("remind_days_before")} /></Field>
        <Field label="Repeat overdue reminders every N days"><input type="number" min="1" value={f.remind_overdue_every} onChange={set("remind_overdue_every")} /></Field>
        <Field label="Email"><label><input type="checkbox" checked={f.channel_email === "1"} onChange={set("channel_email")} /> Enabled</label></Field>
        <Field label="SMS"><label><input type="checkbox" checked={f.channel_sms === "1"} onChange={set("channel_sms")} /> Enabled</label></Field>
        <Field label="WhatsApp"><label><input type="checkbox" checked={f.channel_whatsapp === "1"} onChange={set("channel_whatsapp")} /> Enabled</label></Field>
      </div>
        <p className="muted">Reminders run automatically every day (08:00 Nairobi time by default). You can also trigger them now:</p>
        <button type="button" className="btn" onClick={runNow}>Run reminders now</button></fieldset>
        <fieldset><legend>Email (Gmail or any SMTP)</legend>
        <div className="alert info">Sent to students who have an email address on file. With the email and app password left empty, emails are only recorded in <i>Logs → Messages</i>. For Gmail, turn on 2-Step Verification and create an <b>App password</b> in your Google account, then paste it below.</div>
        <div className="form-grid">
          <Field label="SMTP host"><input value={f.smtp_host} onChange={set("smtp_host")} placeholder="smtp.gmail.com" /></Field>
          <Field label="SMTP port" hint="587 (default) or 465"><input value={f.smtp_port} onChange={set("smtp_port")} placeholder="587" /></Field>
          <Field label="Email address (login)"><input type="email" value={f.smtp_user} onChange={set("smtp_user")} placeholder="yourschool@gmail.com" autoComplete="off" /></Field>
          <Field label="App password"><input type="password" value={f.smtp_password} onChange={set("smtp_password")} autoComplete="new-password" /></Field>
          <Field label="Send as (optional)" hint="Leave empty to use the login address"><input value={f.smtp_from} onChange={set("smtp_from")} /></Field>
        </div>
      </fieldset>
      <fieldset><legend>SMS / WhatsApp provider</legend>
        <div className="alert info">With provider <b>Log only</b>, messages are recorded in <i>Logs → Messages</i> but not delivered — ideal for testing. Choose Twilio (SMS + WhatsApp) or Africa's Talking (SMS) and enter credentials to send real messages.</div>
        <div className="form-grid">
          <Field label="Provider"><select value={f.msg_provider} onChange={set("msg_provider")}><option value="log">Log only (no sending)</option><option value="twilio">Twilio (SMS + WhatsApp)</option><option value="africastalking">Africa's Talking (SMS)</option></select></Field>
        </div>
        {f.msg_provider === "twilio" && <div className="form-grid" style={{ marginTop: ".9rem" }}>
          <Field label="Account SID"><input value={f.twilio_sid} onChange={set("twilio_sid")} /></Field>
          <Field label="Auth token"><input type="password" value={f.twilio_token} onChange={set("twilio_token")} /></Field>
          <Field label="SMS from (number or sender ID)"><input value={f.twilio_sms_from} onChange={set("twilio_sms_from")} placeholder="+1555…" /></Field>
          <Field label="WhatsApp from"><input value={f.twilio_whatsapp_from} onChange={set("twilio_whatsapp_from")} placeholder="whatsapp:+14155238886" /></Field></div>}
        {f.msg_provider === "africastalking" && <div className="form-grid" style={{ marginTop: ".9rem" }}>
          <Field label="Username"><input value={f.at_username} onChange={set("at_username")} /></Field>
          <Field label="API key"><input type="password" value={f.at_api_key} onChange={set("at_api_key")} /></Field>
          <Field label="Sender ID (optional)"><input value={f.at_sender_id} onChange={set("at_sender_id")} /></Field></div>}
      </fieldset>
      <div className="form-actions"><button className="btn primary">Save settings</button></div>
    </form>
  );
}
