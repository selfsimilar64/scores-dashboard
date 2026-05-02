import type { AppHandler } from "./types";
import { getPracticeForDate } from "./practice_for_date";

export const onRequestGet: AppHandler = async ({ data: { sql } }) => {
  const result = await getPracticeForDate(sql, null);
  return Response.json(result);
};
