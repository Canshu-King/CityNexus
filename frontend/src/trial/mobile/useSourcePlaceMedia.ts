import { useEffect, useRef, useState } from "react";
import { cityNexusApi, type GoalPlaceMediaResult } from "../../api/citynexus";
import { readTravelerBearer, readTravelerIdentity, subscribeTravelerBearer } from "../../lib/travelerSession";
import type { WorkspaceMapPoint } from "./WorkspaceMap";

/** Three automatic photo lookups, then only the explicitly selected extra place. */
export function useSourcePlaceMedia(journeyId: string | undefined, taskId: string | undefined,
  enabled: boolean, places: WorkspaceMapPoint[], sourceIds: ReadonlySet<string>,
  scheduledIds?: ReadonlySet<string>, selectedId?: string | null) {
  const [identityVersion, setIdentityVersion] = useState(0);
  const [results, setResults] = useState<Record<string, GoalPlaceMediaResult>>({});
  const completed = useRef(new Map<string, GoalPlaceMediaResult>());
  const context = useRef("");
  useEffect(() => subscribeTravelerBearer(() => {
    completed.current.clear(); setResults({}); setIdentityVersion(value => value + 1);
  }), []);
  const owner = readTravelerIdentity()?.travelerId;
  const bearer = readTravelerBearer();
  const scope = JSON.stringify([journeyId, taskId, owner, bearer, identityVersion]);
  const eligible = places.filter(point => sourceIds.has(point.candidate_id)
    && point.provider_provenance === "LIVE_PROVIDER" && point.region_status !== "CONFLICT"
    && point.selection_state !== "REGION_CONFLICT")
    .sort((a, b) => Number(scheduledIds?.has(b.candidate_id)) - Number(scheduledIds?.has(a.candidate_id)));
  const targets = [...new Set([...eligible.slice(0, 3).map(point => point.candidate_id),
    ...eligible.filter(point => point.candidate_id === selectedId).map(point => point.candidate_id)])];
  const signature = JSON.stringify(targets.map(id => {
    const point = eligible.find(item => item.candidate_id === id)!;
    return [id, point.name, point.latitude, point.longitude];
  }));
  useEffect(() => {
    if (context.current !== scope) {
      context.current = scope; completed.current.clear(); setResults({});
    }
    if (!enabled || !journeyId || !taskId || !owner || !bearer) { setResults({}); return; }
    const controller = new AbortController();
    const sameOwner = () => !controller.signal.aborted && context.current === scope
      && readTravelerBearer() === bearer && readTravelerIdentity()?.travelerId === owner;
    void (async () => {
      for (const [id, name, latitude, longitude] of JSON.parse(signature) as [string, string, number, number][]) {
        if (!sameOwner()) return;
        const key = JSON.stringify([id, name, latitude, longitude]);
        let result = completed.current.get(key);
        if (!result) {
          try {
            result = await cityNexusApi.getGoalPlaceMedia(journeyId, taskId, id, controller.signal);
            if (!sameOwner()) return;
            if (result.candidate_id !== id || result.journey_id !== journeyId || result.task_id !== taskId
                || (result.media && result.media.place_id !== id)) continue;
            completed.current.set(key, result);
          } catch {
            if (!sameOwner()) return;
            // This lookup has finished. Re-renders do not retry a failed source.
            result = { candidate_id: id, place_id: id, journey_id: journeyId, task_id: taskId,
              status: "UNAVAILABLE", media: null };
            completed.current.set(key, result);
          }
        }
        if (sameOwner()) setResults(previous => ({ ...previous, [id]: result! }));
      }
    })();
    return () => controller.abort();
  }, [scope, enabled, signature, journeyId, taskId, owner, bearer]);
  return context.current === scope && enabled ? results : {};
}
