import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { ImportarExcel } from "./pages/ImportarExcel";
import { Inventario } from "./pages/Inventario";
import { Login } from "./pages/Login";
import { Precios } from "./pages/Precios";
import { Proveedores } from "./pages/Proveedores";
import { Reportes } from "./pages/Reportes";
import { Ventas } from "./pages/Ventas";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="inventario" element={<Inventario />} />
        <Route path="ventas" element={<Ventas />} />
        <Route path="proveedores" element={<Proveedores />} />
        <Route path="reportes" element={<Reportes />} />
        <Route path="importar" element={<ImportarExcel />} />
        <Route path="precios" element={<Precios />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}