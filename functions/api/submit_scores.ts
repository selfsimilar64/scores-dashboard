import type { AppHandler } from "./types";
import { jsonResponse } from "./types";

export const onRequestPost: AppHandler = async ({ request, data: { sql } }) => {
  const body = await request.json<{
    meetName: string;
    meetDate: string;
    compYear: string;
    athleteName: string;
    level: string;
    events: { event: string; score: string | number | null; place: string | number | null }[];
  }>();

  const { meetName, meetDate, compYear, athleteName, level, events = [] } = body;

  if (!meetName || !meetDate || !compYear || !athleteName || !level) {
    return jsonResponse({ error: "Missing required fields" }, 400);
  }

  let insertedCount = 0;

  for (const ev of events) {
    if (ev.score == null || ev.score === "") continue;

    const scoreValue = Number(ev.score);
    if (isNaN(scoreValue)) continue;

    const placeValue = ev.place ? Number(ev.place) : null;

    await sql`
      INSERT INTO scores (AthleteName, Level, CompYear, MeetName, MeetDate, Event, StartValue, Score, Place)
      VALUES (${athleteName}, ${level}, ${compYear}, ${meetName}, ${meetDate}, ${ev.event}, NULL, ${scoreValue}, ${placeValue})
    `;
    insertedCount++;
  }

  return jsonResponse({
    success: true,
    message: `Inserted ${insertedCount} score(s) for ${athleteName}`,
    inserted_count: insertedCount,
  });
};
