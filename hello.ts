import crypto from "node:crypto";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { Pool } from "pg";
import { attachDatabasePool } from "@neon/functions";
import { createRealtime, rawSql } from "@neon/realtime/server";
import { createRemoteJWKSet, jwtVerify } from "jose";

const connectionString = (process.env.DATABASE_URL || "").replace(
  "sslmode=require",
  "sslmode=verify-full"
);

// Module-scope pg Pool reused across requests on the same Neon Function isolate
const pool = new Pool({ connectionString, max: 5 });
attachDatabasePool(pool);

function getDbNameFromUrl(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl);
    return parsed.pathname.replace(/^\//, "") || "neondb";
  } catch {
    return "neondb";
  }
}

const dbName = getDbNameFromUrl(process.env.DATABASE_URL || "");
const realtimeSecret = process.env.NEON_REALTIME_SECRET || process.env.REALTIME_SECRET || "";
const realtimeUrl = process.env.NEON_REALTIME_URL || process.env.REALTIME_URL || "";
const realtime = realtimeSecret
  ? createRealtime({ secret: realtimeSecret, db: dbName })
  : null;

const authBaseUrl = process.env.NEON_AUTH_BASE_URL || "";
const authJwksUrl = process.env.NEON_AUTH_JWKS_URL || (authBaseUrl ? `${authBaseUrl}/.well-known/jwks.json` : "");
const authOrigin = authBaseUrl ? new URL(authBaseUrl).origin : "";
const jwks = authJwksUrl ? createRemoteJWKSet(new URL(authJwksUrl)) : null;

interface CampaignActivityRow {
  id: string;
  user_id: string;
  name: string;
  record_type: string;
  status: string;
  summary: string;
  created_at: string;
}

async function verifyNeonAuthBearer(authHeader: string | undefined): Promise<{ sub: string; email?: string } | null> {
  if (!authHeader || !authHeader.toLowerCase().startsWith("bearer ") || !jwks || !authOrigin) {
    return null;
  }
  const token = authHeader.slice(7).trim();
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, jwks, { issuer: authOrigin });
    if (!payload.sub) return null;
    return {
      sub: String(payload.sub),
      email: typeof payload.email === "string" ? payload.email : undefined,
    };
  } catch {
    return null;
  }
}

function verifyServerSealSignature(userId: string, signatureHex: string | undefined): boolean {
  if (!realtimeSecret || !userId || !signatureHex) return false;
  const expected = crypto
    .createHmac("sha256", realtimeSecret)
    .update(`seal:${userId}`)
    .digest("hex");
  const actualBuf = Buffer.from(signatureHex.trim(), "utf8");
  const expectedBuf = Buffer.from(expected, "utf8");
  if (actualBuf.length !== expectedBuf.length) return false;
  return crypto.timingSafeEqual(actualBuf, expectedBuf);
}

const app = new Hono();

app.use(
  "*",
  cors({
    origin: "*",
    allowMethods: ["GET", "POST", "OPTIONS"],
    allowHeaders: ["Authorization", "Content-Type", "X-Server-Signature"],
  })
);

app.get("/", async (c) => {
  try {
    const { rows } = await pool.query<{ db: string; now: string }>(
      "SELECT current_database() AS db, now()::text AS now"
    );
    return c.json({
      service: "Campaign Intelligence Neon Function",
      status: "ok",
      branch: process.env.NEON_BRANCH || null,
      branch_id: process.env.NEON_BRANCH_ID || null,
      postgres: {
        connected: true,
        database: rows[0]?.db || dbName,
        server_time: rows[0]?.now || null,
      },
      services: {
        postgres: Boolean(process.env.DATABASE_URL),
        auth: Boolean(authJwksUrl),
        realtime: Boolean(realtime),
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return c.json({ status: "error", detail: message }, 500);
  }
});

app.get("/auth/verify", async (c) => {
  const identity = await verifyNeonAuthBearer(c.req.header("authorization"));
  if (!identity) {
    return c.json({ authenticated: false, detail: "Missing or invalid Neon Auth Bearer token." }, 401);
  }
  return c.json({ authenticated: true, user: identity });
});

app.post("/realtime/seal", async (c) => {
  if (!realtime) {
    return c.json({ detail: "Neon Realtime is not configured on this branch." }, 503);
  }

  let body: { user_id?: string } = {};
  try {
    body = await c.req.json<{ user_id?: string }>();
  } catch {
    body = {};
  }

  // Authorize via either Neon Auth JWT or trusted backend HMAC signature
  let authorizedUserId: string | null = null;
  const neonIdentity = await verifyNeonAuthBearer(c.req.header("authorization"));
  if (neonIdentity) {
    authorizedUserId = neonIdentity.sub;
  } else if (body.user_id && verifyServerSealSignature(body.user_id, c.req.header("x-server-signature"))) {
    authorizedUserId = body.user_id;
  }

  if (!authorizedUserId) {
    return c.json({ detail: "Unauthorized realtime seal request." }, 401);
  }

  const query = rawSql<CampaignActivityRow>(
    `SELECT id, user_id, name, record_type, status, summary, created_at
     FROM campaign_records
     WHERE user_id = $1
     ORDER BY created_at DESC
     LIMIT 20`,
    [authorizedUserId]
  );

  const sealedQuery = await realtime.seal({ query });
  return c.json({
    realtime_url: realtimeUrl || null,
    sealed_query: sealedQuery,
  });
});

export default app;
