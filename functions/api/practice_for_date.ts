import type { AppHandler } from "./types";
import { todayISO } from "./types";

/**
 * Shared logic for practice_for_date and todays_practice.
 * Returns the JSON-ready result object.
 */
export async function getPracticeForDate(
  sql: Parameters<AppHandler>[0]["data"]["sql"],
  dateStr?: string | null,
) {
  const practiceDate = dateStr || todayISO();

  // Python weekday: Mon=0, our storage: Sun=0
  const d = new Date(practiceDate + "T12:00:00Z");
  const dayOfWeek = d.getUTCDay(); // JS getDay: Sun=0, matches our storage

  // Session containing this date
  const sessions = await sql`
    SELECT * FROM sessions
    WHERE start_date <= ${practiceDate} AND end_date >= ${practiceDate}
    LIMIT 1
  `;

  if (sessions.length === 0) {
    return { error: "No active session for this date", levels: [], date: practiceDate };
  }
  const currentSession = sessions[0];

  // Regular schedule levels for this day of week
  const levelsRegular = await sql`
    SELECT DISTINCT level, start_time, end_time
    FROM practice_schedules
    WHERE session_id = ${currentSession.id} AND day_of_week = ${dayOfWeek}
    ORDER BY level
  `;

  // Special practice dates (may not exist; catch gracefully)
  let levelsSpecial: typeof levelsRegular = [];
  try {
    levelsSpecial = await sql`
      SELECT DISTINCT level, start_time, end_time
      FROM special_practice_dates
      WHERE session_id = ${currentSession.id} AND practice_date = ${practiceDate}
      ORDER BY level
    `;
  } catch {
    // Table may not exist yet
  }

  // Merge: special overrides regular for same level
  const levelsMap: Record<string, (typeof levelsRegular)[0]> = {};
  for (const lr of levelsRegular) levelsMap[String(lr.level)] = lr;
  for (const ls of levelsSpecial) levelsMap[String(ls.level)] = ls;

  const levelsToday = Object.values(levelsMap);

  const resultLevels = [];

  for (const levelRow of levelsToday) {
    const level = String(levelRow.level);

    const athletes = await sql`
      SELECT id, name, current_level FROM athletes
      WHERE current_level = ${level} AND active = TRUE ORDER BY name
    `;

    const attRecords = await sql`
      SELECT athlete_id, status, notes, late_minutes
      FROM attendance WHERE practice_date = ${practiceDate} AND level = ${level}
    `;
    const attIndex: Record<number, { status: string; notes: string | null; late_minutes: number }> = {};
    for (const a of attRecords) {
      attIndex[a.athlete_id as number] = {
        status: String(a.status),
        notes: a.notes as string | null,
        late_minutes: Number(a.late_minutes ?? 0),
      };
    }

    resultLevels.push({
      level,
      start_time: String(levelRow.start_time),
      end_time: String(levelRow.end_time),
      athletes: athletes.map((a) => {
        const att = attIndex[a.id as number] ?? { status: "none", notes: null, late_minutes: 0 };
        return { id: a.id, name: a.name, status: att.status, notes: att.notes, late_minutes: att.late_minutes };
      }),
    });
  }

  return {
    date: practiceDate,
    day_of_week: dayOfWeek,
    session: currentSession,
    levels: resultLevels,
  };
}

export const onRequestGet: AppHandler = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const dateStr = url.searchParams.get("date");
  const result = await getPracticeForDate(sql, dateStr);
  return Response.json(result);
};
