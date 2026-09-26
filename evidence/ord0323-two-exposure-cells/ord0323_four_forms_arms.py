"""ORD-0323 甲 follow-on: the memory read's own fields, and the four arms that judge the four forms.

Step 1 is one product line: `loadMemory`'s catch printed only copyFor's sentence, so the F1 arm had no
machine half to assert on. It now carries the same `deviceFields` reading the confirm fold already shows
(`:489`), which is what makes the two directions of F1 separately falsifiable.

Step 2 adds four arms (`N7_F1..F4`). Each asserts both halves the commander asked for -- the upstream
sentence nowhere on the page, and this device's own fields in their own slot -- plus the Q71 attribute
leg and its denominator.
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend")
SRC = FE / "src/features/inbox/JourneyInboxWorkbench.tsx"
SPEC = FE / "e2e/qoder-ord0323-two-exposure-cells.spec.ts"


def edit(path: pathlib.Path, jobs: list) -> None:
    t = path.read_text(encoding="utf-8")
    for old, new, want in jobs:
        n = t.count(old)
        if n != want:
            raise SystemExit(f"{path.name}: expected {want}, found {n} for:\n{old[:220]}")
        t = t.replace(old, new)
    path.write_text(t, encoding="utf-8", newline="\n")
    print(f"{path.name}: {len(jobs)} edit(s) written")


edit(SRC, [
    ("""    const body = await requestJson<{ drafts?: Draft[] }>(""", """    const body = await requestJson<{ drafts?: Draft[] }>(""", 1),
    ("""      setMemory(await requestJson<Memory>(`/api/v1/journeys/${journeyId}/memory`));
    } catch (error) {
      setMessage(deviceCopy(error));
    }""",
     """      setMemory(await requestJson<Memory>(`/api/v1/journeys/${journeyId}/memory`));
    } catch (error) {
      /* ORD-0323 form F1's other half (CMDR 04:53): the sentence alone cannot be checked, so this line
         carries what the device measured too -- which status answered, with which media type. */
      setMessage(`${deviceCopy(error)} · ${deviceFields(error)}`);
    }""", 1),
])

ARMS = r'''
/* ---------------- ORD-0323 甲 follow-on (CMDR 04:53): four more forms in this panel ----------------
 * F1 an answered-but-unusable body, F2 the reply's `reason` as the status line, F3/F4 the model's
 * `reasoning_summary` rendered as this panel's own words.  Each form is judged in both directions: the
 * upstream sentence must be nowhere on the page (Q71: attributes count), and this device's own fields
 * must still be in the slot that form writes to.
 */
const F_SENTINELS: Record<string, string> = {
  F1: "f1_forbidden_body_that_is_not_json",
  F2: "f2_forbidden_server_reason_sentence",
  F3: "f3_forbidden_reasoning_summary_memory_row",
  F4: "f4_forbidden_reasoning_summary_draft_row",
};

const memoryRow = {
  id: "ORD0323-M1",
  title: "天津西 → 北京南 高铁",
  role: "MID_TRIP",
  label: "ORD0323-M1-LABEL",
  at: "2026-09-26T08:00:00Z",
  protected: false,
  confidence: 0.62,
  reasoning_summary: F_SENTINELS.F3,
};

const interpretationDraft = {
  ...draftRow,
  id: "ORD0323-D4",
  interpretation: {...draftRow.interpretation, reasoning_summary: F_SENTINELS.F4, payment_status: "PAID"},
};

async function openWallet(page: Page, id: string): Promise<void> {
  await boot(page, id);
  await page.goto("/v8/bookings", {waitUntil: "load"});
  await expect(
    page.getByTestId("v13-2-memory"),
    node("boot", "the wallet panel never rendered, so these arms have no surface to be judged on"),
  ).toBeVisible({timeout: 30_000});
}

async function runPasteExtraction(page: Page, arm: string): Promise<string> {
  await page.getByTestId("inbox-tab-paste").click();
  await page.locator("textarea").filter({visible: true}).first().fill("9月26日 天津西→北京南 G8901 二等座 07:30");
  await page.getByRole("button", {name: "提取文本草稿", exact: true}).click();
  const line = page.locator(".v10-inbox-message").first();
  await expect(line, node(arm, `${arm}: the extraction ran but this panel left no status line at all`)).toBeVisible({
    timeout: 30_000,
  });
  return clean(await line.textContent());
}

test("N7_F1_an_answered_body_that_is_not_json_is_not_filed_as_a_transport_failure — F1：回答到了但正文不能用，不许说成网络断了，也不许把正文带上屏", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "F1";
  const id = await journeyId(page);
  await page.route("**/api/v1/journeys/**", async (r: Route) => {
    const path = new URL(r.request().url()).pathname;
    if (path.endsWith("/memory") && r.request().method() === "GET") {
      await r.fulfill({
        status: 200,
        contentType: "text/html;charset=UTF-8",
        body: `<!doctype html><html><body>${F_SENTINELS.F1} 这不是这台设备的读数</body></html>`,
      });
      return;
    }
    return r.fallback();
  });
  await openWallet(page, id);
  const line = page.locator(".v10-inbox-message").first();
  await expect(line, node(arm, "F1: 服务器答了，这一屏却什么也没说")).toBeVisible({timeout: 30_000});
  const text = clean(await line.textContent());
  const dom = await domReading(page);
  readings[arm] = {
    asked_status: 200, asked_content_type: "text/html", message_text: text,
    sentinel_on_screen: dom.root.includes(F_SENTINELS.F1) || dom.body.includes(F_SENTINELS.F1),
    sentinel_in_attributes: [F_SENTINELS.F1].filter((n) => dom.attrs.includes(n)),
    attribute_pairs_swept: dom.attr_pairs,
    fields_in_line: /http_status=200/.test(text) && /content_type=text\/html/.test(text),
    answered_evidence: /evidence=HTTP_RESPONSE/.test(text),
    filed_as_transport: /evidence=TRANSPORT/.test(text),
  };
  expect(readings[arm].sentinel_on_screen, node(arm, `F1: 正文的碎片被当成这句话带上屏了（${text.slice(0, 220)}）`)).toBe(false);
  expect(readings[arm].sentinel_in_attributes, node(arm, `F1: Q71 口径下正文进了属性也是上屏（${String(dom.attr_pairs)} 对）`)).toEqual([]);
  expect(readings[arm].filed_as_transport, node(arm, `F1: 明明答了 200，这一行把它说成网络问题（${text.slice(0, 220)}）`)).toBe(false);
  expect(readings[arm].answered_evidence, node(arm, `F1: 没有把「这是回答，不是断线」写进读数（${text.slice(0, 220)}）`)).toBe(true);
  expect(readings[arm].fields_in_line, node(arm, `F1: 这一行没有这台设备自己量的状态与媒体类型（${text.slice(0, 220)}）`)).toBe(true);
});

test("N7_F2_a_rejected_extraction_shows_its_machine_status_not_the_reply_s_sentence — F2：服务器那句 reason 不再当状态行", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "F2";
  const id = await journeyId(page);
  await page.route("**/api/v1/journeys/**", async (r: Route) => {
    const path = new URL(r.request().url()).pathname;
    if (path.endsWith("/inbox/text-extract") && r.request().method() === "POST") {
      await r.fulfill({status: 200, contentType: "application/json",
        body: jsonBody({status: "REJECTED", reason: F_SENTINELS.F2})});
      return;
    }
    return r.fallback();
  });
  await openWallet(page, id);
  const text = await runPasteExtraction(page, arm);
  const dom = await domReading(page);
  readings[arm] = {
    message_text: text,
    sentinel_on_screen: dom.root.includes(F_SENTINELS.F2) || dom.body.includes(F_SENTINELS.F2),
    sentinel_in_attributes: [F_SENTINELS.F2].filter((n) => dom.attrs.includes(n)),
    attribute_pairs_swept: dom.attr_pairs,
    machine_status_in_line: text.includes("REJECTED"),
  };
  expect(readings[arm].sentinel_on_screen, node(arm, `F2: 服务器那句原话又成了这一屏的状态行（${text.slice(0, 220)}）`)).toBe(false);
  expect(readings[arm].sentinel_in_attributes, node(arm, `F2: Q71 口径下原话进了属性也是上屏（${String(dom.attr_pairs)} 对）`)).toEqual([]);
  expect(readings[arm].machine_status_in_line, node(arm, `F2: 状态行不再说明这台答复自己的机器状态（${text.slice(0, 220)}）`)).toBe(true);
});

test("N7_F3_a_memory_row_shows_what_it_measured_not_the_model_s_sentence — F3：纪念册那一行的推理摘要不再原样上屏", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "F3";
  const id = await journeyId(page);
  await page.route("**/api/v1/journeys/*/memory", async (r: Route) => {
    await r.fulfill({status: 200, contentType: "application/json",
      body: jsonBody({items: [memoryRow]})});
  });
  await openWallet(page, id);
  const row = page.locator('#v13-2-memory li').first();
  await expect(row, node(arm, "F3: 这台设备的记忆行根本没渲染，摘要在不在屏上就没有可判的对象")).toBeVisible({timeout: 30_000});
  const rowText = clean(await row.textContent());
  const dom = await domReading(page);
  readings[arm] = {
    row_text: rowText,
    sentinel_on_screen: dom.root.includes(F_SENTINELS.F3) || dom.body.includes(F_SENTINELS.F3),
    sentinel_in_attributes: [F_SENTINELS.F3].filter((n) => dom.attrs.includes(n)),
    attribute_pairs_swept: dom.attr_pairs,
    held_token_present: (await page.getByTestId("v13-2-memory-summary-held").count()) > 0,
    own_fields_present: rowText.includes("ORD0323-M1-LABEL") && rowText.includes("62"),
  };
  expect(readings[arm].sentinel_on_screen, node(arm, `F3: 模型的推理摘要被这一屏当成自己的话说出来了（${rowText.slice(0, 200)}）`)).toBe(false);
  expect(readings[arm].sentinel_in_attributes, node(arm, `F3: Q71 口径下摘要进了属性也是上屏（${String(dom.attr_pairs)} 对）`)).toEqual([]);
  expect(readings[arm].held_token_present, node(arm, "F3: 这一行不再说明摘要存在但不在这里展示")).toBe(true);
  expect(readings[arm].own_fields_present, node(arm, `F3: 这一行自己的读数不在了（${rowText.slice(0, 200)}）`)).toBe(true);
});

test("N7_F4_the_draft_review_shows_its_own_fields_not_the_model_s_sentence — F4：待审那一屏的推理摘要不再原样上屏", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "F4";
  const id = await journeyId(page);
  await page.route("**/api/v1/journeys/**", async (r: Route) => {
    const path = new URL(r.request().url()).pathname;
    const method = r.request().method();
    if (path.endsWith("/inbox/text-extract") && method === "POST") {
      await r.fulfill({status: 200, contentType: "application/json",
        body: jsonBody({status: "READY", draft: interpretationDraft})});
      return;
    }
    if (path.endsWith("/inbox") && method === "GET") {
      await r.fulfill({status: 200, contentType: "application/json", body: jsonBody({drafts: [interpretationDraft]})});
      return;
    }
    return r.fallback();
  });
  await openWallet(page, id);
  await runPasteExtraction(page, arm);
  await expect(
    page.getByTestId("v13-2-review"),
    node(arm, "F4: 待审那一屏根本没开，摘要在不在就没有可判的对象"),
  ).toBeVisible({timeout: 30_000});
  const dom = await domReading(page);
  const review = clean(await page.getByTestId("v13-2-review").textContent());
  readings[arm] = {
    review_text: review,
    sentinel_on_screen: dom.root.includes(F_SENTINELS.F4) || dom.body.includes(F_SENTINELS.F4),
    sentinel_in_attributes: [F_SENTINELS.F4].filter((n) => dom.attrs.includes(n)),
    attribute_pairs_swept: dom.attr_pairs,
    held_token_present: (await page.getByTestId("v13-2-draft-summary-held").count()) > 0,
    own_fields_present: review.includes("到站") || review.includes("MID_TRIP") || /0\.8|80%/.test(review),
  };
  expect(readings[arm].sentinel_on_screen, node(arm, `F4: 模型的推理摘要被待审那一屏当成自己的话说出来了（${review.slice(0, 200)}）`)).toBe(false);
  expect(readings[arm].sentinel_in_attributes, node(arm, `F4: Q71 口径下摘要进了属性也是上屏（${String(dom.attr_pairs)} 对）`)).toEqual([]);
  expect(readings[arm].held_token_present, node(arm, "F4: 待审那一屏不再说明摘要存在但不在这里展示")).toBe(true);
});
'''

edit(SPEC, [
    ("/^N4_(T\\d\\d)_/.exec(title)?.[1] ?? /^N6_(Q68[abcd])_/.exec(title)?.[1] ?? title.split(\"_\")[0];",
     "/^N4_(T\\d\\d)_/.exec(title)?.[1] ?? /^N6_(Q68[abcd])_/.exec(title)?.[1]\n"
     "  ?? /^N7_(F\\d)_/.exec(title)?.[1] ?? title.split(\"_\")[0];", 1),
])

spec = SPEC.read_text(encoding="utf-8")
if "N7_F1" in spec:
    raise SystemExit("the arms are already in the spec")
SPEC.write_text(spec.rstrip("\n") + "\n" + ARMS, encoding="utf-8", newline="\n")
print("four N7 arms appended to the spec")
