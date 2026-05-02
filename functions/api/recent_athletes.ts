import type { AppHandler } from "./types";

export const onRequestGet: AppHandler = async ({ data: { sql } }) => {
  const rows = await sql`SELECT DISTINCT AthleteName FROM scores ORDER BY AthleteName`;
  return Response.json(rows.map((r) => r.athletename));
};
