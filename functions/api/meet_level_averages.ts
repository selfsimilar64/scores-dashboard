import type { AppHandler } from "./types";
import { toDateStr } from "./types";

function median(nums: number[]): number {
  const sorted = [...nums].sort((a, b) => a - b);
  const n = sorted.length;
  if (n === 0) return 0;
  if (n % 2 === 0) return (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
  return sorted[Math.floor(n / 2)];
}

const LEVEL_ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "XB", "XS", "XG", "XP", "XD", "XSA"];
const TEAM_EVENTS = ["Vault", "Bars", "Beam", "Floor"];

export const onRequestGet: AppHandler = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const compYear = url.searchParams.get("comp_year") || "2026";

  // All comp years for dropdown
  const compYearRows = await sql`SELECT DISTINCT CompYear FROM scores ORDER BY CompYear DESC`;
  const allCompYears = compYearRows.map((r) => r.compyear);

  // All meets for this comp year
  const meetsRaw = await sql`
    SELECT MeetName, MIN(MeetDate) as EarliestDate, CompYear
    FROM scores WHERE CompYear = ${compYear}
    GROUP BY MeetName, CompYear
    ORDER BY MIN(MeetDate) ASC
  `;

  // Sort chronologically by earliest date (ascending)
  const meets = [...meetsRaw].sort((a, b) => {
    return toDateStr(a.earliestdate) < toDateStr(b.earliestdate) ? -1 : 1;
  });

  // Bulk-fetch ALL AA scores and ALL event scores for this comp year in two queries
  const allAAScores = await sql`
    SELECT MeetName, Level, AthleteName, Score
    FROM scores
    WHERE CompYear = ${compYear} AND Event = 'All Around' AND Score IS NOT NULL
    ORDER BY Score DESC
  `;

  const allEventScores = await sql`
    SELECT MeetName, Level, Event, AthleteName, Score
    FROM scores
    WHERE CompYear = ${compYear} AND Event IN ('Vault', 'Bars', 'Beam', 'Floor') AND Score IS NOT NULL
    ORDER BY Score DESC
  `;

  // Also get all meet dates
  const allMeetDates = await sql`
    SELECT DISTINCT MeetName, MeetDate
    FROM scores WHERE CompYear = ${compYear}
    ORDER BY MeetDate
  `;

  // Index data by meet
  type AAEntry = { athletename: string; score: number };
  type EventEntry = { athletename: string; score: number; level: string };

  const aaBymeetLevel: Record<string, AAEntry[]> = {};
  for (const r of allAAScores) {
    const key = `${r.meetname}|${r.level}`;
    (aaBymeetLevel[key] ??= []).push({ athletename: r.athletename, score: Number(r.score) });
  }

  const eventByMeetLevelEvent: Record<string, EventEntry[]> = {};
  for (const r of allEventScores) {
    const key = `${r.meetname}|${r.level}|${r.event}`;
    (eventByMeetLevelEvent[key] ??= []).push({ athletename: r.athletename, score: Number(r.score), level: r.level });
  }

  const datesByMeet: Record<string, string[]> = {};
  for (const r of allMeetDates) {
    (datesByMeet[String(r.meetname)] ??= []).push(toDateStr(r.meetdate));
  }

  // Build results
  const results = meets.map((meet) => {
    const meetName = String(meet.meetname);
    const meetData: Record<string, unknown> = {
      meet_name: meetName,
      meet_dates: datesByMeet[meetName] ?? [],
      earliest_date: toDateStr(meet.earliestdate),
      comp_year: meet.compyear,
      levels: {} as Record<string, unknown>,
      gymfest_avg: null,
      gymfest_median: null,
      gymfest_count: 0,
      gymfest_event_top3: null,
      gymfest_team_score: null,
    };

    const levels = meetData.levels as Record<string, unknown>;
    const allAAForGymfest: number[] = [];
    const allEventForGymfest: Record<string, { athlete: string; score: number; level: string }[]> = {};
    for (const ev of TEAM_EVENTS) allEventForGymfest[ev] = [];

    for (const lvl of LEVEL_ORDER) {
      const aaKey = `${meetName}|${lvl}`;
      const aaEntries = aaBymeetLevel[aaKey];

      if (!aaEntries || aaEntries.length === 0) {
        levels[lvl] = null;
        continue;
      }

      const scoresList = aaEntries.map((e) => e.score);
      const avg = scoresList.reduce((a, b) => a + b, 0) / scoresList.length;

      // Team score: sum of top 3 per event
      let teamScore = 0;
      let hasTeamScore = true;
      const eventTop3: Record<string, { athlete: string; score: number }[]> = {};
      const eventScoresForMedian: Record<string, number[]> = {};

      for (const event of TEAM_EVENTS) {
        const evKey = `${meetName}|${lvl}|${event}`;
        const entries = eventByMeetLevelEvent[evKey] ?? [];
        eventScoresForMedian[event] = entries.map((e) => e.score);
        if (entries.length >= 3) {
          const top3 = entries.slice(0, 3);
          eventTop3[event] = top3.map((e) => ({ athlete: e.athletename, score: e.score }));
          teamScore += top3.reduce((s, e) => s + e.score, 0);
        } else {
          hasTeamScore = false;
        }
      }

      // Median: sum of per-event medians (Vault + Bars + Beam + Floor)
      const eventMedians = TEAM_EVENTS.map((ev) =>
        eventScoresForMedian[ev]?.length > 0 ? median(eventScoresForMedian[ev]) : null
      );
      const med = eventMedians.every((m) => m !== null)
        ? (eventMedians as number[]).reduce((a, b) => a + b, 0)
        : null;

      levels[lvl] = {
        avg, median: med, count: scoresList.length,
        team_score: hasTeamScore ? teamScore : null,
        event_top3: hasTeamScore ? eventTop3 : null,
      };

      allAAForGymfest.push(...scoresList);
      for (const event of TEAM_EVENTS) {
        const evKey = `${meetName}|${lvl}|${event}`;
        for (const e of (eventByMeetLevelEvent[evKey] ?? [])) {
          allEventForGymfest[event].push({ athlete: e.athletename, score: e.score, level: lvl });
        }
      }
    }

    // Gymfest totals
    if (allAAForGymfest.length > 0) {
      meetData.gymfest_avg = allAAForGymfest.reduce((a, b) => a + b, 0) / allAAForGymfest.length;
      meetData.gymfest_count = allAAForGymfest.length;

      // Gymfest median: sum of per-event medians across all levels
      const gymfestEventMedians = TEAM_EVENTS.map((ev) =>
        allEventForGymfest[ev].length > 0 ? median(allEventForGymfest[ev].map((e) => e.score)) : null
      );
      meetData.gymfest_median = gymfestEventMedians.every((m) => m !== null)
        ? (gymfestEventMedians as number[]).reduce((a, b) => a + b, 0)
        : null;

      let gymfestTeamScore = 0;
      let hasGymfestTeam = true;
      const gymfestTop3: Record<string, { athlete: string; score: number; level: string }[]> = {};

      for (const event of TEAM_EVENTS) {
        const sorted = allEventForGymfest[event].sort((a, b) => b.score - a.score);
        if (sorted.length >= 3) {
          gymfestTop3[event] = sorted.slice(0, 3);
          gymfestTeamScore += sorted.slice(0, 3).reduce((s, e) => s + e.score, 0);
        } else {
          hasGymfestTeam = false;
          break;
        }
      }

      meetData.gymfest_event_top3 = hasGymfestTeam ? gymfestTop3 : null;
      meetData.gymfest_team_score = hasGymfestTeam ? gymfestTeamScore : null;
    }

    return meetData;
  });

  // Determine which levels have data
  const levelsWithData = LEVEL_ORDER.filter((lvl) =>
    results.some((m) => (m.levels as Record<string, unknown>)[lvl] != null)
  );

  return Response.json({
    level_order: levelsWithData,
    all_comp_years: allCompYears,
    comp_year: compYear,
    meets: results,
  });
};
