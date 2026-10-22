import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import api, { API } from "../api";

// ---------- toast ----------
const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const show = useCallback((msg, type = "ok") => {
    const id = Math.random();
    setItems((x) => [...x, { id, msg, type }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), type === "err" ? 6000 : 3500);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div className="toasts">
        {items.map((t) => <div key={t.id} className={`toast ${t.type}`}>{t.msg}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}

// ---------- helpers ----------
export const money = (n) => "KES " + Number(n || 0).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const fdate = (d) => (d ? new Date(d.length <= 10 ? d + "T00:00:00" : d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—");
export const fdatetime = (d) => (d ? new Date(d + (d.endsWith("Z") ? "" : "Z")).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");

export function useDebounce(value, ms = 350) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

export function useApi(path, params, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    if (!path) { setLoading(false); return; }
    setLoading(true);
    api.get(path, { params }).then((r) => live && (setData(r.data), setError(null)))
      .catch((e) => live && setError(e?.response?.data?.error || e.message))
      .finally(() => live && setLoading(false));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, JSON.stringify(params), tick, ...deps]);
  return { data, loading, error, reload: () => setTick((t) => t + 1), setData };
}

// ---------- components ----------
export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const h = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true">
        <div className="modal-head"><h3>{title}</h3><button className="icon-btn" onClick={onClose} aria-label="Close">✕</button></div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function PageHeader({ title, sub, children }) {
  return (
    <div className="page-head">
      <div><h1>{title}</h1>{sub && <p className="muted">{sub}</p>}</div>
      <div className="actions">{children}</div>
    </div>
  );
}

const STATUS_CLASS = { Active: "blue", "In Progress": "amber", "Cleared (Completed)": "green", Suspended: "red", Withdrawn: "gray",
  Paid: "green", Partial: "amber", Pending: "gray", Present: "green", Late: "amber", Absent: "red", sent: "green", simulated: "blue", failed: "red" };
export const Badge = ({ text }) => <span className={`badge ${STATUS_CLASS[text] || "gray"}`}>{text}</span>;

export function Progress({ value, small }) {
  const v = Math.max(0, Math.min(100, value || 0));
  return (
    <div className={`bar ${small ? "small" : ""}`} title={`${v}%`}>
      <div style={{ width: v + "%" }} className={v >= 100 ? "done" : ""} />
      <span>{v}%</span>
    </div>
  );
}

export function Pagination({ meta, onPage }) {
  if (!meta || meta.pages <= 1) return meta ? <div className="pager muted">{meta.total} record{meta.total === 1 ? "" : "s"}</div> : null;
  return (
    <div className="pager">
      <span className="muted">{meta.total} records</span>
      <button className="btn sm" disabled={meta.page <= 1} onClick={() => onPage(meta.page - 1)}>← Prev</button>
      <span>Page {meta.page} of {meta.pages}</span>
      <button className="btn sm" disabled={meta.page >= meta.pages} onClick={() => onPage(meta.page + 1)}>Next →</button>
    </div>
  );
}

export const Loading = () => <div className="loading"><div className="spinner" /> Loading…</div>;
export const ErrorBox = ({ msg }) => msg ? <div className="alert err">{msg}</div> : null;
export const Empty = ({ children = "Nothing to show yet." }) => <div className="empty">{children}</div>;

export function Field({ label, children, hint, required, full }) {
  return (
    <label className={`field ${full ? "full" : ""}`}>
      <span>{label}{required && <b className="req"> *</b>}</span>
      {children}
      {hint && <small className="muted">{hint}</small>}
    </label>
  );
}

// <img> tags can't send the Authorization header, so images are fetched as blobs.
export function AuthImage({ src, alt = "", className = "", fallback }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let revoked = false, obj;
    setUrl(null);
    if (!src) return;
    api.get(`/files/${src}`, { responseType: "blob" }).then((r) => {
      if (revoked) return;
      obj = URL.createObjectURL(r.data);
      setUrl(obj);
    }).catch(() => {});
    return () => { revoked = true; if (obj) URL.revokeObjectURL(obj); };
  }, [src]);
  if (!url) return fallback || <div className={`avatar ${className}`} aria-label={alt}>👤</div>;
  return <img src={url} alt={alt} className={className} />;
}

export function Avatar({ photo, name, size = 36 }) {
  const initials = (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const fallback = <div className="avatar-i" style={{ width: size, height: size, fontSize: size * 0.38 }}>{initials}</div>;
  if (!photo) return fallback;
  return <AuthImage src={photo} alt={name} className="avatar-img" fallback={fallback} />;
}

export function Confirm({ title, message, onYes, onNo, danger = true, yes = "Delete" }) {
  return (
    <Modal title={title} onClose={onNo}>
      <p>{message}</p>
      <div className="form-actions">
        <button className="btn" onClick={onNo}>Cancel</button>
        <button className={`btn ${danger ? "danger" : "primary"}`} onClick={onYes}>{yes}</button>
      </div>
    </Modal>
  );
}

export const LogoImg = ({ className }) => <img src={`${API}/public/logo`} alt="logo" className={className} />;
