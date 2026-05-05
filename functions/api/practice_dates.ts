import type { AppHandler } from "./types";
import { todayISO, toDateStr, toNoonUTC } from "./types";

export const onRequestGet: AppHandler = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("session_id");

  let session;
  if (sessionId) {
    const rows = await sql`SELECT * FROM sessions WHERE id = ${Number(sessionId)}`;
    session = rows[0];
  } else {
    const today = todayISO();
    const rows = await sql`
      SELECT * FROM sessions
      WHERE start_date <= ${today} AND end_date >= ${today}
      LIMIT 1
    `;
    session = rows[0];
  }

  if (!session) {
    return Response.json({ dates: [], error: "No session found" });
  }

  // Days of week with practice
  const dowRows = await sql`
    SELECT DISTINCT day_of_week FROM practice_schedules WHERE session_id = ${session.id}
  `;
  const practiceDays = new Set(dowRows.map((r) => Number(r.day_of_week)));

  // Special practice dates
  const specialDates = new Set<string>();
  try {
    const spRows = await sql`
      SELECT DISTINCT practice_date FROM special_practice_dates WHERE session_id = ${session.id}
    `;
    for (const r of spRows) specialDates.add(toDateStr(r.practice_date));
  } catch {
    // Table may not exist
  }

  // Generate all practice dates within the session range
  const dates: string[] = [];
  const start = toNoonUTC(session.start_date);
  const end = toNoonUTC(session.end_date);

  const current = new Date(start);
  while (current <= end) {
    const dow = current.getUTCDay(); // Sun=0
    const iso = current.toISOString().split("T")[0];
    if (practiceDays.has(dow) || specialDates.has(iso)) {
      dates.push(iso);
    }
    current.setUTCDate(current.getUTCDate() + 1);
  }

  return Response.json({ dates, session });
};
