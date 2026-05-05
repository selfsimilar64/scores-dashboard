import type { Env, AppData } from "../../types";
import { jsonResponse, toDateStr, toNoonUTC } from "../../types";

export const onRequestGet: PagesFunction<Env, string, AppData> = async ({ params, request, data: { sql } }) => {
  const sessionId = Number(params.session_id);
  const url = new URL(request.url);
  const level = url.searchParams.get("level");

  // Session info
  const sessionRows = await sql`SELECT * FROM sessions WHERE id = ${sessionId}`;
  if (sessionRows.length === 0) {
    return jsonResponse({ error: "Session not found" }, 404);
  }
  const session = sessionRows[0];

  // Practice schedules for this session
  let schedules;
  if (level) {
    schedules = await sql`
      SELECT DISTINCT level, day_of_week FROM practice_schedules
      WHERE session_id = ${sessionId} AND level = ${level}
    `;
  } else {
    schedules = await sql`
      SELECT DISTINCT level, day_of_week FROM practice_schedules
      WHERE session_id = ${sessionId}
    `;
  }

  // Build per-level sets of practice days-of-week
  const scheduleByLevel: Record<string, Set<number>> = {};
  for (const s of schedules) {
    const lvl = String(s.level);
    (scheduleByLevel[lvl] ??= new Set()).add(Number(s.day_of_week));
  }

  // Generate practice dates per level
  const practiceDatesByLevel: Record<string, string[]> = {};
  const startDate = toNoonUTC(session.start_date);
  const endDate = toNoonUTC(session.end_date);

  const cur = new Date(startDate);
  while (cur <= endDate) {
    const dow = cur.getUTCDay();
    const iso = cur.toISOString().split("T")[0];
    for (const [lvl, days] of Object.entries(scheduleByLevel)) {
      if (days.has(dow)) {
        (practiceDatesByLevel[lvl] ??= []).push(iso);
      }
    }
    cur.setUTCDate(cur.getUTCDate() + 1);
  }

  // Attendance records
  let attRecords;
  if (level) {
    attRecords = await sql`SELECT * FROM attendance WHERE session_id = ${sessionId} AND level = ${level}`;
  } else {
    attRecords = await sql`SELECT * FROM attendance WHERE session_id = ${sessionId}`;
  }

  const attIndex: Record<string, (typeof attRecords)[0]> = {};
  for (const rec of attRecords) {
    attIndex[`${rec.athlete_id}|${toDateStr(rec.practice_date)}`] = rec;
  }

  // Athletes
  let athletes;
  if (level) {
    athletes = await sql`
      SELECT * FROM athletes WHERE active = TRUE AND current_level = ${level} ORDER BY current_level, name
    `;
  } else {
    athletes = await sql`SELECT * FROM athletes WHERE active = TRUE ORDER BY current_level, name`;
  }

  // Build result
  const levels: Record<string, { dates: string[]; athletes: unknown[] }> = {};
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  for (const athlete of athletes) {
    const lvl = String(athlete.current_level);
    if (!levels[lvl]) {
      levels[lvl] = { dates: practiceDatesByLevel[lvl] ?? [], athletes: [] };
    }

    const dates = practiceDatesByLevel[lvl] ?? [];
    const attendanceData: unknown[] = [];
    let presentCount = 0;
    let recordedCount = 0;
    const dowCounts: Record<number, { present: number; total: number }> = {};
    for (let i = 0; i < 7; i++) dowCounts[i] = { present: 0, total: 0 };

    for (const d of dates) {
      const key = `${athlete.id}|${d}`;
      const rec = attIndex[key];
      const dateObj = new Date(d + "T12:00:00Z");
      const dow = dateObj.getUTCDay();

      if (rec) {
        const status = String(rec.status);
        if (status === "present" || status === "absent" || status === "partial") {
          recordedCount++;
          dowCounts[dow].total++;
          if (status === "present") { presentCount++; dowCounts[dow].present++; }
          else if (status === "partial") { presentCount += 0.5; dowCounts[dow].present += 0.5; }
        }
        attendanceData.push({
          date: d, status, notes: rec.notes ?? null,
          late_minutes: Number(rec.late_minutes ?? 0),
        });
      } else {
        attendanceData.push({ date: d, status: "none", notes: null, late_minutes: 0 });
      }
    }

    const totalPct = recordedCount > 0 ? Math.round((presentCount / recordedCount) * 100) : 0;
    const dowPcts: Record<string, number> = {};
    for (const [dow, counts] of Object.entries(dowCounts)) {
      if (counts.total > 0) {
        dowPcts[dayNames[Number(dow)]] = Math.round((counts.present / counts.total) * 100);
      }
    }

    levels[lvl].athletes.push({
      id: athlete.id, name: athlete.name,
      attendance: attendanceData, total_pct: totalPct, dow_pcts: dowPcts,
    });
  }

  return Response.json({ session, levels });
};
