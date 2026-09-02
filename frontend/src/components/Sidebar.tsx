import { useEffect } from "react";
import type { ComponentType } from "react";
import { NavLink } from "react-router-dom";
import {
  BookIcon,
  CartIcon,
  ChartIcon,
  HomeIcon,
  LogoutIcon,
  MenuIcon,
  TagIcon,
  UploadIcon,
  UserIcon,
  UsersIcon,
} from "./icons";

interface IconProps {
  className?: string;
}

interface NavEntry {
  to: string;
  label: string;
  icon: ComponentType<IconProps>;
  end?: boolean;
}

const NAV_ITEMS: NavEntry[] = [
  { to: "/", label: "Inicio", icon: HomeIcon, end: true },
  { to: "/inventario", label: "Inventario", icon: BookIcon },
  { to: "/ventas", label: "Ventas", icon: CartIcon },
  { to: "/proveedores", label: "Proveedores", icon: UsersIcon },
  { to: "/reportes", label: "Reportes", icon: ChartIcon },
  { to: "/importar", label: "Importar Excel", icon: UploadIcon },
  { to: "/precios", label: "Precios", icon: TagIcon },
  { to: "/cuenta", label: "Cuenta", icon: UserIcon },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onLogout: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({
  collapsed,
  onToggle,
  onLogout,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onMobileClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen, onMobileClose]);

  const labelClass = collapsed ? "lg:hidden" : "";

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-navy/50 lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}
      <aside
        role={mobileOpen ? "dialog" : undefined}
        aria-modal={mobileOpen ? "true" : undefined}
        aria-label="Menú de navegación"
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-navy/10 bg-paper text-ink transition-transform duration-200 lg:transition-[width] ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 ${collapsed ? "lg:w-16" : "lg:w-64"}`}
      >
        <div className="flex h-16 items-center gap-2 px-3">
          <img
            src="/logo-horizontal-naranja.svg"
            alt="Ojo de Poeta - Libros"
            className={`h-10 w-auto object-contain ${
              collapsed ? "lg:hidden" : ""
            }`}
          />
          <button
            type="button"
            onClick={onToggle}
            className="ml-auto hidden rounded-sm p-1.5 text-ink-soft hover:bg-navy/10 hover:text-ink lg:flex"
            aria-label={collapsed ? "Expandir menú" : "Contraer menú"}
          >
            <MenuIcon className="h-5 w-5" />
          </button>
        </div>

        <nav className="mt-2 flex-1 space-y-1 overflow-y-auto px-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm ${
                  isActive
                    ? "bg-navy font-semibold text-white"
                    : "text-ink-soft hover:bg-navy/10 hover:text-ink"
                }`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              <span className={labelClass}>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-navy/10 p-2">
          <button
            type="button"
            onClick={onLogout}
            className="flex w-full items-center gap-3 rounded-sm px-3 py-2.5 text-sm text-ink-soft hover:bg-navy/10 hover:text-ink"
            title={collapsed ? "Cerrar sesión" : undefined}
          >
            <LogoutIcon className="h-5 w-5 shrink-0" />
            <span className={labelClass}>Cerrar sesión</span>
          </button>
        </div>
      </aside>
    </>
  );
}