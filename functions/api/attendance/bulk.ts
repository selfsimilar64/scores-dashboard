import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{
    records: {
      athlete_id: number; practice_date: string; level: string;
      status?: string; notes?: string | null; session_id?: number;
    }[];
  }>();

  const records = body.records ?? [];
  if (records.length === 0) {
    return jsonResponse({ error: "No records provided" }, 400);
  }

  let successCount = 0;
  const errors: { record: unknown; error: string }[] = [];

  for (const rec of records) {
    try {
      const { athlete_id, practice_date, level, status = "none", notes = null } = rec;
      let sessionId = rec.session_id;

      if (!athlete_id || !practice_date || !level) {
        errors.push({ record: rec, error: "Missing required fields" });
        continue;
      }

      if (!sessionId) {
        const rows = await sql`
          SELECT id FROM sessions
          WHERE start_date <= ${practice_date} AND end_date >= ${practice_date}
          LIMIT 1
        `;
        sessionId = rows[0]?.id as number | undefined;
      }

      await sql`
        INSERT INTO attendance (athlete_id, session_id, practice_date, level, status, notes, updated_at)
        VALUES (${athlete_id}, ${sessionId ?? null}, ${practice_date}, ${level}, ${status}, ${notes}, NOW())
        ON CONFLICT (athlete_id, practice_date)
        DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes, updated_at = NOW()
      `;
      successCount++;
    } catch (e: unknown) {
      errors.push({ record: rec, error: e instanceof Error ? e.message : "Failed" });
    }
  }

  return jsonResponse({ success: true, inserted: successCount, errors });
};
