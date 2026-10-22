import { useState } from "react";
import { Badge, Empty, Loading, PageHeader, Pagination, fdatetime, useApi, useDebounce } from "../components/ui.jsx";

export default function Logs() {
  const [tab, setTab] = useState("activity");
  return (
    <>
      <PageHeader title="Logs" sub="Audit trail of user activity and outgoing messages" />
      <div className="tabs"><button className={tab === "activity" ? "on" : ""} onClick={() => setTab("activity")}>Activity log</button><button className={tab === "messages" ? "on" : ""} onClick={() => setTab("messages")}>SMS / WhatsApp messages</button></div>
      {tab === "activity" ? <Activity /> : <Messages />}
    </>
  );
}
function Activity() {
  const [q, setQ] = useState(""); const [page, setPage] = useState(1); const dq = useDebounce(q);
  const { data, loading } = useApi("/activity-logs", { q: dq, page });
  return (<><div className="filters"><input className="grow" placeholder="Filter by action or detail…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} /></div>
    <div className="card flush">{loading ? <Loading /> : !data.items.length ? <Empty>No activity.</Empty> : (
      <div className="table-wrap"><table><thead><tr><th>When</th><th>User</th><th>Action</th><th>Detail</th><th>IP</th></tr></thead>
        <tbody>{data.items.map((a) => <tr key={a.id}><td className="nowrap">{fdatetime(a.created_at)}</td><td>{a.user}</td><td><span className="badge gray">{a.action}</span></td><td>{a.detail}</td><td>{a.ip}</td></tr>)}</tbody></table></div>)}
      <Pagination meta={data} onPage={setPage} /></div></>);
}
function Messages() {
  const [page, setPage] = useState(1);
  const { data, loading } = useApi("/message-logs", { page });
  return (<div className="card flush">{loading ? <Loading /> : !data.items.length ? <Empty>No messages yet.</Empty> : (
    <div className="table-wrap"><table><thead><tr><th>When</th><th>Student</th><th>Channel</th><th>Type</th><th>Status</th><th>Message</th></tr></thead>
      <tbody>{data.items.map((m) => <tr key={m.id}><td className="nowrap">{fdatetime(m.created_at)}</td><td>{m.student}<br /><small className="muted">{m.to}</small></td><td>{m.channel}</td><td>{m.kind}</td><td><Badge text={m.status} />{m.error && <div className="muted"><small>{m.error}</small></div>}</td><td style={{ minWidth: 260 }}>{m.body}</td></tr>)}</tbody></table></div>)}
    <Pagination meta={data} onPage={setPage} /></div>);
}
