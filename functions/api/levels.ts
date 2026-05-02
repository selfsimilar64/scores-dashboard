import type { AppHandler } from "./types";

export const onRequestGet: AppHandler = async ({ data: { sql } }) => {
  const rows = await sql`SELECT DISTINCT Level FROM scores ORDER BY Level`;
  return Response.json(rows.map((r) => r.level));
};
