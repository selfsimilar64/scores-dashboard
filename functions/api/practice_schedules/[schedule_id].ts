import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestPut: PagesFunction<Env, string, AppData> = async ({ params, request, data: { sql } }) => {
  const scheduleId = Number(params.schedule_id);
  const body = await request.json<{
    level: string; day_of_week: number; start_time: string; end_time: string;
  }>();

  try {
    await sql`
      UPDATE practice_schedules
      SET level = ${body.level}, day_of_week = ${body.day_of_week},
          start_time = ${body.start_time}, end_time = ${body.end_time}
      WHERE id = ${scheduleId}
    `;
    return jsonResponse({ success: true });
  } catch (e: unknown) {
    return jsonResponse({ error: e instanceof Error ? e.message : "Update failed" }, 400);
  }
};

export const onRequestDelete: PagesFunction<Env, string, AppData> = async ({ params, data: { sql } }) => {
  const scheduleId = Number(params.schedule_id);
  await sql`DELETE FROM practice_schedules WHERE id = ${scheduleId}`;
  return jsonResponse({ success: true });
};
