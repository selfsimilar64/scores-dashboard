import type { AppHandler } from "./types";
import { jsonResponse, toDateStr } from "./types";

export const onRequestGet: AppHandler = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const meetName = url.searchParams.get("meet_name");
  let compYear = url.searchParams.get("comp_year");
  const meetDateLegacy = url.searchParams.get("meet_date");

  if (!meetName) {
    return jsonResponse({ error: "meet_name is required" }, 400);
  }

  // Legacy support: derive comp_year from meet_date
  if (!compYear && meetDateLegacy) {
    const [row] = await sql`
      SELECT CompYear FROM scores
      WHERE MeetName = ${meetName} AND MeetDate = ${meetDateLegacy}
      LIMIT 1
    `;
    if (row) compYear = row.compyear;
  }

  if (!compYear) {
    return jsonResponse({ error: "comp_year is required (or provide meet_date)" }, 400);
  }

  // Get all dates for this meet
  const dateRows = await sql`
    SELECT DISTINCT MeetDate FROM scores
    WHERE MeetName = ${meetName} AND CompYear = ${compYear}
    ORDER BY MeetDate
  `;

  if (dateRows.length === 0) {
    return Response.json({ error: "Meet not found", scores: [] });
  }

  const meetDates = dateRows.map((r) => toDateStr(r.meetdate));
  const earliestDate = dateRows[0].meetdate;

  // Seasons-at-level lookup (single query)
  const seasonsRows = await sql`
    SELECT AthleteName, Level, COUNT(DISTINCT CompYear) as season_count
    FROM scores
    WHERE (AthleteName, Level) IN (
      SELECT DISTINCT AthleteName, Level FROM scores
      WHERE MeetName = ${meetName} AND CompYear = ${compYear}
    )
    GROUP BY AthleteName, Level
  `;
  const seasonsLookup: Record<string, number> = {};
  for (const r of seasonsRows) {
    seasonsLookup[`${r.athletename}|${r.level}`] = Number(r.season_count);
  }

  // Single query: all meet scores with year-best and alltime-best via LATERAL joins
  const rows = await sql`
    SELECT
      c.AthleteName, c.Level, c.Event, c.Score, c.Place,
      yb.score   as year_best,
      yb.meetname as year_best_meet,
      yb.meetdate as year_best_date,
      ab.score   as alltime_best,
      ab.meetname as alltime_best_meet,
      ab.meetdate as alltime_best_date
    FROM scores c
    LEFT JOIN LATERAL (
      SELECT Score, MeetName, MeetDate
      FROM scores
      WHERE AthleteName = c.AthleteName AND Event = c.Event
        AND CompYear = ${compYear} AND MeetDate < ${earliestDate}
        AND Score IS NOT NULL
      ORDER BY Score DESC LIMIT 1
    ) yb ON true
    LEFT JOIN LATERAL (
      SELECT Score, MeetName, MeetDate
      FROM scores
      WHERE AthleteName = c.AthleteName AND Event = c.Event
        AND Level = c.Level AND CompYear != ${compYear}
        AND Score IS NOT NULL
      ORDER BY Score DESC LIMIT 1
    ) ab ON true
    WHERE c.MeetName = ${meetName} AND c.CompYear = ${compYear}
    ORDER BY c.AthleteName, c.Event
  `;

  const allScores = rows.map((r) => {
    const currentScore = r.score != null ? Number(r.score) : null;
    const yearBest = r.year_best != null ? Number(r.year_best) : null;
    const prevYearBest = r.alltime_best != null ? Number(r.alltime_best) : null;

    if (currentScore === null) {
      return {
        athlete: r.athletename, level: r.level, event: r.event,
        score: null, place: r.place,
        seasons_at_level: seasonsLookup[`${r.athletename}|${r.level}`] ?? 1,
      };
    }

    // True all-time best = max of year_best and prev_year_best
    let alltimeBest: number | null = null;
    let alltimeBestMeet: string | null = null;
    let alltimeBestDate: string | null = null;

    if (yearBest != null && prevYearBest != null) {
      if (yearBest >= prevYearBest) {
        alltimeBest = yearBest;
        alltimeBestMeet = r.year_best_meet;
        alltimeBestDate = toDateStr(r.year_best_date);
      } else {
        alltimeBest = prevYearBest;
        alltimeBestMeet = r.alltime_best_meet;
        alltimeBestDate = toDateStr(r.alltime_best_date);
      }
    } else if (yearBest != null) {
      alltimeBest = yearBest;
      alltimeBestMeet = r.year_best_meet;
      alltimeBestDate = toDateStr(r.year_best_date);
    } else if (prevYearBest != null) {
      alltimeBest = prevYearBest;
      alltimeBestMeet = r.alltime_best_meet;
      alltimeBestDate = toDateStr(r.alltime_best_date);
    }

    const isFirstYearAtLevel = prevYearBest === null;
    const isFirstMeetOfYear = yearBest === null;

    const isAlltimePb = !isFirstYearAtLevel && alltimeBest !== null && currentScore > alltimeBest;
    const isYearPb = !isFirstMeetOfYear && yearBest !== null && currentScore > yearBest;

    return {
      athlete: r.athletename,
      level: r.level,
      event: r.event,
      score: currentScore,
      place: r.place,
      is_first_year_at_level: isFirstYearAtLevel,
      is_first_meet_of_year: isFirstMeetOfYear,
      is_year_pb: isYearPb,
      is_alltime_pb: isAlltimePb,
      year_best: yearBest,
      year_best_meet: r.year_best_meet ?? null,
      year_best_date: r.year_best_date ? toDateStr(r.year_best_date) : null,
      alltime_best: alltimeBest,
      alltime_best_meet: alltimeBestMeet,
      alltime_best_date: alltimeBestDate,
      year_improvement: isYearPb && yearBest != null ? Math.round((currentScore - yearBest) * 1000) / 1000 : null,
      alltime_improvement: isAlltimePb && alltimeBest != null ? Math.round((currentScore - alltimeBest) * 1000) / 1000 : null,
      seasons_at_level: seasonsLookup[`${r.athletename}|${r.level}`] ?? 1,
    };
  });

  return Response.json({
    meet_name: meetName,
    meet_dates: meetDates,
    comp_year: compYear,
    scores: allScores,
  });
};
