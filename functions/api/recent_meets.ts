import type { AppHandler } from "./types";

export const onRequestGet: AppHandler = async ({ data: { sql } }) => {
  const rows = await sql`SELECT DISTINCT MeetName FROM scores ORDER BY MeetName`;
  return Response.json(rows.map((r) => r.meetname));
};
