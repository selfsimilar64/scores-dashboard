import type { Env, AppData } from "../types";
import { jsonResponse } from "../types";

export const onRequestDelete: PagesFunction<Env, string, AppData> = async ({ params, data: { sql } }) => {
  const dateId = Number(params.date_id);
  await sql`DELETE FROM special_practice_dates WHERE id = ${dateId}`;
  return jsonResponse({ success: true });
};
