import { useEffect, useState } from "react";
import {
  CityNexusApiError,
  cityNexusApi,
  type MomentScoutInterest,
  type MomentScoutResult,
} from "../../api/citynexus";
import { useLocale } from "../../i18n/LocaleContext";

export function MomentScoutCard({
  journeyId,
  onRefreshLocation,
  onUpdated,
}: {
  journeyId: string;
  onRefreshLocation?: () => Promise<string | null>;
  onUpdated: () => Promise<void>;
}) {
  const { locale } = useLocale();
  const zh = locale.startsWith("zh");
  const [budgetMinutes, setBudgetMinutes] = useState<15 | 30 | 45>(30);
  const [interest, setInterest] = useState<MomentScoutInterest>("ANYTHING");
  const [receipt, setReceipt] = useState<{
    value: MomentScoutResult;
    locationObservationId: string;
  } | null>(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!receipt) return;
    const timeout = window.setTimeout(() => {
      setReceipt(null);
      setSelectedPlaceId("");
    }, 60_000);
    return () => window.clearTimeout(timeout);
  }, [receipt]);

  const scout = async () => {
    if (busy || !onRefreshLocation) return;
    setBusy(true);
    setMessage(null);
    setReceipt(null);
    setSelectedPlaceId("");
    try {
      const locationObservationId = await onRefreshLocation();
      if (!locationObservationId) {
        setMessage(zh
          ? "没有取得这一次的位置；没有生成附近推荐。你可以继续共同计划。"
          : "No one-time location was available, so no nearby options were generated. You can continue the shared plan.");
        return;
      }
      const value = await cityNexusApi.scoutMemberMoment(
        journeyId,
        locationObservationId,
        budgetMinutes,
        interest,
      );
      setReceipt({ value, locationObservationId });
      if (value.scout_state === "NO_GROUNDED_OPTIONS") {
        setMessage(zh
          ? "附近没有可核实的已知地点；当前共同计划保持不变。"
          : "There are no grounded known places nearby. Your shared Journey stays unchanged.");
      }
    } catch {
      setMessage(zh
        ? "暂时无法查找附近体验；共享行程没有改变。请刷新位置后重试。"
        : "Nearby discovery is unavailable right now. The shared Journey is unchanged; refresh your location and try again.");
    } finally {
      setBusy(false);
    }
  };

  const confirmSelection = async () => {
    const candidate = receipt?.value.candidates.find((item) => item.place_id === selectedPlaceId);
    if (!candidate || !receipt || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      await cityNexusApi.selectMomentScoutCandidate(
        journeyId,
        receipt.locationObservationId,
        receipt.value.budget_minutes,
        receipt.value.interest,
        receipt.value.scout_context,
        candidate.place_id,
      );
      setReceipt(null);
      setSelectedPlaceId("");
      setMessage(zh
        ? "私人停留已准备好；路线时间仍未核实。共同会合点和共享计划未改变。"
        : "Your private stop is ready. Route time remains unverified; the rendezvous and shared plan are unchanged.");
      try {
        await onUpdated();
      } catch {
        setMessage(zh
          ? "私人停留已保存；页面刷新失败，请手动刷新查看当前状态。"
          : "Your private stop is saved, but the screen did not refresh. Reload to see its current state.");
      }
    } catch (error) {
      setReceipt(null);
      setSelectedPlaceId("");
      const detail = error instanceof CityNexusApiError
        && error.body && typeof error.body === "object" && "detail" in error.body
        ? String(error.body.detail ?? "")
        : "";
      if (detail.includes("Start the Journey Operator before planning a side trip")) {
        setMessage(zh
          ? "请先在本页点击「照看这趟行程」开启 Journey Operator，再重新查找并确认私人停留。尚未创建私人支线。"
          : "First tap 'Take care of this trip' to start Journey Operator on this page, then scout and confirm again. No private stop was created.");
      } else if (error instanceof CityNexusApiError && [401, 403].includes(error.status)) {
        setMessage(zh
          ? "你的行程成员身份无效或已失效，请重新登录自己的账号。没有替其他成员创建私人支线。"
          : "Your Journey membership or sign-in is no longer valid. Sign in as yourself; no stop was created for another member.");
      } else if (error instanceof CityNexusApiError && error.status === 409) {
        setMessage(zh
          ? "推荐、共同会合安排或当前私人支线状态已经变化。请刷新再查找；如果分离意图已生效，可以继续完成私人地点选择。"
          : "The suggestion, rendezvous or private-stop state changed. Refresh and scout again; if a split was created, continue choosing your stop.");
      } else {
        setMessage(zh
          ? "暂时无法完成地点选择，请刷新确认当前状态后再试。"
          : "The destination could not be selected. Refresh to check the current state before trying again.");
      }
      try {
        await onUpdated();
      } catch {
        // Keep the recoverable selection message visible if the projection reload also fails.
      }
    } finally {
      setBusy(false);
    }
  };

  const rendezvous = receipt?.value.rendezvous;
  const rendezvousIsPast = rendezvous?.time_state === "PAST";
  const shortWindow = rendezvous?.time_state === "AVAILABLE"
    && rendezvous.minutes_until !== null
    && rendezvous.minutes_until < (receipt?.value.budget_minutes ?? 0);
  const rendezvousTime = rendezvous?.scheduled_at
    ? new Date(rendezvous.scheduled_at).toLocaleString(locale, { dateStyle: "short", timeStyle: "short" })
    : null;

  return (
    <section className="journey-moment-scout" data-testid="moment-scout" aria-live="polite">
      <strong>{zh ? "附近有什么可以顺路玩？" : "Find a quick adventure nearby"}</strong>
      <small>
        {zh
          ? "仅在你点击后读取一次当前位置；距离是直线距离，不是步行时间。推荐仅本人可见。"
          : "A single foreground location sample is requested only after you tap. Distance is straight-line, not walking time; suggestions are visible only to you."}
      </small>
      <label>
        {zh ? "个人时间偏好" : "Personal time budget"}
        <select
          data-testid="moment-scout-budget"
          value={budgetMinutes}
          disabled={busy}
          onChange={(event) => {
            setBudgetMinutes(Number(event.target.value) as 15 | 30 | 45);
            setReceipt(null);
            setSelectedPlaceId("");
          }}
        >
          <option value={15}>{zh ? "15 分钟" : "15 minutes"}</option>
          <option value={30}>{zh ? "30 分钟" : "30 minutes"}</option>
          <option value={45}>{zh ? "45 分钟" : "45 minutes"}</option>
        </select>
      </label>
      <label>
        {zh ? "兴趣（可选）" : "Interest (optional)"}
        <select
          data-testid="moment-scout-interest"
          value={interest}
          disabled={busy}
          onChange={(event) => {
            setInterest(event.target.value as MomentScoutInterest);
            setReceipt(null);
            setSelectedPlaceId("");
          }}
        >
          <option value="ANYTHING">{zh ? "随便看看" : "Anything"}</option>
          <option value="COFFEE_FOOD">{zh ? "咖啡 / 美食" : "Coffee / food"}</option>
          <option value="CULTURE">{zh ? "文化" : "Culture"}</option>
          <option value="NATURE">{zh ? "自然" : "Nature"}</option>
        </select>
      </label>
      <button
        type="button"
        data-testid="moment-scout-submit"
        disabled={busy || !onRefreshLocation}
        onClick={() => void scout()}
      >
        {busy ? (zh ? "正在查找…" : "Looking nearby…") : (zh ? "查找附近体验" : "Scout nearby")}
      </button>
      {receipt?.value.scout_state === "OPTIONS_AVAILABLE" && (
        <div data-testid="moment-scout-results" data-state={receipt.value.scout_state}>
          <small>
            {zh
              ? `共同会合点：${receipt.value.rendezvous.place_name}${rendezvousTime ? ` · ${rendezvousTime}` : ""} · ${receipt.value.budget_minutes} 分钟仅作个人偏好。`
              : `Rejoin at ${receipt.value.rendezvous.place_name}${rendezvousTime ? ` · ${rendezvousTime}` : ""} · ${receipt.value.budget_minutes} min is a personal preference.`}
          </small>
          {rendezvous?.time_state === "UNKNOWN" && (
            <small role="status" data-testid="moment-scout-rendezvous-time-warning">
              {zh
                ? "共同会合时间未知；离开前请核对共享计划。路线时间也未核实。"
                : "The shared rendezvous time is unknown. Check the shared plan before leaving; route time is also unverified."}
            </small>
          )}
          {rendezvous?.time_state === "PAST" && (
            <small role="alert" data-testid="moment-scout-rendezvous-time-warning">
              {zh
                ? "下一共同会合时间已过，不能创建私人停留；请继续共同计划。"
                : "The next shared rendezvous time has passed, so a private stop cannot be started. Continue the shared plan."}
            </small>
          )}
          {rendezvous?.time_state === "AVAILABLE" && shortWindow && (
            <small role="status" data-testid="moment-scout-rendezvous-time-warning">
              {zh
                ? `距离会合约 ${rendezvous.minutes_until} 分钟，少于你选的 ${receipt.value.budget_minutes} 分钟偏好；路线时间未核实。`
                : `About ${rendezvous.minutes_until} minutes remain before the rendezvous, less than your ${receipt.value.budget_minutes}-minute preference. Route time is unverified.`}
            </small>
          )}
          {receipt.value.candidates.map((candidate) => (
            <article key={candidate.place_id} data-testid="moment-scout-candidate" data-place-id={candidate.place_id}>
              <strong>{candidate.name}</strong>
              <small>
                {candidate.category} · {zh ? `直线 ${candidate.straight_line_distance_m} 米` : `${candidate.straight_line_distance_m} m straight line, not a route ETA`}
              </small>
              <small>
                {candidate.place_provenance === "DEMO_FIXTURE"
                  ? (zh ? "来源：演示 / 夹具地点" : "Source: demo / fixture place")
                  : `Source: ${candidate.place_provenance.replace("CITY_PLACE_CATALOG:", "")}`}
                {zh ? " · 营业状态未知 · 会合适配未核实" : " · opening status unknown · return fit unverified"}
              </small>
              <button
                type="button"
                data-testid="moment-scout-choose"
                disabled={busy || rendezvousIsPast}
                aria-pressed={selectedPlaceId === candidate.place_id}
                onClick={() => setSelectedPlaceId(candidate.place_id)}
              >
                {selectedPlaceId === candidate.place_id
                  ? (zh ? "已选择" : "Selected")
                  : (zh ? "选择这个地点" : "Choose this place")}
              </button>
            </article>
          ))}
          {selectedPlaceId && (
            <div data-testid="moment-scout-confirmation">
              <small>
                {zh
                  ? `确认先去「${receipt.value.candidates.find((item) => item.place_id === selectedPlaceId)?.name}」，再回到「${receipt.value.rendezvous.place_name}」${rendezvousTime ? `（${rendezvousTime}）` : ""}会合。${rendezvous?.time_state === "UNKNOWN" ? "会合时间未知，请核对共享计划。" : shortWindow ? `剩余时间少于 ${receipt.value.budget_minutes} 分钟偏好。` : ""}路线时间尚未核实。`
                  : `Go to ${receipt.value.candidates.find((item) => item.place_id === selectedPlaceId)?.name}, then rejoin at ${receipt.value.rendezvous.place_name}${rendezvousTime ? ` (${rendezvousTime})` : ""}.${rendezvous?.time_state === "UNKNOWN" ? " Rendezvous time is unknown; check the shared plan." : shortWindow ? ` Less than your ${receipt.value.budget_minutes}-minute preference remains.` : ""} Route time is unverified.`}
              </small>
              <button
                type="button"
                data-testid="moment-scout-confirm"
                disabled={busy || rendezvousIsPast}
                onClick={() => void confirmSelection()}
              >
                {busy
                  ? (zh ? "正在准备私人停留…" : "Preparing private stop…")
                  : shortWindow
                    ? (zh ? "仍要继续并确认" : "Continue despite short time")
                    : (zh ? "确认私人停留" : "Confirm private stop")}
              </button>
            </div>
          )}
          <small>{zh ? "选项是附近地点线索，不代表营业、可达或能按时返回。" : "These are nearby place leads, not proof of opening, route access, or an on-time return."}</small>
        </div>
      )}
      {message && <small data-testid="moment-scout-message">{message}</small>}
    </section>
  );
}
