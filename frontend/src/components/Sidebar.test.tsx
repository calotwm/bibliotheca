import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "./Sidebar";

function renderSidebar(collapsed: boolean, onLogout: () => void = () => {}) {
  return render(
    <MemoryRouter>
      <Sidebar collapsed={collapsed} onToggle={() => {}} onLogout={onLogout} />
    </MemoryRouter>
  );
}

describe("Sidebar", () => {
  it("renders every navigation link with its label", () => {
    renderSidebar(false);
    expect(screen.getByText("Inicio")).toBeInTheDocument();
    expect(screen.getByText("Inventario")).toBeInTheDocument();
    expect(screen.getByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText("Proveedores")).toBeInTheDocument();
    expect(screen.getByText("Reportes")).toBeInTheDocument();
    expect(screen.getByText("Importar Excel")).toBeInTheDocument();
    expect(screen.getByText("Cerrar sesión")).toBeInTheDocument();
  });

  it("hides labels when collapsed", () => {
    renderSidebar(true);
    expect(screen.queryByText("Inventario")).not.toBeInTheDocument();
    expect(screen.getByTitle("Inventario")).toBeInTheDocument();
  });

  it("calls onLogout when Cerrar sesión is clicked", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    renderSidebar(false, onLogout);
    await user.click(screen.getByText("Cerrar sesión"));
    expect(onLogout).toHaveBeenCalledTimes(1);
  });
});