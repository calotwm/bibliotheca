import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Sidebar } from "./Sidebar";

const PAGE_TITLES: Record<string, string> = {
  "/": "Inicio",
  "/inventario": "Inventario",
  "/ventas": "Ventas (POS)",
  "/proveedores": "Proveedores",
  "/reportes": "Reportes",
  "/importar": "Importar Excel",
};

export function Layout() {
  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem("sidebar_collapsed") === "1"
  );
  const { user, logout } = useAuth();
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] ?? "Bibliotheca";

  const toggle = () => {
    setCollapsed((current) => {
      localStorage.setItem("sidebar_collapsed", current ? "0" : "1");
      return !current;
    });
  };

  const roleLabel = user?.role === "admin" ? "Administrador" : "Cajero";

  return (
    <div className="min-h-screen">
      <Sidebar collapsed={collapsed} onToggle={toggle} onLogout={logout} />
      <div
        className={`transition-[padding] duration-200 ${
          collapsed ? "pl-16" : "pl-64"
        }`}
      >
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-navy/10 bg-paper/95 px-4 backdrop-blur">
          <h1 className="text-xl font-bold">{title}</h1>
          <div className="text-sm text-ink-soft">
            {user ? `${user.username} · ${roleLabel}` : ""}
          </div>
        </header>
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}