import crypto from "node:crypto";
import {
  AbortMultipartUploadCommand,
  CompleteMultipartUploadCommand,
  CreateMultipartUploadCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  PutObjectCommand,
  S3Client,
  UploadPartCommand,
} from "@aws-sdk/client-s3";
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

// Neon Object Storage S3 client (reads AWS_* env vars injected automatically by Neon)
const VIDEOS_BUCKET = "videos";
const s3 = process.env.AWS_ENDPOINT_URL_S3
  ? new S3Client({ forcePathStyle: true })
  : null;

function getDbNameFromUrl(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl);
    return parsed.pathname.replace(/^\//, "") || "neondb";
  } catch {
    return "neondb";
  }
}

const dbName = getDbNameFromUrl(process.env.DATABASE_URL || "");
const realtimeSecret = (process.env.NEON_REALTIME_SECRET || process.env.REALTIME_SECRET || "")
  .trim()
  .replace(/^["']|["']$/g, "");
const realtimeUrl = (process.env.NEON_REALTIME_URL || process.env.REALTIME_URL || "")
  .trim()
  .replace(/^["']|["']$/g, "");
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

function verifyServerHmac(message: string, signatureHex: string | undefined): boolean {
  if (!realtimeSecret || !message || !signatureHex) return false;
  const expected = crypto.createHmac("sha256", realtimeSecret).update(message).digest("hex");
  const actualBuf = Buffer.from(signatureHex.trim(), "utf8");
  const expectedBuf = Buffer.from(expected, "utf8");
  if (actualBuf.length !== expectedBuf.length) return false;
  return crypto.timingSafeEqual(actualBuf, expectedBuf);
}

function verifyUploadToken(token: string | undefined): { user_id: string; object_key: string } | null {
  if (!token || !realtimeSecret || !token.includes(".")) return null;
  const [payloadB64, sigHex] = token.split(".", 2);
  if (!payloadB64 || !sigHex) return null;
  if (!verifyServerHmac(`upload:${payloadB64}`, sigHex)) return null;
  try {
    const decoded = JSON.parse(Buffer.from(payloadB64, "base64url").toString("utf-8")) as {
      user_id?: string;
      object_key?: string;
      exp?: number;
    };
    if (!decoded.user_id || !decoded.object_key) return null;
    if (decoded.exp && Date.now() / 1000 > decoded.exp) return null;
    return { user_id: decoded.user_id, object_key: decoded.object_key };
  } catch {
    return null;
  }
}

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Server-Signature, X-Upload-Token",
};

const app = new Hono();

app.use(
  "*",
  cors({
    origin: "*",
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Authorization", "Content-Type", "X-Server-Signature", "X-Upload-Token"],
  })
);

app.onError((err, c) => {
  const message = err instanceof Error ? err.message : String(err);
  return c.json({ detail: `Neon Function error: ${message}` }, 500, CORS_HEADERS);
});

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
        storage: Boolean(s3),
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

// Single-shot upload for smaller files (supports both raw binary PUT and multipart POST)
async function handleSingleUpload(c: any) {
  if (!s3) {
    return c.json({ detail: "Neon Object Storage is not configured on this branch." }, 503);
  }
  const grant = verifyUploadToken(c.req.header("x-upload-token"));
  if (!grant) {
    return c.json({ detail: "Invalid or expired upload token." }, 401);
  }

  let bytes: Uint8Array;
  let contentType = c.req.header("content-type") || "video/mp4";

  if (contentType.includes("multipart/form-data")) {
    const form = await c.req.formData();
    const file = form.get("file");
    if (!file || typeof file === "string") {
      return c.json({ detail: "Missing video file in multipart upload." }, 400);
    }
    contentType = file.type || "video/mp4";
    bytes = new Uint8Array(await file.arrayBuffer());
  } else {
    bytes = new Uint8Array(await c.req.arrayBuffer());
  }

  if (bytes.byteLength === 0) {
    return c.json({ detail: "Uploaded video file is empty." }, 400);
  }

  await s3.send(
    new PutObjectCommand({
      Bucket: VIDEOS_BUCKET,
      Key: grant.object_key,
      Body: bytes,
      ContentType: contentType,
    })
  );

  return c.json(
    {
      ok: true,
      object_key: grant.object_key,
      file_size_bytes: bytes.byteLength,
      content_type: contentType,
    },
    201
  );
}

app.post("/storage/upload", handleSingleUpload);
app.put("/storage/upload", handleSingleUpload);

// S3 Multipart Upload endpoints for large videos (6 MiB chunks — works up to 500 MB+ with low memory)
app.post("/storage/multipart/start", async (c) => {
  if (!s3) {
    return c.json({ detail: "Neon Object Storage is not configured on this branch." }, 503);
  }
  const grant = verifyUploadToken(c.req.header("x-upload-token"));
  if (!grant) {
    return c.json({ detail: "Invalid or expired upload token." }, 401);
  }
  let contentType = "video/mp4";
  try {
    const body = await c.req.json<{ content_type?: string }>();
    if (body?.content_type) contentType = body.content_type;
  } catch {
    // default video/mp4
  }

  const created = await s3.send(
    new CreateMultipartUploadCommand({
      Bucket: VIDEOS_BUCKET,
      Key: grant.object_key,
      ContentType: contentType,
    })
  );
  if (!created.UploadId) {
    return c.json({ detail: "Failed to initiate multipart upload in Neon Object Storage." }, 502);
  }
  return c.json({ upload_id: created.UploadId, object_key: grant.object_key }, 201);
});

app.put("/storage/multipart/part", async (c) => {
  if (!s3) {
    return c.json({ detail: "Neon Object Storage is not configured." }, 503);
  }
  const grant = verifyUploadToken(c.req.header("x-upload-token"));
  if (!grant) {
    return c.json({ detail: "Invalid or expired upload token." }, 401);
  }
  const uploadId = c.req.query("uploadId") || "";
  const partNumber = Number(c.req.query("partNumber") || "0");
  if (!uploadId || !Number.isInteger(partNumber) || partNumber < 1 || partNumber > 10000) {
    return c.json({ detail: "Invalid uploadId or partNumber." }, 400);
  }

  const chunk = new Uint8Array(await c.req.arrayBuffer());
  if (chunk.byteLength === 0) {
    return c.json({ detail: "Empty upload chunk." }, 400);
  }

  const res = await s3.send(
    new UploadPartCommand({
      Bucket: VIDEOS_BUCKET,
      Key: grant.object_key,
      UploadId: uploadId,
      PartNumber: partNumber,
      Body: chunk,
    })
  );
  return c.json({ part_number: partNumber, etag: res.ETag || "", bytes: chunk.byteLength });
});

app.post("/storage/multipart/complete", async (c) => {
  if (!s3) {
    return c.json({ detail: "Neon Object Storage is not configured." }, 503);
  }
  const grant = verifyUploadToken(c.req.header("x-upload-token"));
  if (!grant) {
    return c.json({ detail: "Invalid or expired upload token." }, 401);
  }
  const body = await c.req.json<{
    upload_id?: string;
    parts?: Array<{ part_number: number; etag: string }>;
    file_size_bytes?: number;
    content_type?: string;
  }>();
  if (!body.upload_id || !Array.isArray(body.parts) || body.parts.length === 0) {
    return c.json({ detail: "Missing upload_id or parts list." }, 400);
  }

  const sortedParts = [...body.parts]
    .sort((a, b) => a.part_number - b.part_number)
    .map((p) => ({ PartNumber: p.part_number, ETag: p.etag }));

  await s3.send(
    new CompleteMultipartUploadCommand({
      Bucket: VIDEOS_BUCKET,
      Key: grant.object_key,
      UploadId: body.upload_id,
      MultipartUpload: { Parts: sortedParts },
    })
  );

  return c.json(
    {
      ok: true,
      object_key: grant.object_key,
      file_size_bytes: body.file_size_bytes || 0,
      content_type: body.content_type || "video/mp4",
    },
    201
  );
});

app.post("/storage/multipart/abort", async (c) => {
  if (!s3) return c.json({ ok: true });
  const grant = verifyUploadToken(c.req.header("x-upload-token"));
  if (!grant) return c.json({ detail: "Invalid upload token." }, 401);
  try {
    const body = await c.req.json<{ upload_id?: string }>();
    if (body?.upload_id) {
      await s3.send(
        new AbortMultipartUploadCommand({
          Bucket: VIDEOS_BUCKET,
          Key: grant.object_key,
          UploadId: body.upload_id,
        })
      );
    }
  } catch {
    // Best-effort cleanup
  }
  return c.json({ ok: true });
});

app.get("/storage/download", async (c) => {
  if (!s3) {
    return c.json({ detail: "Neon Object Storage is not configured." }, 503);
  }
  const key = c.req.query("key") || "";
  if (!key || !verifyServerHmac(`download:${key}`, c.req.header("x-server-signature"))) {
    return c.json({ detail: "Unauthorized storage download request." }, 401);
  }

  try {
    const obj = await s3.send(new GetObjectCommand({ Bucket: VIDEOS_BUCKET, Key: key }));
    const body = obj.Body ? await obj.Body.transformToByteArray() : new Uint8Array();
    return new Response(body, {
      status: 200,
      headers: {
        "Content-Type": obj.ContentType || "application/octet-stream",
        "Content-Length": String(body.byteLength),
      },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return c.json({ detail: `Object not found: ${msg}` }, 404);
  }
});

app.delete("/storage/object", async (c) => {
  if (!s3) {
    return c.json({ ok: true });
  }
  const key = c.req.query("key") || "";
  if (!key || !verifyServerHmac(`delete:${key}`, c.req.header("x-server-signature"))) {
    return c.json({ detail: "Unauthorized storage delete request." }, 401);
  }
  try {
    await s3.send(new DeleteObjectCommand({ Bucket: VIDEOS_BUCKET, Key: key }));
  } catch {
    // Ignore missing object on cleanup
  }
  return c.json({ ok: true });
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
  } else if (body.user_id && verifyServerHmac(`seal:${body.user_id}`, c.req.header("x-server-signature"))) {
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
