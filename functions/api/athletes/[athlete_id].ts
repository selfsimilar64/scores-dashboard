import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestPut: PagesFunction<Env, string, AppData> = async ({ params, request, data: { sql } }) => {
  const athleteId = Number(params.athlete_id);
  const body = await request.json<Record<string, unknown>>();

  const sets: string[] = [];
  const values: unknown[] = [];

  if ("current_level" in body) { sets.push("current_level"); values.push(body.current_level); }
  if ("active" in body) { sets.push("active"); values.push(body.active); }
  if ("name" in body) { sets.push("name"); values.push(body.name); }
  if ("birthday" in body) { sets.push("birthday"); values.push(body.birthday || null); }

  if (sets.length === 0) {
    return jsonResponse({ success: true });
  }

  // Build dynamic UPDATE using individual field queries to stay compatible
  // with the tagged template literal driver (can't interpolate column names)
  for (let i = 0; i < sets.length; i++) {
    const col = sets[i];
    const val = values[i];
    if (col === "current_level") await sql`UPDATE athletes SET current_level = ${val as string} WHERE id = ${athleteId}`;
    else if (col === "active") await sql`UPDATE athletes SET active = ${val as boolean} WHERE id = ${athleteId}`;
    else if (col === "name") await sql`UPDATE athletes SET name = ${val as string} WHERE id = ${athleteId}`;
    else if (col === "birthday") await sql`UPDATE athletes SET birthday = ${val as string | null} WHERE id = ${athleteId}`;
  }

  return jsonResponse({ success: true });
};
