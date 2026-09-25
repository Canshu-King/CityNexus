import { RawFacts, rawFactLines } from "../lib/rawFacts";

/**
 * The Q64=1 whitelist block.
 *
 * Only what this device measured reaches the DOM: the status it saw, the media type the answer
 * carried, the byte count.  No fragment of the upstream body is forwarded, so a screenshot or an
 * evidence file cannot carry a credential that arrived here.  The label above the block is the
 * attribution R14 asks for -- it says whose reading this is, so it cannot be mistaken for the
 * server's own words.
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
        {rawFactLines(facts).map((line) => `${line}\n`)}
      </pre>
    </div>
  );
}
