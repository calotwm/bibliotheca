import type { Dashboard } from "../lib/types";
import { apiFetch } from "./client";

export function getDashboard(): Promise<Dashboard> {
  return apiFetch<Dashboard>("/dashboard");
}