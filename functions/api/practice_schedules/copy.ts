import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{ source_session_id: number; target_session_id: number }>();
  const { source_session_id, target_session_id } = body;

  if (!source_session_id || !target_session_id) {
    return jsonResponse({ error: "Both source and target session IDs required" }, 400);
  }
  if (source_session_id === target_session_id) {
    return jsonResponse({ error: "Source and target sessions must be different" }, 400);
  }

  const sourceSchedules = await sql`
    SELECT level, day_of_week, start_time, end_time
    FROM practice_schedules WHERE session_id = ${source_session_id}
  `;

  if (sourceSchedules.length === 0) {
    return jsonResponse({ error: "No schedules found in source session" }, 400);
  }

  let copied = 0;
  for (const s of sourceSchedules) {
    const result = await sql`
      INSERT INTO practice_schedules (session_id, level, day_of_week, start_time, end_time)
      VALUES (${target_session_id}, ${s.level}, ${s.day_of_week}, ${s.start_time}, ${s.end_time})
      ON CONFLICT (session_id, level, day_of_week) DO NOTHING
    `;
    if ((result as unknown as { count: number }).count > 0) copied++;
  }

  return jsonResponse({ success: true, copied, total: sourceSchedules.length });
};
