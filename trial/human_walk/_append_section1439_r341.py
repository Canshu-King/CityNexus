"""Append section 14.39: the fourth fault, the three-bucket ruler it fed, and what that changes.

Every number is pulled out of the live receipts while this runs, and the one number that has no surviving
artifact is named as having no surviving artifact instead of being quoted anyway: between the first and the
second of tonight's cutter fixes the reading-the-refusal count was 6, but the receipt carrying that was
overwritten by the second fix, so this section publishes only 64 -> 63 and 1 -> 5, which both copies do
carry.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
GOZERO = os.path.join(ROOT, "trial", "results", "20261026_gozero")
BW325 = "bw325-what-the-screen-says.txt"
BW326 = "bw326-what-the-panels-do-with-a-refusal.txt"
BW327 = "bw327-what-the-panels-say-instead.txt"
BW328 = "bw328-is-that-sentence-on-screen.txt"
BW338 = "bw338-where-a-read-field-actually-goes.txt"
KEPT = ".before_catch_body_fix"

CITES = {
    "revision": (BW325, "CATCH_BODY_REVISION"),
    "tally_326": (BW326, "TALLY panels="),
    "tally_327": (BW327, "TALLY catch="),
    "tally_328": (BW328, "TALLY rows="),
    "tally_338": (BW338, "TALLY bodies="),
    "provenance_338": (BW338, "API_MESSAGE_PROVENANCE"),
    "controls_338": (BW338, "text reaches state"),
    "ruler_325": ("trial/human_walk/_cmdr_screen_text_r325.py", "def comment_spans"),
    "ruler_340": ("trial/human_walk/_cmdr_field_destination_r340.py", "def api_message_recipe"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.38 补（10-29 深夜）"),
}


def read(rel):
    base = GOZERO if rel.startswith("bw") else ROOT
    path = os.path.join(base, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, cell in enumerate(read(rel).split("\n")) if needle in cell]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def keys(rel, needle, wanted):
    line = next((cell for cell in read(rel).split("\n") if cell.startswith(needle)), "")
    if not line:
        raise SystemExit("ABORT no %r line in %s" % (needle, rel))
    out = {}
    for key in wanted:
        match = re.search(r"%s=(\d+)" % key, line)
        if not match:
            raise SystemExit("ABORT %s carries no %s=" % (rel, key))
        out[key] = int(match.group(1))
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    shape = dict((k, int(v)) for k, v in re.findall(r"(files|bodies|shortest|median|longest)=(\d+)",
                                                    row_at(BW325, at["revision"])))
    new_326 = keys(BW326, "TALLY panels=", ("panels", "catch", "reads_the_refusal", "hides_the_refusal"))
    old_326 = keys(BW326 + KEPT, "TALLY panels=", ("panels", "catch", "reads_the_refusal",
                                                    "hides_the_refusal"))
    new_327 = keys(BW327, "TALLY catch=", ("catch", "says_zh", "says_en_only", "into_state", "nowhere",
                                            "retry_shaped", "reads_the_error"))
    new_328 = keys(BW328, "TALLY rows=", ("rows", "rendered"))
    new_338 = keys(BW338, "TALLY bodies=", ("bodies", "hands_server_text_to_state",
                                            "hands_server_structure_to_state", "compares_only",
                                            "reads_and_leaves_it_unused", "never_reads_a_server_field"))
    provenance = row_at(BW338, at["provenance_338"])
    throw = re.search(r"throws at `([^`]+):(\d+)`", provenance)
    text_rows = re.search(r"of the (\d+) bodies that hand a text field to state, (\d+) sit in a try",
                          provenance)
    if not (throw and text_rows):
        raise SystemExit("ABORT the provenance line in bw338 does not carry its throw site and its count")
    print("LIVE NUMBERS shape=%s new326=%s old326=%s new327=%s new338=%s throw=%s:%s"
          % (shape, new_326, old_326, new_327, new_338, throw.group(1), throw.group(2)))

    if new_326["catch"] != new_327["catch"] != new_338["bodies"]:
        raise SystemExit("ABORT the three rulers no longer share a denominator: %d / %d / %d"
                         % (new_326["catch"], new_327["catch"], new_338["bodies"]))
    if new_326["reads_the_refusal"] > old_326["catch"] or new_326["catch"] >= old_326["catch"]:
        raise SystemExit("ABORT the corrected denominator did not shrink, so the comment fix did not take")
    if sum(new_338[key] for key in ("hands_server_text_to_state", "hands_server_structure_to_state",
                                    "compares_only", "reads_and_leaves_it_unused",
                                    "never_reads_a_server_field")) != new_338["bodies"]:
        raise SystemExit("ABORT bw338's five buckets do not cover its own bodies")
    if new_338["hands_server_text_to_state"] != int(text_rows.group(1)):
        raise SystemExit("ABORT bw338's tally and its provenance line disagree about the text bucket")
    if new_327["says_zh"] != 26:
        raise SystemExit("ABORT the corrected sentence count moved off 26 again: it now reads %d, so the "
                         "correction block needs a second pass" % new_327["says_zh"])

    text = read("trial/results/20261026_GO_FROM_BLANK_REPORT.md")
    if "14.39 补" in text:
        return 4
    section = "\n".join([
        "",
        "### 14.39 补（10-30 零点）：第四处量具错（把注释里的 catch 当成 handler）＋「读到的字段到底去了哪」的三档尺",
        "",
        "- 第四处错：catch 的正则扫的是文本行，而 RecoveryRequiredPanel.tsx 的文件头注释里就写着一段 "
        "`catch { … }` 作为「以前怎么错的」的说明——它被当成了 handler。尺 trial/human_walk/_cmdr_screen_text_r325.py:%d "
        "现在先用状态机认块注释区间（`//` 早于 `/*` 的那一行不算开注释，字符串里的 URL 不受影响），三把共用这把"
        "切刀的尺（bw325/bw326/bw337）与全文 catch 跨度扫描一起接上。现读：本树 %d 个文件里 %d 枚 catch body，"
        "最短 %d 行、中位 %d 行、最长 %d 行（回执 trial/results/20261026_gozero/%s:%d 的 body 形状行）；挂载面板"
        "的分母 %d 处→%d 处（回执 trial/results/20261026_gozero/%s:%d 对同目录 %s 留底）。"
        % (at["ruler_325"], shape["files"], shape["bodies"], shape["shortest"], shape["median"],
           shape["longest"], BW325, at["revision"],
           old_326["catch"], new_326["catch"], BW326, at["tally_326"], KEPT),
        "- 这一处改口改的是次轴，不改主句：读到拒绝句 %d 处→%d 处、藏起来 %d 处→%d 处；面板自造中文句仍 %d 处、"
        "被标记读到仍 %d 处（回执 trial/results/20261026_gozero/%s:%d 与 trial/results/20261026_gozero/%s:%d），"
        "所以 #373 那格的「十九→廿六」"
        "照旧成立。次轴另动三处：只说英文 %d 处、交给 state %d 处、两头都不是 %d 处、带重试句形 %d 处（同一回执 :%d）。"
        "还要老实记一句：第一次修复与第二次修复之间该读数是否另有其值，已无工件可查（bw326 的回执被第二次修复"
        "覆盖），所以本节只报留底可证的 %d→%d，不拿中间态当证据。"
        % (old_326["reads_the_refusal"], new_326["reads_the_refusal"], old_326["hides_the_refusal"],
           new_326["hides_the_refusal"], new_327["says_zh"], new_328["rendered"], BW327, at["tally_327"], BW328, at["tally_328"],
           new_327["says_en_only"], new_327["into_state"], new_327["nowhere"], new_327["retry_shaped"],
           at["tally_327"], old_326["reads_the_refusal"], new_326["reads_the_refusal"]),
        "- 新尺 trial/human_walk/_cmdr_field_destination_r340.py:%d 答的是 §14.38 应下的那一问：读字段不等于把"
        "那句显出来。它把字段分文本（detail/message/quote/statusText）与结构（facts/envelope/body/code/status/"
        "data/errors）两组，认一次派生名（`const detail = body?.detail ?? …` 这种写法），再看 setter 的实参与"
        "比较行。现读 %d 枚 body：%d 处把文本交进 state、%d 处只交结构化事实、%d 处只拿去比对、%d 处读了不用、"
        "%d 处根本没读（回执 trial/results/20261026_gozero/%s:%d）。"
        % (at["ruler_340"], new_338["bodies"], new_338["hands_server_text_to_state"],
           new_338["hands_server_structure_to_state"], new_338["compares_only"],
           new_338["reads_and_leaves_it_unused"], new_338["never_reads_a_server_field"], BW338,
           at["tally_338"]),
        "- 判别力在三枚各自落不同档的控制上（回执 trial/results/20261026_gozero/%s:%d 起三行）：Destination"
        "PreparationPanel 那处判交文本、RealCityDiscoveryPanel 那处判只交结构（它的注释自己写明「匹配的是机器码、"
        "丢的是句子」）、LiveRecovery 那处 `} catch {` 无绑定判没读。三枚中任一落进源码不认可的档，尺就 ABORT。"
        % (BW338, at["controls_338"]),
        "- 顺出来的一条新缺陷面（不是文案面）：那 %d 处交进 state 的 `error.message` 追到了出处——四处的 try 里"
        "点的都是 cityNexusApi 的调用（现读 %d/%d），而 api 层在 %s:%d 抛错时把 message 拼成 "
        "`\"CityNexus API \" + response.status + \": \" + path`。所以旅客在这四格里看到的是本机拼装串（带状态码"
        "与路径），既不是服务端的拒绝句，也不是一句能看懂的话。「屏上有英文」这件事，在这 %d 枚面板 handler 里"
        "现读为 %d 处，而那 %d 处显的是内部诊断——这一格是第四档，不在 §14.32 的三档里，请一并点。"
        % (new_338["hands_server_text_to_state"], int(text_rows.group(2)), int(text_rows.group(1)),
           throw.group(1), int(throw.group(2)), new_338["bodies"], new_338["hands_server_text_to_state"],
           new_338["hands_server_text_to_state"]),
        "- 这把尺不能说的那句：provenance 只证明该 catch 的 try 文本里出现了 api 层的调用名，不证明那次 message "
        "一定由 api 层那行拼装而来（同一个 try 里若有本地 throw，就会走别的路径）；要钉死得真按一次把这四格逼到"
        "屏上，本尺不替它做。它也不看 JSX 插值（归 bw328）、不追跨组件的 prop。全程 0 改产品字节、0 点击。",
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
        "",
    ])
    with io.open(REPORT, "rb") as handle:
        blob = handle.read()
    crlf = blob.count(b"\r\n")
    bare = blob.count(b"\n") - crlf
    if not blob.endswith(b"\r\n"):
        blob += b"\r\n"
    lines = section.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    payload = b"\r\n".join(cell.encode("utf-8") for cell in lines) + b"\r\n"
    io.open(REPORT, "wb").write(blob + payload)
    back = io.open(REPORT, "rb").read()
    hits = back.count("14.39 补".encode("utf-8"))
    crlf_after = back.count(b"\r\n")
    bare_after = back.count(b"\n") - crlf_after
    print("APPENDED bytes_added=%d section_lines=%d heading_hits=%d crlf_now=%d bare_lf_now=%d"
          % (len(payload), len(lines), hits, crlf_after, bare_after))
    if hits != 1:
        raise SystemExit("ABORT the heading is not unique")
    if crlf_after != crlf + len(lines) or bare_after != bare:
        raise SystemExit("ABORT the line endings moved: added %d CRLF and %d bare LF"
                         % (crlf_after - crlf, bare_after - bare))
    return 0


if __name__ == "__main__":
    sys.exit(main())
