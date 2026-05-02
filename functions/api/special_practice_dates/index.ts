import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestGet: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("session_id");

  let rows;
  if (sessionId) {
    rows = await sql`
      SELECT spd.*, s.name as session_name
      FROM special_practice_dates spd
      JOIN sessions s ON spd.session_id = s.id
      WHERE spd.session_id = ${Number(sessionId)}
      ORDER BY spd.practice_date, spd.level
    `;
  } else {
    rows = await sql`
      SELECT spd.*, s.name as session_name
      FROM special_practice_dates spd
      JOIN sessions s ON spd.session_id = s.id
      ORDER BY spd.practice_date DESC, spd.level
    `;
  }

  return Response.json(rows);
};

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{
    session_id: number; practice_date: string; level: string;
    start_time: string; end_time: string; description?: string;
  }>();

  try {
    const [row] = await sql`
      INSERT INTO special_practice_dates (session_id, practice_date, level, start_time, end_time, description)
      VALUES (${body.session_id}, ${body.practice_date}, ${body.level},
              ${body.start_time}, ${body.end_time}, ${body.description ?? null})
      RETURNING id
    `;
    return jsonResponse({ success: true, id: row.id });
  } catch (e: unknown) {
    return jsonResponse({ error: e instanceof Error ? e.message : "Insert failed" }, 400);
  }
};
