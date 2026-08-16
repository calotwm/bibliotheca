import type { LoginResponse, UserInfo } from "../lib/types";
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