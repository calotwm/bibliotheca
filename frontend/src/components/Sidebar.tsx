import type { ComponentType } from "react";
import { NavLink } from "react-router-dom";
import {
  BookIcon,
  CartIcon,
  ChartIcon,
  HomeIcon,
  LogoutIcon,
  MenuIcon,
  UploadIcon,
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
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onLogout: () => void;
}

export function Sidebar({ collapsed, onToggle, onLogout }: SidebarProps) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex flex-col bg-navy text-cream transition-[width] duration-200 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      <div className="flex h-14 items-center gap-2 px-3">
        <span className="font-heading text-xl font-black">B</span>
        {!collapsed && (
          <span className="font-heading text-lg font-black">Bibliotheca</span>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="ml-auto rounded-sm p-1.5 text-cream/80 hover:bg-navy-light hover:text-cream"
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
              `flex items-center gap-3 rounded-sm px-3 py-2 text-sm ${
                isActive
                  ? "bg-cream font-semibold text-navy"
                  : "text-cream/80 hover:bg-navy-light hover:text-cream"
              }`
            }
            title={collapsed ? item.label : undefined}
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-cream/20 p-2">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-sm px-3 py-2 text-sm text-cream/80 hover:bg-navy-light hover:text-cream"
          title={collapsed ? "Cerrar sesión" : undefined}
        >
          <LogoutIcon className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Cerrar sesión</span>}
        </button>
      </div>
    </aside>
  );
}