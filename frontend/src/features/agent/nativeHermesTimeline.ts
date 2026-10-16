import { useEffect, useState } from "react";
import { CityNexusApiError, cityNexusApi, type CopilotResponse, type NativeRuntimeEvent } from "../../api/citynexus";
import { readTravelerBearer, subscribeTravelerBearer, travelerAuthHeaders } from "../../lib/travelerSession";

export type NativeHermesRun = NonNullable<CopilotResponse["agent_run"]>;
export type NativeTimelineAuth = "checking" | "authorized" | "unauthorized";
export type NativeTimelineConnection = "idle" | "connecting" | "connected" | "retrying" | "unavailable" | "complete";

const NATIVE_EVENT_TYPES = new Set([
  "semantic.interpreted",
  "mission.planned",
  "run.started",
  "tool.started",
  "tool.completed",
  "tool.failed",
  "gateway.checked",
  "guardian.checked",
  "proposal.created",
  "approval.required",
  "run.completed",
  "run.failed",
  "run.stopped",
]);

export function nativeEventKey(event: NativeRuntimeEvent) {
  return [
    event.event_type,
    event.event_id ?? "",
    event.sequence ?? "",
    event.tool_name ?? "",
    event.timestamp ?? "",
    event.duration_ms ?? "",
    event.approval_id ?? "",
    event.proposal_id ?? "",
  ].join("|");
}

export function mergeNativeEvents(...groups: Array<NativeRuntimeEvent[] | undefined>) {
  const result: NativeRuntimeEvent[] = [];
  const seen = new Set<string>();
  for (const group of groups) {
    for (const item of group ?? []) {
      if (!item || typeof item !== "object") continue;
      const key = nativeEventKey(item);
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(item);
    }
  }
  return result
    .map((event, index) => ({ event, index }))
    .sort((left, right) => {
      const leftSequence = Number.isFinite(left.event.sequence) ? Number(left.event.sequence) : null;
      const rightSequence = Number.isFinite(right.event.sequence) ? Number(right.event.sequence) : null;
      if (leftSequence != null && rightSequence != null && leftSequence !== rightSequence) {
        return leftSequence - rightSequence;
      }
      const leftTime = left.event.timestamp ? Date.parse(String(left.event.timestamp)) : Number.NaN;
      const rightTime = right.event.timestamp ? Date.parse(String(right.event.timestamp)) : Number.NaN;
      if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
        return leftTime - rightTime;
      }
      return left.index - right.index;
    })
    .map(({ event }) => event)
    .slice(-250);
}

export function statusForNativeEvent(event: NativeRuntimeEvent): "active" | "done" | "approval" | "failed" {
  if (event.event_type === "approval.required" || event.status === "approval_required") return "approval";
  if (event.event_type.endsWith(".failed") || event.status === "failed") return "failed";
  if (event.event_type.endsWith(".completed") || event.status === "completed") return "done";
  if (event.event_type === "run.stopped" || event.status === "stopped") return "failed";
  return "active";
}

function isTerminal(status: string) {
  return /^(completed|succeeded|failed|cancelled|canceled|stopped|error)$/i.test(status);
}

function readStatus(error: unknown) {
  return error instanceof CityNexusApiError ? error.status : null;
}

function eventFromFrame(frame: string): NativeRuntimeEvent | null {
  let eventName = "message";
  const data: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (data.length === 0) return null;
  try {
    const parsed = JSON.parse(data.join("\n")) as NativeRuntimeEvent;
    if (!parsed || typeof parsed !== "object" || typeof parsed.event_type !== "string") return null;
    if (!NATIVE_EVENT_TYPES.has(parsed.event_type)) return null;
    if (eventName !== "message" && eventName !== parsed.event_type) return null;
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Read one server-bound Hermes run. Events are never cached in browser storage;
 * a signed bearer change clears the private trace and aborts the stream.
 */
export function useNativeHermesTimeline({
  journeyId,
  run,
  enabled = true,
}: {
  journeyId: string;
  run: NativeHermesRun | null;
  enabled?: boolean;
}) {
  const [events, setEvents] = useState<NativeRuntimeEvent[]>([]);
  const [runState, setRunState] = useState("unknown");
  const [authState, setAuthState] = useState<NativeTimelineAuth>("checking");
  const [connection, setConnection] = useState<NativeTimelineConnection>("idle");
  const [bearerEpoch, setBearerEpoch] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let ended = false;
    let denied = false;
    let attempts = 0;
    let controller: AbortController | null = null;
    let retryTimer: number | undefined;
    let pollTimer: number | undefined;
    const startingBearer = readTravelerBearer();

    setEvents([]);
    setRunState(run?.status ?? "unknown");
    setConnection(run ? "connecting" : "idle");
    setAuthState(startingBearer ? "authorized" : "unauthorized");

    const current = () => !cancelled && !denied && Boolean(startingBearer) && readTravelerBearer() === startingBearer;
    const clearPrivateState = () => {
      denied = true;
      ended = true;
      controller?.abort();
      if (retryTimer != null) window.clearTimeout(retryTimer);
      if (pollTimer != null) window.clearInterval(pollTimer);
      setEvents([]);
      setRunState("unknown");
      setAuthState("unauthorized");
      setConnection("idle");
    };
    const unsubscribe = subscribeTravelerBearer((bearer) => {
      if (bearer !== startingBearer) {
        clearPrivateState();
        setBearerEpoch((epoch) => epoch + 1);
      }
    });

    if (!run || run.runtime_identity !== "HERMES_NATIVE_MCP" || !enabled || !startingBearer) {
      if (!startingBearer && run) setAuthState("unauthorized");
      return () => {
        cancelled = true;
        unsubscribe();
      };
    }

    const append = (incoming: NativeRuntimeEvent[]) => {
      if (!current()) return;
      const matching = incoming.filter((event) =>
        event.run_id === run.run_id && NATIVE_EVENT_TYPES.has(event.event_type),
      );
      if (matching.length === 0) return;
      setEvents((currentEvents) => mergeNativeEvents(currentEvents, matching));
      const terminal = [...matching].reverse().find((event) =>
        ["run.completed", "run.failed", "run.stopped"].includes(event.event_type),
      );
      if (terminal?.status) setRunState(String(terminal.status));
      else if (matching.some((event) => event.event_type === "run.started")) setRunState("running");
      if (terminal) {
        ended = true;
        setConnection("complete");
        controller?.abort();
        if (pollTimer != null) window.clearInterval(pollTimer);
      }
    };

    const refreshTimeline = async () => {
      if (!current() || ended || document.visibilityState === "hidden") return;
      try {
        const payload = await cityNexusApi.getNativeHermesTimeline(journeyId, run.run_id);
        if (!current()) return;
        if (payload.run_id !== run.run_id || payload.journey_id !== journeyId || payload.runtime_identity !== "HERMES_NATIVE_MCP") {
          clearPrivateState();
          return;
        }
        append(payload.events ?? []);
        if (payload.observability?.completion_status) {
          setRunState(payload.observability.completion_status);
          if (isTerminal(payload.observability.completion_status)) {
            ended = true;
            setConnection("complete");
            controller?.abort();
            if (pollTimer != null) window.clearInterval(pollTimer);
          }
        }
      } catch (error) {
        if (!current()) return;
        if ([401, 403, 404].includes(readStatus(error) ?? 0)) {
          clearPrivateState();
          return;
        }
        // A failed history refresh does not erase already verified in-memory events.
      }
    };

    const stream = async () => {
      if (typeof window === "undefined") {
        setConnection("unavailable");
        return;
      }
      const url = "/api/v1/journeys/" + encodeURIComponent(journeyId)
        + "/agent/hermes/runs/" + encodeURIComponent(run.run_id) + "/events";
      while (current() && !ended && attempts < 4) {
        controller = new AbortController();
        try {
          setConnection(attempts === 0 ? "connecting" : "retrying");
          const response = await fetch(url, {
            headers: { Accept: "text/event-stream", ...travelerAuthHeaders() },
            cache: "no-store",
            signal: controller.signal,
          });
          if (response.status === 401 || response.status === 403 || response.status === 404) {
            clearPrivateState();
            return;
          }
          if (!response.ok || !response.body) throw new Error("event_stream_unavailable");
          attempts = 0;
          setConnection("connected");
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (current() && !ended) {
            const next = await reader.read();
            if (next.done) break;
            buffer += decoder.decode(next.value, { stream: true });
            let boundary = buffer.indexOf("\n\n");
            while (boundary >= 0) {
              const frame = buffer.slice(0, boundary);
              buffer = buffer.slice(boundary + 2);
              const event = eventFromFrame(frame);
              if (event?.run_id === run.run_id && event.source === "HERMES_NATIVE") append([event]);
              boundary = buffer.indexOf("\n\n");
            }
          }
          if (!ended && current()) throw new Error("event_stream_closed");
        } catch (error) {
          if (!current() || ended || (error instanceof DOMException && error.name === "AbortError")) return;
          attempts += 1;
          if (attempts >= 4) {
            setConnection("unavailable");
            return;
          }
          setConnection("retrying");
          await new Promise<void>((resolve) => {
            retryTimer = window.setTimeout(resolve, Math.min(5000, 500 * 2 ** (attempts - 1)));
          });
        }
      }
    };

    void refreshTimeline();
    pollTimer = window.setInterval(() => { void refreshTimeline(); }, 8000);
    void stream();
    return () => {
      cancelled = true;
      ended = true;
      controller?.abort();
      if (retryTimer != null) window.clearTimeout(retryTimer);
      if (pollTimer != null) window.clearInterval(pollTimer);
      unsubscribe();
    };
  }, [bearerEpoch, enabled, journeyId, run?.run_id, run?.runtime_identity, run?.status]);

  return { events, runState, setRunState, authState, connection };
}
