/* Name-anchor guard for the recycle-bin screen (lane 82f55d8a).
 *
 * Why this exists instead of a re-pinned number: `journeyTrash.ts` shipped line-number citations twice and
 * rotted twice -- ORD-0535's r8 re-measured all of them at one tip, and r9 had to move two of them again
 * after other lanes landed above `app.main`. A drifted line anchor does not fail; it quietly starts
 * describing whatever line landed there, which is worse than a red test. The ruling on this family is that
 * a shipped citation names its subject, so this file converts the last ten numbers to names and then keeps
 * the conversion honest:
 *
 *  A1  no `file.ext:<digits>` citation survives in the shipped file -- re-introducing one reddens here;
 *  A2  every name the comment quotes resolves in the file it points at, saying what the comment claims;
 *  A3  the shipped file still carries each of those names -- deleting a citation is not converting it.
 *
 * All three arms read source text: no browser, no backend, no store, no seed. A green here means the
 * screen's comments describe real code at *this* checkout; it says nothing about rendering.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { expect, test } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SHIPPED = join(ROOT, "frontend", "src", "features", "trash", "journeyTrash.ts");
const FILE = "e2e/qoder-82f55d8a-journeytrash-name-anchors-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const EVIDENCE = process.env.CITYNEXUS_NAMEANCHOR_EVIDENCE ?? "";
const RUN = process.env.CITYNEXUS_NAMEANCHOR_RUN ?? "nameanchor-unset";

/** Each entry: where the comment points, the string the comment quotes, and what that string proves. */
const ANCHORS: { file: string; needle: string; claim: string }[] = [
  {
    file: "backend/app/main.py",
    needle: '@app.post("/api/v1/journeys/{journey_id}/undelete',
    claim: "the write door exists as a POST on that path",
  },
  {
    file: "backend/app/main.py",
    needle: 'refused.reason_code = "JOURNEY_NOT_DELETED"',
    claim: "the refusal answers instead of a fake success",
  },
  {
    file: "backend/app/main.py",
    needle: '@app.get("/api/v1/recycle-bin/journeys", response_model=list[RecycleBinJourney])',
    claim: "the read door exists and answers the binned-row schema",
  },
  {
    file: "backend/app/main.py",
    needle: ".order_by(Journey.deleted_at.desc(), Journey.id)",
    claim: "the server, not the client, orders the list newest-deletion first",
  },
  {
    file: "backend/app/main.py",
    needle: "live = select(Journey).where(Journey.deleted_at.is_(None))",
    claim: "the live list keeps its deleted_at IS NULL promise",
  },
  {
    file: "contracts/openapi.yaml",
    needle: "/recycle-bin/journeys:",
    claim: "the read door is declared in the contract",
  },
  {
    file: "frontend/src/generated/api.ts",
    needle: '"/recycle-bin/journeys": {',
    claim: "the door is generated into the client this screen calls",
  },
  {
    file: "frontend/src/generated/api.ts",
    needle: 'RecycleBinJourney: components["schemas"]["Journey"] & {',
    claim: "the row type is typed from the contract, not re-declared",
  },
  {
    file: "backend/app/schemas.py",
    needle: "deleted_at: datetime",
    claim: "each row carries the stored deletion moment",
  },
  {
    file: "backend/app/schemas.py",
    needle: 'bin_state: Literal["IN_RECYCLE_BIN"]',
    claim: "and the bin state the screen must not infer",
  },
];

const read = (rel: string) => readFileSync(join(ROOT, rel), "utf8");
const shipped = () => readFileSync(SHIPPED, "utf8");

test("A1 no line-number citation survives in the shipped file", () => {
  const digits = [...shipped().matchAll(/[\w./\\-]+\.(?:py|ts|tsx|js|json|yaml|yml|md):\d+/g)].map((m) => m[0]);
  expect(
    digits,
    node("A1", "a `file.ext:<digits>` citation is back; numbers rot silently, which is what this guard exists to stop"),
  ).toEqual([]);
});

test("A2 every quoted name resolves in the file it points at", () => {
  const missing = ANCHORS.filter((a) => !read(a.file).includes(a.needle));
  expect(
    missing.map((a) => `${a.file} no longer holds ${JSON.stringify(a.needle)} (${a.claim})`),
    node("A2", "a shipped comment names something the server-side code does not contain"),
  ).toEqual([]);
});

test("A3 the shipped file still names each of those anchors", () => {
  const text = shipped();
  const lost = ANCHORS.filter((a) => !text.includes(a.needle));
  expect(
    lost.map((a) => `journeyTrash.ts no longer quotes ${JSON.stringify(a.needle)}`),
    node("A3", "a citation was deleted rather than converted; the screen's claims are now unanchored"),
  ).toEqual([]);
  expect(ANCHORS.length, node("A3", "the anchor ledger itself shrank")).toBe(10);
  if (EVIDENCE) {
    mkdirSync(dirname(EVIDENCE), { recursive: true });
    writeFileSync(
      EVIDENCE,
      JSON.stringify(
        {
          generatedBy: "82f55d8a",
          guard: "journeytrash-name-anchors-r1",
          run: RUN,
          anchors: ANCHORS.map((a) => ({ ...a, resolves: read(a.file).includes(a.needle), quoted: text.includes(a.needle) })),
          digit_citations_left: [...text.matchAll(/[\w./\\-]+\.(?:py|ts|tsx|js|json|yaml|yml|md):\d+/g)].map((m) => m[0]),
          shipped_bytes: Buffer.byteLength(text),
        },
        null,
        1,
      ),
      "utf8",
    );
  }
});
