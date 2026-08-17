import { useState } from "react";
import type { FormEvent } from "react";
import * as authApi from "../api/auth";
import { useAuth } from "../auth/AuthContext";
import { AlertIcon, CheckIcon } from "../components/icons";

const inputClass =
  "min-h-11 w-full rounded-sm border border-navy/20 bg-paper px-3 py-2 text-sm outline-none focus:border-navy disabled:opacity-50";

export function Cuenta() {
  const { user, login, refreshUser } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const roleLabel = user?.role === "admin" ? "Administrador" : "Cajero";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmedUsername = newUsername.trim();
    const usernameChanged =
      trimmedUsername !== "" && trimmedUsername !== user?.username;
    const passwordChanged = newPassword !== "";

    if (!currentPassword) {
      setError("Ingrese su contraseña actual.");
      return;
    }
    if (!usernameChanged && !passwordChanged) {
      setError("Indique un nuevo usuario o una nueva contraseña.");
      return;
    }
    if (usernameChanged && trimmedUsername.length < 3) {
      setError("El nuevo usuario debe tener al menos 3 caracteres.");
      return;
    }
    if (passwordChanged && newPassword.length < 6) {
      setError("La nueva contraseña debe tener al menos 6 caracteres.");
      return;
    }
    if (passwordChanged && newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setBusy(true);
    try {
      await authApi.updateAccount({
        current_password: currentPassword,
        new_username: usernameChanged ? trimmedUsername : null,
        new_password: passwordChanged ? newPassword : null,
      });
      if (usernameChanged) {
        // The JWT embeds the username, so a username change invalidates the
        // current token. Re-authenticate to keep the session working.
        await login(trimmedUsername, passwordChanged ? newPassword : currentPassword);
      } else {
        await refreshUser();
      }
      setSuccess("Cambios guardados.");
      setCurrentPassword("");
      setNewUsername("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No se pudieron guardar los cambios."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-8">
      <section className="rounded-sm border border-navy/10 bg-cream p-4">
        <h2 className="text-lg font-bold">Mi cuenta</h2>
        <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-ink-soft">Usuario</dt>
            <dd className="font-semibold">{user?.username}</dd>
          </div>
          <div>
            <dt className="text-ink-soft">Rol</dt>
            <dd className="font-semibold">{roleLabel}</dd>
          </div>
        </dl>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <label className="block">
            <span className="text-sm font-medium">Contraseña actual *</span>
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className={inputClass}
              autoComplete="current-password"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Nuevo usuario</span>
            <input
              type="text"
              value={newUsername}
              onChange={(event) => setNewUsername(event.target.value)}
              className={inputClass}
              placeholder="Dejar vacío para no cambiar"
              autoComplete="username"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Nueva contraseña</span>
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className={inputClass}
              placeholder="Mínimo 6 caracteres"
              autoComplete="new-password"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Confirmar nueva contraseña</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className={inputClass}
              autoComplete="new-password"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="min-h-11 w-full rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
          >
            {busy ? "Guardando…" : "Guardar cambios"}
          </button>
        </form>

        {error && (
          <p className="mt-3 flex items-center gap-1 text-sm text-red-700" role="alert">
            <AlertIcon className="h-4 w-4 shrink-0" />
            {error}
          </p>
        )}
        {success && (
          <p className="mt-3 flex items-center gap-1 text-sm font-semibold text-green-800">
            <CheckIcon className="h-4 w-4 shrink-0" />
            {success}
          </p>
        )}
      </section>
    </div>
  );
}