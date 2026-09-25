/**
 * ORD-0326 / Q67=① -- the only place a server's own sentence is allowed to reach the DOM.
 *
 * Q64=① forbids upstream prose in the main copy; Q67=① says that same sentence, attributed and inside the
 * 技术详情 slot, is compliant attribution. This component is that slot, so a screen cannot accidentally
 * promote the sentence into a headline by rendering it directly.
 *
 * It renders strings and nothing else: every character comes from `serverReasonScreenTexts`, which is
 * where the two-sided assertions live.
 */
import type { ServerReason } from "../lib/serverReason";
import { serverReasonScreenTexts } from "../lib/serverReason";

type Props = {
  reason: ServerReason | null | undefined;
  zh: boolean;
  /** Stable prefix so a test can name the slot it read, not just the text inside it. */
  testId?: string;
};

export function ServerReasonDetail({ reason, zh, testId = "server-reason" }: Props) {
  if (!reason) return null;
  const t = serverReasonScreenTexts(reason, zh);
  return (
    <details className="v8-advanced" data-testid={testId} data-server-reason-kind={reason.kind}>
      <summary>{zh ? "技术详情" : "Advanced / technical detail"}</summary>
      <p className="v8-server-reason" data-testid={`${testId}-sentence`}>
        <span className="v8-kicker" data-attribution={t.attribution}>{t.label}</span>
        <code data-testid={`${testId}-text`}>{t.sentence}</code>
      </p>
      <p
        className="v8-server-reason-fields"
        data-testid={`${testId}-fields`}
        data-http-status={reason.http_status ?? ""}
        data-request-id={reason.request_id ?? ""}
      >
        {t.machine}
      </p>
    </details>
  );
}

/**
 * What a call site puts in its *main* copy. A device-written sentence when the server wrote nothing; a
 * pointer at the fold when it did. Screens that already have R14 copy (`copyFor`) keep using that and
 * render only the fold -- this exists so a bare `setMessage(x)` cannot become the leak point again.
 */
export function serverReasonHeadline(reason: ServerReason | null | undefined, zh: boolean): string | null {
  if (!reason) return null;
  return serverReasonScreenTexts(reason, zh).headline;
}
