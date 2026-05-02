import type { AppHandler } from "./types";
import { jsonResponse, todayISO, toDateStr } from "./types";

export const onRequestGet: AppHandler = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const athleteName = url.searchParams.get("name");
  const allLevels = url.searchParams.get("all_levels") === "true";

  if (!athleteName) {
    return jsonResponse({ error: "name parameter required" }, 400);
  }

  // Athlete info from athletes table
  const athleteRows = await sql`
    SELECT id, name, current_level, active, birthday FROM athletes WHERE name = ${athleteName}
  `;
  const athleteRow = athleteRows[0] ?? null;

  // Most recent score to determine current level
  const recentScoreRows = await sql`
    SELECT Level, CompYear FROM scores
    WHERE AthleteName = ${athleteName} AND Score IS NOT NULL
    ORDER BY MeetDate DESC LIMIT 1
  `;

  if (recentScoreRows.length === 0) {
    const athleteInfo = {
      name: athleteName,
      level: athleteRow?.current_level ?? null,
      birthday: null, age: null, active: true,
    };
    return Response.json({ error: "No scores found for this athlete", athlete: athleteInfo });
  }

  const level = recentScoreRows[0].level;
  const compYear = recentScoreRows[0].compyear;

  // Birthday / age calculation
  let birthday: string | null = null;
  let age: number | null = null;
  if (athleteRow?.birthday) {
    birthday = toDateStr(athleteRow.birthday);
    const bd = new Date(birthday);
    const now = new Date(todayISO());
    age = now.getFullYear() - bd.getFullYear() -
      (now.getMonth() < bd.getMonth() || (now.getMonth() === bd.getMonth() && now.getDate() < bd.getDate()) ? 1 : 0);
  }

  // Seasons at level
  const [seasonsRow] = await sql`
    SELECT COUNT(DISTINCT CompYear) as cnt FROM scores WHERE AthleteName = ${athleteName} AND Level = ${level}
  `;
  const seasonsAtLevel = Number(seasonsRow.cnt);

  // Level history
  const levelHistoryRows = await sql`
    SELECT Level, CompYear
    FROM (
      SELECT Level, CompYear, MAX(MeetDate) as last_meet
      FROM scores WHERE AthleteName = ${athleteName} AND Score IS NOT NULL
      GROUP BY Level, CompYear
    ) sub
    ORDER BY last_meet DESC
  `;

  const athleteInfo = {
    name: athleteRow?.name ?? athleteName,
    level,
    birthday,
    age,
    active: athleteRow?.active ?? true,
    seasons_at_level: seasonsAtLevel,
    level_history: levelHistoryRows.map((r) => r.level),
  };

  // Build meets + scores queries depending on all_levels toggle
  let meets;
  let rawScores;

  if (allLevels) {
    meets = await sql`
      SELECT DISTINCT MeetName, MeetDate, CompYear
      FROM scores WHERE AthleteName = ${athleteName}
      ORDER BY MeetDate ASC
    `;
    // Single query with LATERAL joins for PB annotations
    rawScores = await sql`
      SELECT
        c.AthleteName, c.Level, c.Event, c.Score, c.Place,
        c.MeetName, c.MeetDate, c.CompYear,
        yb.score as year_best,
        ab.score as alltime_best
      FROM scores c
      LEFT JOIN LATERAL (
        SELECT Score FROM scores
        WHERE AthleteName = c.AthleteName AND Event = c.Event
          AND CompYear = c.CompYear AND MeetDate < c.MeetDate
          AND Score IS NOT NULL
        ORDER BY Score DESC LIMIT 1
      ) yb ON true
      LEFT JOIN LATERAL (
        SELECT Score FROM scores
        WHERE AthleteName = c.AthleteName AND Event = c.Event
          AND Level = c.Level AND CompYear != c.CompYear
          AND Score IS NOT NULL
        ORDER BY Score DESC LIMIT 1
      ) ab ON true
      WHERE c.AthleteName = ${athleteName}
      ORDER BY c.MeetDate ASC, c.Event
    `;
  } else {
    meets = await sql`
      SELECT DISTINCT MeetName, MeetDate, CompYear
      FROM scores WHERE AthleteName = ${athleteName} AND Level = ${level}
      ORDER BY MeetDate ASC
    `;
    rawScores = await sql`
      SELECT
        c.AthleteName, c.Level, c.Event, c.Score, c.Place,
        c.MeetName, c.MeetDate, c.CompYear,
        yb.score as year_best,
        ab.score as alltime_best
      FROM scores c
      LEFT JOIN LATERAL (
        SELECT Score FROM scores
        WHERE AthleteName = c.AthleteName AND Event = c.Event
          AND CompYear = c.CompYear AND MeetDate < c.MeetDate
          AND Score IS NOT NULL
        ORDER BY Score DESC LIMIT 1
      ) yb ON true
      LEFT JOIN LATERAL (
        SELECT Score FROM scores
        WHERE AthleteName = c.AthleteName AND Event = c.Event
          AND Level = c.Level AND CompYear != c.CompYear
          AND Score IS NOT NULL
        ORDER BY Score DESC LIMIT 1
      ) ab ON true
      WHERE c.AthleteName = ${athleteName} AND c.Level = ${level}
      ORDER BY c.MeetDate ASC, c.Event
    `;
  }

  const allScores = rawScores.map((r) => {
    const currentScore = r.score != null ? Number(r.score) : null;
    const yearBest = r.year_best != null ? Number(r.year_best) : null;
    const prevYearBest = r.alltime_best != null ? Number(r.alltime_best) : null;
    const meetDateStr = toDateStr(r.meetdate);

    if (currentScore === null) {
      return {
        athlete: r.athletename, level: r.level, event: r.event,
        score: null, place: r.place,
        meet_name: r.meetname, meet_date: meetDateStr, comp_year: r.compyear,
      };
    }

    // All-time best at level (max of year_best and prev_year_best)
    let alltimeBest: number | null = null;
    if (yearBest != null && prevYearBest != null) alltimeBest = Math.max(yearBest, prevYearBest);
    else if (yearBest != null) alltimeBest = yearBest;
    else if (prevYearBest != null) alltimeBest = prevYearBest;

    const isFirstYear = prevYearBest === null;
    const isFirstMeet = yearBest === null;
    const isAlltimePb = !isFirstYear && alltimeBest !== null && currentScore > alltimeBest;
    const isYearPb = !isFirstMeet && yearBest !== null && currentScore > yearBest;

    return {
      athlete: r.athletename, level: r.level, event: r.event,
      score: currentScore, place: r.place,
      meet_name: r.meetname, meet_date: meetDateStr, comp_year: r.compyear,
      is_first_year_at_level: isFirstYear,
      is_first_meet_of_year: isFirstMeet,
      is_year_pb: isYearPb,
      is_alltime_pb: isAlltimePb,
      year_best: yearBest,
      alltime_best: alltimeBest,
      year_improvement: isYearPb && yearBest != null ? Math.round((currentScore - yearBest) * 1000) / 1000 : null,
      alltime_improvement: isAlltimePb && alltimeBest != null ? Math.round((currentScore - alltimeBest) * 1000) / 1000 : null,
      seasons_at_level: seasonsAtLevel,
    };
  });

  return Response.json({
    athlete: athleteInfo,
    comp_year: compYear,
    meets: meets.map((m) => ({
      name: m.meetname,
      date: toDateStr(m.meetdate),
      comp_year: m.compyear,
    })),
    scores: allScores,
  });
};
