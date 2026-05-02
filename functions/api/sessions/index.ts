import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestGet: PagesFunction<Env, string, AppData> = async ({ data: { sql } }) => {
  const rows = await sql`SELECT * FROM sessions ORDER BY year DESC, start_date DESC`;
  return Response.json(rows);
};

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{
    name: string; year: number; season: string; start_date: string; end_date: string;
  }>();

  if (!body.name || !body.year || !body.season || !body.start_date || !body.end_date) {
    return jsonResponse({ error: "All fields required: name, year, season, start_date, end_date" }, 400);
  }

  try {
    const [row] = await sql`
      INSERT INTO sessions (name, year, season, start_date, end_date)
      VALUES (${body.name}, ${body.year}, ${body.season}, ${body.start_date}, ${body.end_date})
      RETURNING id
    `;
    return jsonResponse({ success: true, id: row.id });
  } catch (e: unknown) {
    return jsonResponse({ error: e instanceof Error ? e.message : "Insert failed" }, 400);
  }
};
