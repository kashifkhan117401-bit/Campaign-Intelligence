import { createAuthClient } from "@neon/auth";
import { BetterAuthReactAdapter } from "@neon/auth/react/adapters";
import { createRealtimeClient, type RealtimeClient } from "@neon/realtime/client";

export const NEON_AUTH_URL = (import.meta.env.VITE_NEON_AUTH_URL || "").trim();
export const NEON_REALTIME_URL = (import.meta.env.VITE_NEON_REALTIME_URL || "").trim();

export const neonAuthClient = NEON_AUTH_URL
  ? createAuthClient(NEON_AUTH_URL, {
      adapter: BetterAuthReactAdapter(),
    })
  : null;

// Single app-wide RealtimeClient so all live queries share one WebSocket connection
export const neonRealtimeClient: RealtimeClient | null = NEON_REALTIME_URL
  ? createRealtimeClient({ url: NEON_REALTIME_URL })
  : null;
