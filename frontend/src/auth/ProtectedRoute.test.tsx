import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "./AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

function renderProtected(initialEntries: string[], withToken: boolean) {
  localStorage.clear();
  if (withToken) {
    localStorage.setItem("bibliotheca_token", "test-token");
    localStorage.setItem("bibliotheca_user", JSON.stringify({ username: "admin", role: "admin" }));
  }
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Página de login</div>} />
          <Route
            path="/inventario"
            element={
              <ProtectedRoute>
                <div>Contenido protegido</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("redirects to /login when there is no token", () => {
    renderProtected(["/inventario"], false);
    expect(screen.getByText("Página de login")).toBeInTheDocument();
    expect(screen.queryByText("Contenido protegido")).not.toBeInTheDocument();
  });

  it("renders children when a token exists", () => {
    renderProtected(["/inventario"], true);
    expect(screen.getByText("Contenido protegido")).toBeInTheDocument();
    expect(screen.queryByText("Página de login")).not.toBeInTheDocument();
  });
});