import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "../api/auth";
import { AuthProvider } from "../auth/AuthContext";
import { Login } from "./Login";

vi.mock("../api/auth", () => ({
  login: vi.fn(),
}));

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("Login", () => {
  beforeEach(() => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token",
      token_type: "bearer",
      username: "admin",
      role: "admin",
    });
  });

  it("renders the form fields and submit button", () => {
    renderLogin();
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ingresar" })).toBeInTheDocument();
  });

  it("shows a validation message when fields are empty", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Debe ingresar usuario y contraseña."
    );
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it("calls login and navigates away on valid credentials", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Usuario"), "admin");
    await user.type(screen.getByLabelText("Contraseña"), "secret");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));
    await screen.findByRole("button", { name: "Ingresar" });
    expect(authApi.login).toHaveBeenCalledWith("admin", "secret");
  });
});