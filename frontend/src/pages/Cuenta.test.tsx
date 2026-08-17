import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "../api/auth";
import { AuthProvider } from "../auth/AuthContext";
import { Cuenta } from "./Cuenta";

vi.mock("../api/auth", () => ({
  login: vi.fn(),
  fetchMe: vi.fn(),
  updateAccount: vi.fn(),
}));

function renderCuenta(role = "admin") {
  localStorage.setItem("bibliotheca_token", "test-token");
  localStorage.setItem(
    "bibliotheca_user",
    JSON.stringify({ username: "admin", role })
  );
  return render(
    <AuthProvider>
      <Cuenta />
    </AuthProvider>
  );
}

describe("Cuenta", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(authApi.updateAccount).mockResolvedValue({
      id: 1,
      username: "admin",
      role: "admin",
    });
    vi.mocked(authApi.fetchMe).mockResolvedValue({
      username: "admin",
      role: "admin",
    });
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "new-token",
      token_type: "bearer",
      username: "admin",
      role: "admin",
    });
  });

  it("renders the account card with current username and role", () => {
    renderCuenta();
    expect(
      screen.getByRole("heading", { name: "Mi cuenta" })
    ).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("Administrador")).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña actual/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nuevo usuario/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nueva contraseña/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirmar nueva contraseña/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Guardar cambios" })
    ).toBeInTheDocument();
  });

  it("shows a validation error when the new passwords do not match", async () => {
    const user = userEvent.setup();
    renderCuenta();
    await user.type(screen.getByLabelText(/Contraseña actual/), "admin");
    await user.type(screen.getByLabelText(/Nueva contraseña/), "nueva-segura");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/), "otra");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Las contraseñas no coinciden."
    );
    expect(authApi.updateAccount).not.toHaveBeenCalled();
  });

  it("submits the right payload for a password change and refreshes the user", async () => {
    const user = userEvent.setup();
    renderCuenta();
    await user.type(screen.getByLabelText(/Contraseña actual/), "admin");
    await user.type(screen.getByLabelText(/Nueva contraseña/), "nueva-segura");
    await user.type(
      screen.getByLabelText(/Confirmar nueva contraseña/),
      "nueva-segura"
    );
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(authApi.updateAccount).toHaveBeenCalledWith({
        current_password: "admin",
        new_username: null,
        new_password: "nueva-segura",
      });
    });
    expect(authApi.fetchMe).toHaveBeenCalled();
    expect(await screen.findByText("Cambios guardados.")).toBeInTheDocument();
  });

  it("re-authenticates and shows the new username after a successful change", async () => {
    vi.mocked(authApi.updateAccount).mockResolvedValue({
      id: 1,
      username: "nuevo-admin",
      role: "admin",
    });
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "new-token",
      token_type: "bearer",
      username: "nuevo-admin",
      role: "admin",
    });
    const user = userEvent.setup();
    renderCuenta();
    await user.type(screen.getByLabelText(/Contraseña actual/), "admin");
    await user.type(screen.getByLabelText(/Nuevo usuario/), "nuevo-admin");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(authApi.updateAccount).toHaveBeenCalledWith({
        current_password: "admin",
        new_username: "nuevo-admin",
        new_password: null,
      });
    });
    expect(authApi.login).toHaveBeenCalledWith("nuevo-admin", "admin");
    expect(await screen.findByText("nuevo-admin")).toBeInTheDocument();
  });

  it("shows the API error detail when the current password is wrong", async () => {
    vi.mocked(authApi.updateAccount).mockRejectedValue(
      new Error("Contraseña actual incorrecta")
    );
    const user = userEvent.setup();
    renderCuenta();
    await user.type(screen.getByLabelText(/Contraseña actual/), "mal");
    await user.type(screen.getByLabelText(/Nueva contraseña/), "nueva-segura");
    await user.type(
      screen.getByLabelText(/Confirmar nueva contraseña/),
      "nueva-segura"
    );
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Contraseña actual incorrecta"
    );
  });
});