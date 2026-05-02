import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestGet: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const url = new URL(request.url);
  const level = url.searchParams.get("level");
  const activeOnly = url.searchParams.get("active") !== "false";

  let rows;
  if (level && activeOnly) {
    rows = await sql`
      SELECT id, name, current_level, active, birthday
      FROM athletes WHERE current_level = ${level} AND active = TRUE ORDER BY name`;
  } else if (level) {
    rows = await sql`
      SELECT id, name, current_level, active, birthday
      FROM athletes WHERE current_level = ${level} ORDER BY name`;
  } else if (activeOnly) {
    rows = await sql`
      SELECT id, name, current_level, active, birthday
      FROM athletes WHERE active = TRUE ORDER BY name`;
  } else {
    rows = await sql`
      SELECT id, name, current_level, active, birthday
      FROM athletes ORDER BY name`;
  }

  return Response.json(rows);
};

export const onRequestPost: PagesFunction<Env, string, AppData> = async ({ request, data: { sql } }) => {
  const body = await request.json<{ name: string; current_level?: string; birthday?: string }>();

  if (!body.name) {
    return jsonResponse({ error: "Name is required" }, 400);
  }

  const birthday = body.birthday || null;

  try {
    const [row] = await sql`
      INSERT INTO athletes (name, current_level, birthday)
      VALUES (${body.name}, ${body.current_level ?? null}, ${birthday})
      RETURNING id
    `;
    return jsonResponse({ success: true, id: row.id });
  } catch (e: unknown) {
    return jsonResponse({ error: e instanceof Error ? e.message : "Insert failed" }, 400);
  }
};
