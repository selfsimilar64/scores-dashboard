import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestGet: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("session_id");

  let rows;
  if (sessionId) {
    rows = await sql`
      SELECT ps.*, s.name as session_name
      FROM practice_schedules ps
      JOIN sessions s ON ps.session_id = s.id
      WHERE ps.session_id = ${Number(sessionId)}
      ORDER BY ps.level, ps.day_of_week
    `;
  } else {
    rows = await sql`
      SELECT ps.*, s.name as session_name
      FROM practice_schedules ps
      JOIN sessions s ON ps.session_id = s.id
      ORDER BY s.year DESC, ps.level, ps.day_of_week
    `;
  }

  return Response.json(rows);
};

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{
    session_id: number; level: string; day_of_week: number; start_time: string; end_time: string;
  }>();

  try {
    const [row] = await sql`
      INSERT INTO practice_schedules (session_id, level, day_of_week, start_time, end_time)
      VALUES (${body.session_id}, ${body.level}, ${body.day_of_week}, ${body.start_time}, ${body.end_time})
      RETURNING id
    `;
    return jsonResponse({ success: true, id: row.id });
  } catch (e: unknown) {
    return jsonResponse({ error: e instanceof Error ? e.message : "Insert failed" }, 400);
  }
};
