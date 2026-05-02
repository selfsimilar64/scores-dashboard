import type { AppHandler } from "./types";
import { toDateStr } from "./types";

export const onRequestGet: AppHandler = async ({ data: { sql } }) => {
  // Get the most recent meet
  const recentMeets = await sql`
    SELECT MeetName, MeetDate, CompYear
    FROM scores ORDER BY MeetDate DESC LIMIT 1
  `;

  if (recentMeets.length === 0) {
    return Response.json({ error: "No meets found", personal_bests: [] });
  }

  const { meetname: meetName, meetdate: meetDate, compyear: compYear } = recentMeets[0];

  // Single query: get all scores from the most recent meet WITH their previous bests,
  // eliminating the N+1 loop using a LATERAL join
  const rows = await sql`
    SELECT
      c.AthleteName, c.Level, c.Event, c.Score, c.Place,
      pb.prev_best
    FROM scores c
    LEFT JOIN LATERAL (
      SELECT MAX(Score) as prev_best
      FROM scores
      WHERE AthleteName = c.AthleteName
        AND Event = c.Event
        AND CompYear = c.CompYear
        AND MeetDate < c.MeetDate
        AND Score IS NOT NULL
    ) pb ON true
    WHERE c.MeetName = ${meetName} AND c.MeetDate = ${meetDate}
      AND c.Score IS NOT NULL
    ORDER BY c.AthleteName, c.Event
  `;

  const personalBests = rows
    .filter((r) => r.prev_best === null || Number(r.score) > Number(r.prev_best))
    .map((r) => ({
      athlete: r.athletename,
      level: r.level,
      event: r.event,
      score: Number(r.score),
      place: r.place,
      previous_best: r.prev_best != null ? Number(r.prev_best) : null,
      improvement: r.prev_best != null ? Math.round((Number(r.score) - Number(r.prev_best)) * 1000) / 1000 : null,
      is_first_meet: r.prev_best === null,
    }));

  return Response.json({
    meet_name: meetName,
    meet_date: toDateStr(meetDate),
    comp_year: compYear,
    personal_bests: personalBests,
  });
};
