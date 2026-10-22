import axios from "axios";

export const API = import.meta.env.VITE_API_URL || "/api";
const api = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const publicPath = ["/login", "/verify"].some((p) => location.pathname.startsWith(p));
    if (err.response?.status === 401 && !publicPath) {
      localStorage.removeItem("token");
      location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const errMsg = (e) => e?.response?.data?.error || e?.message || "Something went wrong";

// PDFs / files need the auth header, so they are fetched as blobs.
async function blobOf(url, params) {
  try {
    const r = await api.get(url, { params, responseType: "blob" });
    return r;
  } catch (e) {
    // error bodies arrive as blobs too — turn them back into a readable message
    if (e.response?.data instanceof Blob) {
      try { e.response.data = JSON.parse(await e.response.data.text()); } catch { /* ignore */ }
    }
    throw e;
  }
}

export async function downloadFile(url, filename, params) {
  const r = await blobOf(url, params);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(r.data);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

export async function viewPdf(url) {
  const r = await blobOf(url);
  window.open(URL.createObjectURL(r.data), "_blank");
}

export async function printPdf(url) {
  const r = await blobOf(url);
  const blobUrl = URL.createObjectURL(r.data);
  const frame = document.createElement("iframe");
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  frame.src = blobUrl;
  frame.onload = () => {
    try { frame.contentWindow.focus(); frame.contentWindow.print(); }
    catch { window.open(blobUrl, "_blank"); }
    setTimeout(() => { frame.remove(); URL.revokeObjectURL(blobUrl); }, 60000);
  };
  document.body.appendChild(frame);
}

export default api;
