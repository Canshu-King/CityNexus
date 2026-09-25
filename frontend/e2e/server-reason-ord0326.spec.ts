/**
 * ORD-0326 requirement ③ -- both directions, asserted on the strings that reach the screen.
 *
 * Why strings and not markup: Playwright's own transform rewrites JSX into a node shape that
 * `react-dom/server` rejects ("Objects are not valid as a React child ... {__pw_type, type, props, key}"),
 * which I measured on a one-line JSX module before concluding it. `ServerReasonDetail` renders exactly
 * what `serverReasonScreenTexts` returns and adds no text of its own, so this covers what a traveller
 * would read; the browser-level pass still belongs to the normal e2e suite and this spec does not
 * pretend to replace it.
 *
 * This spec starts no server: the repo's playwright.config.ts would bind 127.0.0.1:8000, which is NOT
 * AVAILABLE by ruling, and `reuseExistingServer: true` means whatever answers there may not be mine.
 */
import { test, expect } from "@playwright/test";
import { describeServerReason, serverReasonScreenTexts } from "../src/lib/serverReason";
import { serverReasonHeadline } from "../src/components/ServerReasonDetail";

/** The envelope main.py:492 answers with: {"error":{code,message,message_key,trace_id,details}}. */
const SERVER_SENTENCE = "Stay option could not become authoritative Journey truth: window overlap";

function screen(reason: ReturnType<typeof describeServerReason>, zh = true) {
  const t = serverReasonScreenTexts(reason, zh);
  return { ...t, headline: serverReasonHeadline(reason, zh) ?? "" };
}

test("direction A - server wrote a sentence: that sentence and its request_id must reach the screen", () => {
  const s = screen(describeServerReason({
    envelope: { error: { code: "VALIDATION_ERROR", message: SERVER_SENTENCE, trace_id: "req-7f3a91" } },
    http_status: 422, content_type: "application/json", body_bytes: 181,
    response_received: true, elapsed_ms: 64,
  }));
  expect(s.attribution).toBe("server");
  expect(s.label).toBe("服务器自己写的原因");
  /* the sentence, verbatim, in the detail slot */
  expect(s.sentence).toBe(SERVER_SENTENCE);
  /* the six allowed fields, and the id a reviewer needs to look the request up */
  expect(s.machine).toContain("http_status=422");
  expect(s.machine).toContain("content_type=application/json");
  expect(s.machine).toContain("body_bytes=181");
  expect(s.machine).toContain("response_received=yes");
  expect(s.machine).toContain("elapsed_ms=64");
  expect(s.machine).toContain("request_id=req-7f3a91");
  /* and the sentence is NOT what the main copy says -- that is the Q64=1 boundary */
  expect(s.headline).not.toContain(SERVER_SENTENCE);
  expect(s.headline).toContain("技术详情");
});

test("direction B - server gave nothing: a named fallback that says it is not HTTP 200 and why", () => {
  const cases: Array<[string, Parameters<typeof describeServerReason>[0], string]> = [
    ["zero bytes", { http_status: 500, body_bytes: 0, content_type: "text/plain", response_received: true }, "HTTP 500"],
    ["html instead of api answer", { http_status: 200, body_bytes: 4211, content_type: "text/html", response_received: true }, "HTTP 200"],
    ["nothing answered at all", { response_received: false }, "没有状态码"],
    ["a code with no text", { envelope: { error: { code: "CATALOG_EMPTY" } }, http_status: 409, body_bytes: 33, response_received: true }, "HTTP 409"],
  ];
  for (const [label, evidence, expectedNaming] of cases) {
    const reason = describeServerReason(evidence);
    expect(reason.kind, label).toBe("no_server_sentence");
    const s = screen(reason);
    expect(s.attribution, label).toBe("device");
    expect(s.label, label).toBe("这台设备自己的说明（服务器没给句子）");
    /* ③ requires the fallback to be named, and to name the status: not one shared blank */
    expect(s.sentence, label).toContain(expectedNaming);
    expect(s.sentence, label).not.toContain(SERVER_SENTENCE);
    expect(s.headline.length, label).toBeGreaterThan(0);
    /* no stack, no raw document, no exception object may ride along */
    for (const blob of [s.sentence, s.headline, s.machine, s.label]) {
      expect(blob, label).not.toMatch(/Traceback|File \"/);
      expect(blob, label).not.toContain("<!DOCTYPE");
      expect(blob, label).not.toContain("[object Object]");
    }
  }
});

test("a parked raw body cannot ride the channel: only named envelope fields are read", () => {
  const raw = '{"error":{"message":"x"}}\nTraceback (most recent call last):\n  File "/app/main.py", line 1, in <module>';
  const reason = describeServerReason({
    /* handing the document itself in, instead of a parsed envelope, must answer "no sentence" */
    envelope: raw, http_status: 500, body_bytes: raw.length,
    content_type: "application/json", response_received: true,
  });
  expect(reason.kind).toBe("no_server_sentence");
  const s = screen(reason);
  expect(s.sentence).not.toContain("Traceback");
  expect(s.sentence).not.toContain("main.py");
  /* the machine line still reports the bytes, so the absence is checkable rather than silent */
  expect(s.machine).toContain(`body_bytes=${raw.length}`);
});

test("a multi-line message is refused as a sentence, so an exception object cannot impersonate a reason", () => {
  const reason = describeServerReason({
    envelope: { error: { message: "OperationalError: database is locked\n  at Session.commit (sqlalchemy)" } },
    http_status: 503, response_received: true,
  });
  expect(reason.kind).toBe("no_server_sentence");
  expect(screen(reason).sentence).toContain("HTTP 503");
});
