import type {
  AccountInfo,
  AccountUpdatePayload,
  LoginResponse,
  UserInfo,
} from "../lib/types";
import { apiFetch } from "./client";

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

export async function fetchMe(): Promise<UserInfo> {
  return apiFetch<UserInfo>("/auth/me");
}

export async function updateAccount(
  payload: AccountUpdatePayload
): Promise<AccountInfo> {
  return apiFetch<AccountInfo>("/auth/me", {
    method: "PATCH",
    body: payload,
  });
}