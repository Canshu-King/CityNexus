import { type RawFacts } from "../lib/rawFacts";
import { readErrorReceipt, receiptLabel } from "../lib/errorReceipt";
import { useT } from "../i18n/LocaleContext";

/**
 * The same three device-measured fields RawFactsPanel prints, mounted the way Q70 asks for them:
 * one element per contract field, `data-cnx-field` carrying the field's own name, and the value as
 * data -- so a gate can bind the anchor instead of scraping a `<pre>`. RawFactsPanel is left alone:
 * accepted gates already read its `data-raw-*` shape, and moving those readers is not this order's.
 *
 * Q71, the reason nothing else may be added here: no fragment of an upstream answer's text goes into
 * the DOM by any route, `data-*` included. Only what this device measured is mounted, and the
 * receipt line is the server's own value or the literal that says there is none (`lib/errorReceipt`).
 */
export function CnxMeasuredFacts({
  facts,
  zh,
  testId,
  envelope,
}: {
  facts: RawFacts;
  zh: boolean;
  testId: string;
  /** The parsed rejection envelope, when this device read one. Nothing is printed from its text. */
  envelope?: unknown;
}) {
  const receipt = readErrorReceipt(envelope);
  const t = useT();
  const fields: Array<{ name: string; value: string | null; label: string }> = [
    { name: "http_status", value: facts.http_status === null ? null : String(facts.http_status),
      label: t("detail.measuredHttpLabel") },
    { name: "content_type", value: facts.content_type, label: t("detail.measuredContentType") },
    { name: "body_bytes", value: facts.bytes === null ? null : String(facts.bytes),
      label: t("detail.measuredBytes") },
  ];
  return (
    <>
      {fields
        .filter((field) => field.name !== "http_status")
        .map((field) => (
        <span
          key={field.name}
          className="cnx-measured-fact"
          data-testid={`${testId}-${field.name}`}
          {...(field.value === null
            ? {}
            : { "data-cnx-field": field.name, "data-cnx-value": field.value })}
        >
          {field.value === null
            ? t("detail.measuredNoneSuffix", { label: field.label })
            : `${field.label} ${field.value}`}
        </span>
      ))}
      {/* ORD-0440 second half, with Q68 kept whole. The number on this line is the server's - that is
          the point of it, a traveller must be able to repeat it - so it cannot be deleted, and it
          cannot be pushed into a `data-*` instead (attribute cells are never exonerated, and
          `error_receipt_id` is not one of the six fields a slot may name). The one shape the
          exposure rule does accept is an upstream text cell inside a fold that also carries a field
          this device measured, under its contract name.
          The anchor is written literally because the ruler reads the attribute name off the source: a
          spread like `{...{ "data-cnx-field": name }}` is invisible to it, which is how the first
          version of this fold measured back as still a cell. The same element that anchors the fold is
          the line that shows the reading, so nothing is duplicated on screen. `open` is load-bearing:
          a collapsed fold would hide a line the traveller is entitled to see, which is X-5's defect
          approached from the other side. */}
      <details className="cnx-measured-fact-fold" data-testid={`${testId}-receipt-fold`} open>
        <summary data-testid={`${testId}-receipt-summary`}>
          {t("detail.receiptFoldSummary")}
        </summary>
        <span
          className="cnx-measured-fact"
          data-testid={`${testId}-http_status`}
          data-cnx-field="http_status"
          {...(facts.http_status === null
            ? {}
            : { "data-cnx-value": String(facts.http_status) })}
        >
          {facts.http_status === null
            ? t("detail.receiptHttpNone")
            : `${t("detail.measuredHttpLabel")} ${facts.http_status}`}
        </span>
        <span className="cnx-measured-fact" data-testid={`${testId}-receipt`} {...receipt.attrs}>
          {`${receiptLabelOf(receipt.present, t)} ${receipt.text}`}
        </span>
      </details>
    </>
  );
}

/* This lives outside the component, so there is no hook in scope: the word function is passed in
   rather than reached for. `zh` is gone from this signature because the language choice now belongs
   to the dictionary lookup, not to a boolean threaded through the call. */
function receiptLabelOf(
  present: boolean,
  t: (key: string, params?: Record<string, string | number>) => string,
): string {
  return present ? t("detail.receiptLabel") : t("detail.receiptLabelAbsent");
}
