import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "./Sidebar";

function renderSidebar(
  collapsed: boolean,
  onLogout: () => void = () => {},
  onMobileClose: () => void = () => {}
) {
  return render(
    <MemoryRouter>
      <Sidebar
        collapsed={collapsed}
        onToggle={() => {}}
        onLogout={onLogout}
        mobileOpen={false}
        onMobileClose={onMobileClose}
      />
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
    expect(screen.getByText("Precios")).toBeInTheDocument();
    expect(screen.getByText("Cerrar sesión")).toBeInTheDocument();
  });

  it("hides labels on desktop when collapsed", () => {
    renderSidebar(true);
    expect(screen.getByText("Inventario")).toHaveClass("lg:hidden");
    expect(screen.getByTitle("Inventario")).toBeInTheDocument();
  });

  it("calls onLogout when Cerrar sesión is clicked", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    renderSidebar(false, onLogout);
    await user.click(screen.getByText("Cerrar sesión"));
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it("renders as a dialog when mobileOpen and closes on Escape", async () => {
    const user = userEvent.setup();
    const onMobileClose = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar
          collapsed={false}
          onToggle={() => {}}
          onLogout={() => {}}
          mobileOpen
          onMobileClose={onMobileClose}
        />
      </MemoryRouter>
    );
    expect(
      screen.getByRole("dialog", { name: "Menú de navegación" })
    ).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(onMobileClose).toHaveBeenCalledTimes(1);
  });

  it("closes when the backdrop is clicked", async () => {
    const user = userEvent.setup();
    const onMobileClose = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar
          collapsed={false}
          onToggle={() => {}}
          onLogout={() => {}}
          mobileOpen
          onMobileClose={onMobileClose}
        />
      </MemoryRouter>
    );
    const backdrop = document.querySelector(
      '[aria-hidden="true"]'
    ) as HTMLElement;
    await user.click(backdrop);
    expect(onMobileClose).toHaveBeenCalledTimes(1);
  });
});