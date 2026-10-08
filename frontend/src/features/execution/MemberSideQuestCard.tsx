import { useEffect, useState } from "react";
import {
  cityNexusApi,
  type MemberSideQuestProjection,
  type PlaceRecord,
} from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";

type Rendezvous = {
  title: string;
  place_name: string;
  scheduled_at?: string | null;
};

export function MemberSideQuestCard({
  journeyId,
  sideQuest,
  rendezvous,
  currentSplitActive = true,
  onUpdated,
}: {
  journeyId: string;
  sideQuest: MemberSideQuestProjection | null;
  rendezvous: Rendezvous | null;
  currentSplitActive?: boolean;
  onUpdated: () => Promise<void>;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [places, setPlaces] = useState<PlaceRecord[]>([]);
  const [placesReady, setPlacesReady] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedPlaceId, setSelectedPlaceId] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!currentSplitActive) {
      setPlacesReady(true);
      return;
    }
    let cancelled = false;
    void cityNexusApi.getJourney(journeyId)
      .then((journey) => cityNexusApi.listPlaces(journey.city_code))
      .then((rows) => {
        if (!cancelled) {
          setPlaces(rows);
          setPlacesReady(true);
        }
      })
      .catch(() => {
        if (!cancelled) setPlacesReady(true);
      });
    return () => { cancelled = true; };
  }, [currentSplitActive, journeyId]);

  const visiblePlaces = places
    .filter((place) => !query.trim() || place.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
    .slice(0, 100);
  const state = sideQuest?.state ?? null;
  const selectedPlace = places.find((place) => place.id === selectedPlaceId) ?? null;
  const displayedRendezvous = sideQuest?.rendezvous ?? rendezvous;
  const scheduledAt = sideQuest?.rendezvous.scheduled_at ?? rendezvous?.scheduled_at ?? null;
  const scheduledLabel = scheduledAt && Number.isFinite(Date.parse(scheduledAt))
    ? new Date(scheduledAt).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })
    : null;
  const canChooseDestination = currentSplitActive && (!sideQuest
    || state === "DESTINATION_UNRESOLVED"
    || ((state === "COMPLETED" || state === "CANCELLED" || state === "READY") && editing));

  if (!displayedRendezvous) return null;

  const saveDestination = async () => {
    if (busy || (!selectedPlaceId && !query.trim())) return;
    setBusy(true);
    setMessage(null);
    try {
      const updated = await cityNexusApi.createMemberSideQuest(
        journeyId,
        selectedPlaceId ? { placeId: selectedPlaceId } : { destinationText: query.trim() },
      );
      setEditing(false);
      setQuery("");
      setSelectedPlaceId("");
      setMessage(updated.member_side_quest?.state === "DESTINATION_UNRESOLVED"
        ? (zh
          ? "已私下保存这个地点描述；请选择一个精确的已知地点后才能开始导航。"
          : "That description is saved privately. Choose an exact known place before starting the stop.")
        : (zh ? "私人支线已准备好；共享行程没有改变。" : "Your private stop is ready. The shared Journey is unchanged."));
      await onUpdated();
    } catch {
      setMessage(zh
        ? "无法保存这条私人支线；请刷新后重试。共享行程没有改变。"
        : "The private stop could not be saved. Refresh and try again; the shared Journey is unchanged.");
    } finally {
      setBusy(false);
    }
  };

  const advance = async (action: "start" | "arrive" | "complete" | "cancel") => {
    if (!sideQuest || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      await cityNexusApi.advanceMemberSideQuest(journeyId, sideQuest.id, action);
      await onUpdated();
      setMessage(action === "complete" || action === "cancel"
        ? (zh ? "私人停留已结束；请返回共同会合点。共享行程没有改变。" : "The personal stop has ended. Return to the shared rendezvous; the shared Journey is unchanged.")
        : null);
    } catch {
      setMessage(zh
        ? "这项支线操作已失效或暂时无法保存；我刷新了当前状态。"
        : "That side-quest action is stale or could not be saved. Current state was refreshed.");
      await onUpdated();
    } finally {
      setBusy(false);
    }
  };

  const returnCopy = (returnState: string) => {
    if (returnState === "ON_TRACK") return zh ? "返程状态：当前路线可按时到达会合点。" : "Return status: the current route reaches the rendezvous in time.";
    if (returnState === "LOW_BUFFER") return zh ? "返程缓冲较少，建议尽快返回。" : "Return status: the safety buffer is low; head back soon.";
    if (returnState === "RETURN_RISK") return zh ? "可信实时路线显示共同会合可能受影响。" : "Trusted live route evidence shows the shared rendezvous may be at risk.";
    if (returnState.startsWith("ADVISORY")) return zh ? "返程判断仅供参考，不会据此修改共享行程。" : "The return estimate is advisory and cannot change the shared Journey.";
    return zh ? "返程状态未知：目前没有可靠的返程路线证据。" : "Return status unknown: no reliable route evidence is available yet.";
  };

  return (
    <div className="journey-side-quest" data-testid="member-side-quest-card" data-state={state ?? "NOT_CREATED"}>
      <span className="v8-kicker">{zh ? "你的私人支线" : "Your private side quest"}</span>
      <small data-testid="member-side-quest-rendezvous">
        {zh ? `共同会合点：${displayedRendezvous.place_name}${scheduledLabel ? ` · ${scheduledLabel}` : ""}` : `Shared rendezvous: ${displayedRendezvous.place_name}${scheduledLabel ? ` · ${scheduledLabel}` : ""}`}
      </small>
      <small>{zh ? "私人停留不会改变共享行程计划。" : "This private stop does not change the shared Journey."}</small>

      {sideQuest && (
        <div data-testid="member-side-quest-owner-state">
          <strong>{sideQuest.destination.title}</strong>
          <small>
            {zh ? `状态：${state}` : `State: ${state}`}
            {sideQuest.destination.authority === "DESCRIPTIVE_ONLY"
              ? (zh ? " · 地点尚未精确匹配" : " · destination is not an exact known Place yet")
              : ""}
          </small>
          {(state === "COMPLETED" || state === "CANCELLED") && (
            <small data-testid="member-side-quest-return-emphasis">
              {zh ? `私人停留已${state === "COMPLETED" ? "完成" : "取消"}；现在返回「${sideQuest.rendezvous.place_name}」。` : `Your personal stop is ${state.toLowerCase()}; return to ${sideQuest.rendezvous.place_name}.`}
            </small>
          )}
          {state === "ARRIVED" && (
            <small data-testid="member-side-quest-arrival-boundary">
              {zh ? "这是你本人报告已到达，不是设备定位证明。" : "This is your report of arrival, not device-verified physical presence."}
            </small>
          )}
          <small data-testid="member-side-quest-return-state">{returnCopy(sideQuest.return_state)}</small>
          {state === "INVALIDATED" && (
            <small>{zh ? "共同会合安排已变化；这条支线保留为历史，不能继续执行。" : "The shared rendezvous changed. This side quest remains as history and can no longer be executed."}</small>
          )}
        </div>
      )}

      {canChooseDestination && (
        <div className="journey-side-quest-form">
          <label htmlFor="member-side-quest-search">
            {state === "READY"
              ? (zh ? "更换尚未开始的私人地点" : "Change the private stop before starting")
              : (zh ? "选择私人停留地点" : "Choose a private stop")}
          </label>
          {selectedPlace && (
            <small data-testid="member-side-quest-confirmation">
              {zh
                ? `确认：先去「${selectedPlace.name}」，再于「${displayedRendezvous.place_name}」和大家会合。`
                : `Go to ${selectedPlace.name} before rejoining everyone at ${displayedRendezvous.place_name}.`}
            </small>
          )}
          {!selectedPlaceId && query.trim() && (
            <small data-testid="member-side-quest-descriptive-boundary">
              {zh ? "这是地点描述，尚未匹配到精确地点；保存后仍需选中已知地点才能开始。" : "This is only a place description; select an exact known Place before the stop can start."}
            </small>
          )}
          <input
            id="member-side-quest-search"
            data-testid="member-side-quest-search"
            type="search"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setSelectedPlaceId(""); }}
            placeholder={zh ? "搜索地点名称" : "Search place names"}
          />
          <select
            aria-label={zh ? "已知地点" : "Known place"}
            data-testid="member-side-quest-place"
            value={selectedPlaceId}
            onChange={(event) => setSelectedPlaceId(event.target.value)}
          >
            <option value="">{placesReady ? (zh ? "选择一个已知地点，或仅保存描述" : "Choose a known place, or save a description") : (zh ? "正在加载地点…" : "Loading places…")}</option>
            {visiblePlaces.map((place) => <option key={place.id} value={place.id}>{place.name}</option>)}
          </select>
          <button
            type="button"
            data-testid="member-side-quest-save"
            disabled={busy || (!selectedPlaceId && !query.trim())}
            onClick={() => void saveDestination()}
          >
            {busy
              ? (zh ? "正在保存…" : "Saving…")
              : selectedPlaceId
                ? (zh ? "确认私人支线" : "Confirm private stop")
                : sideQuest
                  ? (zh ? "保存地点描述" : "Save place description")
                  : (zh ? "保存地点描述" : "Save place description")}
          </button>
          {state === "READY" && (
            <button type="button" disabled={busy} onClick={() => setEditing(false)}>
              {zh ? "返回支线" : "Back to side quest"}
            </button>
          )}
        </div>
      )}

      {currentSplitActive && state === "READY" && !editing && (
        <div className="journey-side-quest-actions">
          <button type="button" data-testid="member-side-quest-start" disabled={busy} onClick={() => void advance("start")}>
            {zh ? "开始前往" : "Start stop"}
          </button>
          <button type="button" disabled={busy} onClick={() => setEditing(true)}>
            {zh ? "更换地点" : "Change destination"}
          </button>
          <button type="button" data-testid="member-side-quest-cancel" disabled={busy} onClick={() => void advance("cancel")}>
            {zh ? "取消支线" : "Cancel stop"}
          </button>
        </div>
      )}
      {currentSplitActive && state === "EN_ROUTE" && (
        <div className="journey-side-quest-actions">
          <button type="button" data-testid="member-side-quest-arrive" disabled={busy} onClick={() => void advance("arrive")}>
            {zh ? "我已到达" : "I arrived"}
          </button>
          <button type="button" data-testid="member-side-quest-cancel" disabled={busy} onClick={() => void advance("cancel")}>
            {zh ? "取消支线" : "Cancel stop"}
          </button>
        </div>
      )}
      {currentSplitActive && state === "ARRIVED" && (
        <div className="journey-side-quest-actions">
          <button type="button" data-testid="member-side-quest-complete" disabled={busy} onClick={() => void advance("complete")}>
            {zh ? "完成私人停留" : "Done with stop"}
          </button>
          <button type="button" data-testid="member-side-quest-cancel" disabled={busy} onClick={() => void advance("cancel")}>
            {zh ? "取消支线" : "Cancel stop"}
          </button>
        </div>
      )}
      {currentSplitActive && (state === "COMPLETED" || state === "CANCELLED") && !editing && (
        <button type="button" data-testid="member-side-quest-another" disabled={busy} onClick={() => setEditing(true)}>
          {zh ? "再安排一个私人停留" : "Plan another private stop"}
        </button>
      )}
      {message && <small data-testid="member-side-quest-message">{message}</small>}
    </div>
  );
}
