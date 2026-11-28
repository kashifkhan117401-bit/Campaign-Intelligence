import React, { useCallback, useEffect, useState } from "react";
import { useLiveQuery } from "@neon/realtime-react";
import type { SealedLiveQuery } from "@neon/realtime/client";
import { Radio } from "lucide-react";
import { neonApi } from "../services/api";
import { neonRealtimeClient } from "../lib/neon";

export interface LiveCampaignActivityRow {
  id: string;
  user_id: string;
  name: string;
  record_type: string;
  status: string;
  summary: string;
  created_at: string;
}

function LiveActivityBadgeInner({
  sealedQuery,
  refreshQuery,
  onRowsUpdate,
}: {
  sealedQuery: SealedLiveQuery<LiveCampaignActivityRow>;
  refreshQuery: () => Promise<SealedLiveQuery<LiveCampaignActivityRow>>;
  onRowsUpdate?: (rows: readonly LiveCampaignActivityRow[]) => void;
}) {
  const { data, status, error } = useLiveQuery(sealedQuery, { refreshQuery });

  useEffect(() => {
    if (data && onRowsUpdate) {
      onRowsUpdate(data);
    }
  }, [data, onRowsUpdate]);

  if (status === "error") {
    return (
      <span
        title={error?.message || "Realtime disconnected"}
        className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-300"
      >
        <Radio className="h-3 w-3" />
        Live sync paused
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
      {data !== undefined ? `Neon Realtime Live (${data.length})` : "Connecting Neon Realtime..."}
    </span>
  );
}

export function NeonRealtimeActivityBadge({
  onRowsUpdate,
}: {
  onRowsUpdate?: (rows: readonly LiveCampaignActivityRow[]) => void;
}) {
  const [sealedQuery, setSealedQuery] = useState<SealedLiveQuery<LiveCampaignActivityRow> | null>(null);

  const fetchSealed = useCallback(async () => {
    const res = await neonApi.sealActivityQuery();
    return res.sealed_query as SealedLiveQuery<LiveCampaignActivityRow>;
  }, []);

  useEffect(() => {
    if (!neonRealtimeClient) return;
    let cancelled = false;
    fetchSealed()
      .then((sealed) => {
        if (!cancelled) setSealedQuery(sealed);
      })
      .catch(() => {
        // Non-fatal: dashboard still loads normally via REST API
      });
    return () => {
      cancelled = true;
    };
  }, [fetchSealed]);

  if (!neonRealtimeClient || !sealedQuery) return null;

  return (
    <LiveActivityBadgeInner
      sealedQuery={sealedQuery}
      refreshQuery={fetchSealed}
      onRowsUpdate={onRowsUpdate}
    />
  );
}
