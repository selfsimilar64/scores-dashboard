import type { NeonQueryFunction } from "@neondatabase/serverless";

export interface Env {
  DATABASE_URL: string;
}

export interface AppData {
  sql: NeonQueryFunction;
}

export type AppHandler = PagesFunction<Env, string, AppData>;

export function jsonResponse(data: unknown, status = 200): Response {
  return Response.json(data, { status });
}

export function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

export function toDateStr(v: unknown): string {
  if (v instanceof Date) return v.toISOString().split("T")[0];
  return String(v ?? "");
}
