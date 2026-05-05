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

/** Extract YYYY-MM-DD from any date value (Date object, ISO timestamp, or plain date string). */
export function toDateStr(v: unknown): string {
  if (v instanceof Date) return v.toISOString().split("T")[0];
  const s = String(v ?? "");
  return s.includes("T") ? s.split("T")[0] : s;
}

/** Parse a date value into a noon-UTC Date, handling both "YYYY-MM-DD" and full ISO timestamps. */
export function toNoonUTC(v: unknown): Date {
  const dateStr = toDateStr(v);
  return new Date(dateStr + "T12:00:00Z");
}
