import { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem("token"));

  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    api.get("/auth/me").then((r) => setUser(r.data.user)).catch(() => localStorage.removeItem("token")).finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };
  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };
  return <Ctx.Provider value={{ user, loading, login, logout, isAdmin: user?.role === "admin" }}>{children}</Ctx.Provider>;
}
