import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{
    athlete_id: number;
    practice_date: string;
    level: string;
    status?: string;
    notes?: string | null;
    late_minutes?: number;
    session_id?: number;
  }>();

  const { athlete_id, practice_date, level, status = "none", notes = null, late_minutes = 0 } = body;
  let { session_id } = body;

  if (!athlete_id || !practice_date || !level) {
    return jsonResponse({ error: "athlete_id, practice_date, and level are required" }, 400);
  }

  // Find session if not provided
  if (!session_id) {
    const rows = await sql`
      SELECT id FROM sessions
      WHERE start_date <= ${practice_date} AND end_date >= ${practice_date}
      LIMIT 1
    `;
    session_id = rows[0]?.id as number | undefined;
  }

  try {
    const [row] = await sql`
      INSERT INTO attendance (athlete_id, session_id, practice_date, level, status, notes, late_minutes, updated_at)
      VALUES (${athlete_id}, ${session_id ?? null}, ${practice_date}, ${level}, ${status}, ${notes}, ${late_minutes}, NOW())
      ON CONFLICT (athlete_id, practice_date)
      DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes, late_minutes = EXCLUDED.late_minutes, updated_at = NOW()
      RETURNING id
    `;
    return jsonResponse({ success: true, id: row.id });
  } catch (e: unknown) {
    return jsonResponse({ error: e instanceof Error ? e.message : "Insert failed" }, 400);
  }
};
