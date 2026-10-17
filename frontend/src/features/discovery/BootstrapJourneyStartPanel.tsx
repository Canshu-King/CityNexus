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
      setMessage(
        "Confirm that the admission price is unknown and excluded from the total.",
      );
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
        throw new Error("The server returned no startable native plan.");
      }
      await cityNexusApi.selectPlan(journeyId, plan.id);
      const startedJourney = await cityNexusApi.startJourney(journeyId);
      if (startedJourney?.context?.journey_status !== "ACTIVE") {
        throw new Error("行程尚未启动。");
      }
      await onStarted();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The native journey could not be started.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="v8-join-entry" data-testid="bootstrap-native-start">
      <section className="v8-loading" aria-labelledby="bootstrap-native-start-title">
        <div className="v8-brand-mark">CN</div>
        <h1 id="bootstrap-native-start-title">Start this native Journey</h1>
        <p>Selected public place: {placeId}.</p>
        <p>
          Admission price: unknown. It is excluded from the total; booking and payment are unavailable here.
        </p>
        <label>
          <input
            type="checkbox"
            data-testid="bootstrap-unknown-cost-ack"
            checked={acceptUnknownCost}
            onChange={(event) => setAcceptUnknownCost(event.target.checked)}
          />
          I understand that the admission price is unknown and excluded from the total.
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
            {busy ? "Starting…" : "Generate and start Journey"}
          </button>
          <button
            type="button"
            className="v8-outline-button"
            data-testid="bootstrap-native-start-cancel"
            disabled={busy}
            onClick={onCancel}
          >
            Cancel
          </button>
        </div>
      </section>
    </main>
  );
}

