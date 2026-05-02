import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestPut: PagesFunction<Env, string, AppData> = async ({ params, request, data: { sql } }) => {
  const sessionId = Number(params.session_id);
  const body = await request.json<{
    name: string; year: number; season: string; start_date: string; end_date: string;
  }>();

  await sql`
    UPDATE sessions SET name = ${body.name}, year = ${body.year}, season = ${body.season},
      start_date = ${body.start_date}, end_date = ${body.end_date}
    WHERE id = ${sessionId}
  `;

  return jsonResponse({ success: true });
};

export const onRequestDelete: PagesFunction<Env, string, AppData> = async ({ params, data: { sql } }) => {
  const sessionId = Number(params.session_id);
  await sql`DELETE FROM sessions WHERE id = ${sessionId}`;
  return jsonResponse({ success: true });
};
