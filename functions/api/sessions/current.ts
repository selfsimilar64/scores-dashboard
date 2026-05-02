import type { Env, AppData } from "../types";
import { todayISO } from "../types";

export const onRequestGet: PagesFunction<Env, string, AppData> = async ({ data: { sql } }) => {
  const today = todayISO();
  const rows = await sql`
    SELECT * FROM sessions
    WHERE start_date <= ${today} AND end_date >= ${today}
    ORDER BY start_date DESC
    LIMIT 1
  `;

  return Response.json(rows[0] ?? null);
};
