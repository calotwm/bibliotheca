import type { UserInfo } from "../lib/types";

const TOKEN_KEY = "bibliotheca_token";
const USER_KEY = "bibliotheca_user";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserInfo;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: UserInfo): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  isFormData?: boolean;
  raw?: boolean;
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, isFormData, raw, ...init } = options;
  const headers = new Headers(init.headers);
  if (body !== undefined && !isFormData) {
    headers.set("Content-Type", "application/json");
  }
  const token = getStoredToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api${path}`, {
    ...init,
    headers,
    body:
      body === undefined
        ? undefined
        : isFormData
          ? (body as FormData)
          : JSON.stringify(body),
  });

  if (response.status === 401 && !path.startsWith("/auth/login")) {
    clearSession();
    window.location.assign("/login");
    throw new ApiError(401, "La sesión expiró. Inicie sesión nuevamente.");
  }

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (data.detail !== undefined) {
        detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      }
    } catch {
      // keep the fallback message
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  if (raw) return (await response.blob()) as unknown as T;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}