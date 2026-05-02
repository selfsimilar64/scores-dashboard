import type { AppHandler } from "./types";
import { toDateStr } from "./types";

export const onRequestGet: AppHandler = async ({ data: { sql } }) => {
  const rows = await sql`
    SELECT MeetName, CompYear,
           MIN(MeetDate) as earliest_date,
           MAX(MeetDate) as latest_date,
           COUNT(DISTINCT MeetDate) as date_count
    FROM scores
    GROUP BY MeetName, CompYear
    ORDER BY MIN(MeetDate) DESC
  `;

  const meets = rows.map((r) => ({
    name: r.meetname,
    comp_year: r.compyear,
    earliest_date: toDateStr(r.earliest_date),
    latest_date: toDateStr(r.latest_date),
    date_count: Number(r.date_count),
  }));

  return Response.json(meets);
};
