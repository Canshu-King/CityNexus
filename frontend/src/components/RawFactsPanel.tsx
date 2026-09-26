import { RawFacts, rawFactEntries } from "../lib/rawFacts";
import { receiptLabel } from "../lib/errorReceipt";

/**
 * The Q64=1 whitelist block.
 *
 * Only what this device measured reaches the DOM: the status it saw, the media type the answer
 * carried, the byte count.  No fragment of the upstream body is forwarded, so a screenshot or an
 * evidence file cannot carry a credential that arrived here.  The label above the block is the
 * attribution R14 asks for -- it says whose reading this is, so it cannot be mistaken for the
 * server's own words.
 *
 * ORD-0353 ③ / Q70: each reading is its own element wearing `data-cnx-field` with the contract
 * name, because the printed label is this screen's wording and a translation or a re-word cannot
 * be allowed to silently rename the field.  The receipt line is the one value here the server
 * authored, and `errorReceipt.ts` already decided whether it exists: when it does not, the line
 * says so by name instead of leaving a 编号 slot to be filled by anything nearby.
 */
export function RawFactsPanel({
  facts,
  zh,
  testId,
}: {
  facts: RawFacts;
  zh: boolean;
  testId: string;
}) {
  return (
    <div className="cnx-raw-facts">
      <span className="cnx-raw-facts-label" data-testid={`${testId}-label`}>
        {zh ? "这台设备自己量到的回读字段" : "Fields this device measured"}
      </span>
      <pre
        className="cnx-raw-facts-reading"
        data-testid={testId}
        data-raw-http-status={facts.http_status ?? ""}
        data-raw-content-type={facts.content_type ?? ""}
        data-raw-bytes={facts.bytes ?? ""}
      >
        {rawFactEntries(facts).map((entry) => (
          <span
            key={entry.field}
            className="cnx-raw-facts-field"
            data-testid={`${testId}-${entry.field}`}
            data-cnx-field={entry.field}
            data-cnx-value={entry.value}
          >
            {`${entry.line}\n`}
          </span>
        ))}
      </pre>
      <span
        className="cnx-raw-facts-receipt"
        data-testid={`${testId}-receipt`}
        {...facts.receipt.attrs}
      >
        {`${receiptLabel(facts.receipt.present, zh)}：${facts.receipt.text}`}
      </span>
    </div>
  );
}
