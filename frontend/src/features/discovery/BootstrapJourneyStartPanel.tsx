import { useState } from "react";
import { cityNexusApi } from "../../api/citynexus";

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
      const knownMessage = error instanceof Error && [
        "没有生成可启动的行程方案。",
        "行程还没有启动。",
      ].includes(error.message);
      setMessage(knownMessage && error instanceof Error ? error.message : "启动失败，草稿已保留。");
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

