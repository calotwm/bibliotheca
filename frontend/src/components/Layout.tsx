import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { MenuIcon, XIcon } from "./icons";
import { Sidebar } from "./Sidebar";

const PAGE_TITLES: Record<string, string> = {
  "/": "Inicio",
  "/inventario": "Inventario",
  "/ventas": "Ventas (POS)",
  "/proveedores": "Proveedores",
  "/reportes": "Reportes",
  "/importar": "Importar Excel",
  "/precios": "Precios",
};

export function Layout() {
  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem("sidebar_collapsed") === "1"
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] ?? "Librería";

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const toggle = () => {
    setCollapsed((current) => {
      localStorage.setItem("sidebar_collapsed", current ? "0" : "1");
      return !current;
    });
  };

  const roleLabel = user?.role === "admin" ? "Administrador" : "Cajero";

  return (
    <div className="min-h-screen">
      <Sidebar
        collapsed={collapsed}
        onToggle={toggle}
        onLogout={logout}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />
      <div
        className={`transition-[padding] duration-200 ${
          collapsed ? "lg:pl-16" : "lg:pl-64"
        }`}
      >
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-navy/10 bg-paper/95 px-4 backdrop-blur lg:hidden">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileOpen((current) => !current)}
              aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm text-navy hover:bg-navy/5"
            >
              {mobileOpen ? (
                <XIcon className="h-5 w-5" />
              ) : (
                <MenuIcon className="h-5 w-5" />
              )}
            </button>
            <span className="truncate font-heading text-lg font-bold text-navy">
              {title}
            </span>
          </div>
          <div className="truncate text-sm text-ink-soft">
            {user ? `${user.username} · ${roleLabel}` : ""}
          </div>
        </header>
        <header className="sticky top-0 z-30 hidden h-14 items-center justify-between border-b border-navy/10 bg-paper/95 px-4 backdrop-blur lg:flex">
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