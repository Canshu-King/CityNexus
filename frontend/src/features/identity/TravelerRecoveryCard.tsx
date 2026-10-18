import { useState } from "react";

import { useLocale } from "../../i18n/LocaleContext";
import {
  adoptSignedSession,
  signedBearerHeaders,
  signedTravelerId,
} from "../../lib/travelerSession";

/**
 * Reform 2026-10-18: the traveller's own way back.
 *
 * The server keeps a digest and a lifecycle; this card is where the person gets the secret (once)
 * and where they present it after a tab, a device or a window has gone. It never shows a raw reason
 * code: "used", "expired", "revoked", "wrong secret", "locked" and "unknown" are six different
 * things to a person, and each one gets its own sentence.
 */

const REFUSAL_KEYS: Record<string, string> = {
  RECOVERY_UNKNOWN: "me.recoveryRefusedUnknown",
  RECOVERY_USED: "me.recoveryRefusedUsed",
  RECOVERY_EXPIRED: "me.recoveryRefusedExpired",
  RECOVERY_REVOKED: "me.recoveryRefusedRevoked",
  RECOVERY_SECRET_MISMATCH: "me.recoveryRefusedMismatch",
  RECOVERY_LOCKED: "me.recoveryRefusedLocked",
};

type Issued = { recovery_id: string; recovery_secret: string; expires_at: string };

export function TravelerRecoveryCard() {
  const { t } = useLocale();
  const travelerId = signedTravelerId();
  const [issued, setIssued] = useState<Issued | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [credentialId, setCredentialId] = useState("");
  const [secret, setSecret] = useState("");

  const create = async () => {
    if (!travelerId) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`/api/v1/travelers/${travelerId}/recovery`, {
        method: "POST",
        headers: { ...signedBearerHeaders() },
      });
      if (!response.ok) {
        setMessage(t("me.recoveryCreateRefused"));
        return;
      }
      setIssued((await response.json()) as Issued);
    } catch {
      setMessage(t("me.recoveryCreateRefused"));
    } finally {
      setBusy(false);
    }
  };

  const redeem = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch("/api/v1/travelers/recovery/redeem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recovery_id: credentialId.trim(),
          recovery_secret: secret.trim(),
        }),
      });
      const body = (await response.json().catch(() => ({}))) as {
        error?: { reason_code?: string };
      } & Record<string, unknown>;
      if (!response.ok) {
        const code = String(body.error?.reason_code ?? "");
        setMessage(t(REFUSAL_KEYS[code] ?? "me.recoveryRefusedUnknown"));
        return;
      }
      if (!adoptSignedSession(body)) {
        setMessage(t("me.recoveryRefusedUnknown"));
        return;
      }
      setMessage(t("me.recoveryDone"));
      window.setTimeout(() => window.location.reload(), 400);
    } catch {
      setMessage(t("me.recoveryRefusedUnknown"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="v8-me-card" data-testid="me-recovery">
      <span className="v8-kicker">{t("me.recoveryTitle")}</span>
      <p>{t("me.recoveryExplain")}</p>

      {travelerId ? (
        issued ? (
          <div data-testid="me-recovery-once">
            <p>{t("me.recoveryOnce")}</p>
            <p>
              <code data-testid="me-recovery-id">{issued.recovery_id}</code>
            </p>
            <p>
              <code data-testid="me-recovery-secret">{issued.recovery_secret}</code>
            </p>
            <button
              type="button"
              className="v8-outline-button"
              data-testid="me-recovery-saved"
              onClick={() => setIssued(null)}
            >
              {t("me.recoverySaved")}
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="v8-outline-button"
            data-testid="me-recovery-create"
            disabled={busy}
            onClick={() => void create()}
          >
            {t("me.recoveryCreate")}
          </button>
        )
      ) : (
        <p className="v8-muted" data-testid="me-recovery-needs-signin">
          {t("me.recoveryNeedSignIn")}
        </p>
      )}

      <details className="v8-advanced" data-testid="me-recovery-redeem">
        <summary>{t("me.recoveryRedeemTitle")}</summary>
        <label>
          <span>{t("me.recoveryId")}</span>
          <input
            data-testid="me-recovery-id-input"
            value={credentialId}
            onChange={(event) => setCredentialId(event.target.value)}
          />
        </label>
        <label>
          <span>{t("me.recoverySecret")}</span>
          <input
            data-testid="me-recovery-secret-input"
            type="password"
            value={secret}
            onChange={(event) => setSecret(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="v8-primary"
          data-testid="me-recovery-submit"
          disabled={busy || !credentialId.trim() || !secret.trim()}
          onClick={() => void redeem()}
        >
          {t("me.recoverySubmit")}
        </button>
      </details>

      {message ? (
        <p className="v8-muted" role="status" data-testid="me-recovery-message">
          {message}
        </p>
      ) : null}
    </article>
  );
}
