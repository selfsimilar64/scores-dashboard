import { neon } from "@neondatabase/serverless";
import type { Env, AppData } from "./types";

export const onRequest: PagesFunction<Env, string, AppData> = async (context) => {
  context.data.sql = neon(context.env.DATABASE_URL);

  try {
    return await context.next();
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Internal server error";
    console.error("[API Error]", e);
    return Response.json({ error: message }, { status: 500 });
  }
};
