import { useNavigate } from "react-router-dom";
import api from "../api";
import { Empty, Loading, PageHeader, Pagination, fdatetime, useApi } from "../components/ui.jsx";
import { useState } from "react";

export default function Notifications() {
  const nav = useNavigate();
  const [page, setPage] = useState(1);
  const { data, loading, reload } = useApi("/notifications", { page });
  const open = async (n) => { if (!n.is_read) await api.post(`/notifications/${n.id}/read`); if (n.link) nav(n.link); else reload(); };
  const readAll = async () => { await api.post("/notifications/read-all"); reload(); };
  return (
    <>
      <PageHeader title="Notifications" sub={data ? `${data.unread} unread` : ""}><button className="btn" onClick={readAll}>Mark all as read</button></PageHeader>
      <div className="card flush">
        {loading ? <Loading /> : !data.items.length ? <Empty>You're all caught up.</Empty> : data.items.map((n) => (
          <div key={n.id} className={`notif ${n.is_read ? "" : "unread"}`} onClick={() => open(n)}>
            <div style={{ flex: 1 }}><b>{n.title}</b><div>{n.message}</div></div><small className="muted nowrap">{fdatetime(n.created_at)}</small>
          </div>))}
        <Pagination meta={data} onPage={setPage} />
      </div>
    </>
  );
}
