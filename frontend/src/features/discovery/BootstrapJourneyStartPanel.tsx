import { useState } from "react";
import { CityNexusApiError, cityNexusApi } from "../../api/citynexus";

function planStartFailureMessage(error: unknown): string {
  if (error instanceof CityNexusApiError && error.body && typeof error.body === "object") {
    const body = error.body as Record<string, unknown>;
    const nestedError = body.error && typeof body.error === "object"
      ? body.error as Record<string, unknown>
      : undefined;
    const detail = body.detail && typeof body.detail === "object"
      ? body.detail as Record<string, unknown>
      : undefined;
    const reasonCode = [body.reason_code, nestedError?.reason_code, detail?.reason_code]
      .find((value): value is string => typeof value === "string");
    if (reasonCode === "UNRESOLVED_ACTIVITY_FACTS") {
      return "营业时间没有可靠来源，暂时无法生成行程。查看地点信息或更换地点后再试。";
    }
    if (reasonCode === "PLACE_COST_UNVERIFIED") {
      return "费用信息还没核实，暂时不能生成正式行程。查看来源或更换地点后再试。";
    }
    if (reasonCode === "PLACES_NOT_IN_CATALOG") {
      return "这个地点已不在当前列表里。回到探索重新选择。";
    }
    if (error.status === 409) {
      return "行程信息刚有变化，刷新后再试。";
    }
    if (error.status === 401 || error.status === 403) {
      return "当前行程已无法访问。重新开始探索。";
    }
  }
  if (error instanceof Error && error.message === "没有生成可启动的行程方案。") {
    return "还没有生成行程方案。请补齐地点信息或更换地点。";
  }
  if (error instanceof Error && error.message === "行程还没有启动。") {
    return "行程还没启动成功。请稍后再试。";
  }
  return "没有启动成功。行程草稿还在，可以返回探索更换地点或重试。";
}

/**
 * The first native journey action after zero-catalogue discovery.
 *
 * This deliberately does not go through the Agent command surface: choosing
 * one provider Place is already the traveller's explicit scope, and planning
 * must be a visible generate -> select -> start chain with no AgentRun or
 * booking side effect.  Unknown admission price is a separate acknowledgement
 * and never a free-price claim.
 */
export function BootstrapJourneyStartPanel({
  journeyId,
  placeId,
  onStarted,
  onCancel,
}: {
  journeyId: string;
  placeId: string;
  onStarted: () => Promise<void>;
  onCancel: () => void;
}) {
  const [acceptUnknownCost, setAcceptUnknownCost] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const start = async () => {
    if (!acceptUnknownCost) {
      setMessage("先确认费用信息再启动行程。");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const generated = await cityNexusApi.generatePlans(journeyId, 1, {
        placeIds: [placeId],
        allowSinglePlace: true,
        allowUnknownCost: true,
        idempotencyKey: crypto.randomUUID(),
      });
      const plan = generated[0];
      if (!plan?.id) {
        throw new Error("没有生成可启动的行程方案。");
      }
      await cityNexusApi.selectPlan(journeyId, plan.id);
      const startedJourney = await cityNexusApi.startJourney(journeyId);
      if (startedJourney?.context?.journey_status !== "ACTIVE") {
        throw new Error("行程还没有启动。");
      }
      await onStarted();
    } catch (error) {
      setMessage(planStartFailureMessage(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="v8-join-entry" data-testid="bootstrap-native-start">
      <section className="v8-loading" aria-labelledby="bootstrap-native-start-title">
        <div className="v8-brand-mark">CN</div>
        <h1 id="bootstrap-native-start-title">启动正式行程</h1>
        <p>已选择 1 个地点。</p>
        <p>
          门票价格未知，未计入金额；预订或付款需另行确认。
        </p>
        <label>
          <input
            type="checkbox"
            data-testid="bootstrap-unknown-cost-ack"
            checked={acceptUnknownCost}
            onChange={(event) => setAcceptUnknownCost(event.target.checked)}
          />
          确认以上费用信息。
        </label>
        {message ? <p role="status" data-testid="bootstrap-native-start-message">{message}</p> : null}
        <div className="v8-actions">
          <button
            type="button"
            className="v8-primary-button"
            data-testid="bootstrap-native-start-submit"
            disabled={busy}
            onClick={() => void start()}
          >
            {busy ? "正在启动…" : "生成并启动行程"}
          </button>
          <button
            type="button"
            className="v8-outline-button"
            data-testid="bootstrap-native-start-cancel"
            disabled={busy}
            onClick={onCancel}
          >
            返回探索
          </button>
        </div>
      </section>
    </section>
  );
}

