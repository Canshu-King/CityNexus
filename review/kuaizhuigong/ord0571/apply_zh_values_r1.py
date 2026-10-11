"""ORD-0571 kuaizhuigong: fill in the 22 Chinese-side values that were left as English sentences.

The door is in this file: nothing is written unless every row matches the line number, the key name
and the current value byte for byte, and unless the placeholder set of the new Chinese value equals
the English side. One bad row aborts the whole batch, so a half-applied dictionary never exists.
"""

import re
import sys

PATH = "frontend/src/i18n/LocaleContext.tsx"

# key, line on the current tip, value read there now, the Chinese value to put in
ROWS = [
    ("main.cityNexusRequestFailed", 2315, "CityNexus request failed", "CityNexus 请求失败"),
    ("main.cityNexusRequestRefusedHttp", 2316, "CityNexus request refused (HTTP {status})",
     "CityNexus 请求被拒绝（HTTP {status}）"),
    ("main.persistedOperationUpdate", 2317, "Persisted operation update", "已持久化的操作更新"),
    ("main.generalRecovery", 2318, "general recovery", "通用恢复"),
    ("main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage",
     2319,
     "Activate a standing mission once; subsequent city signals can launch recovery without a new chat message.",
     "激活一次常驻任务；之后的城市信号无需新的聊天消息即可发起恢复。"),
    ("main.noDominantFailureMode", 2320, "No dominant failure mode", "没有主导的失败模式"),
    ("main.notEvaluated", 2321, "not evaluated", "未评估"),
    ("main.validatedActivity", 2322, "validated Activity", "通过校验的活动"),
    ("main.noActionableTarget", 2323, "no actionable target", "没有可行动的目标"),
    ("main.outcomeEvidence", 2324, "outcome evidence", "结果证据"),
    ("main.explicitWins", 2325, "explicit wins", "显式胜出项"),
    ("main.notReported", 2326, "not reported", "未上报"),
    ("main.noUpcomingActivity", 2327, "no upcoming activity", "接下来没有活动"),
    ("main.noActiveC4", 2328, "No active C4", "当前没有生效的 C4"),
    ("main.notAvailable", 2329, "not available", "不可用"),
    ("main.verifiedFeasible", 2330, "verified feasible", "已验证可行"),
    ("main.notFeasible", 2331, "not feasible", "不可行"),
    ("main.notPreserved", 2332, "not preserved", "未被保留"),
    ("main.verifiedEvidenceAttached", 2333, "verified evidence attached", "已附带已验证证据"),
    ("main.evidenceUnavailable", 2334, "evidence unavailable", "证据不可用"),
    ("recovery.noDominantMode", 1800, "no dominant mode", "没有主导模式"),
    ("recovery.noneOnThisJourney", 1801, "none on this journey", "这趟行程上没有"),
]

PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")

raw = open(PATH, "rb").read()
if b"\r\n" in raw:
    print("ABORT: this file is not LF as expected, refusing to rewrite it")
    sys.exit(1)
lines = raw.decode("utf-8").split("\n")
before_count = len(lines)

errors = []
plan = {}

for key, line_no, old_val, new_val in ROWS:
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        errors.append(f"{key}: line {line_no} is out of range")
        continue
    current = lines[idx]
    expect = f'  "{key}": "{old_val}",'
    if current != expect:
        errors.append(f"{key} line {line_no}: expected {expect!r} found {current!r}")
        continue
    # the Chinese side must not lose or invent a placeholder slot
    en_slots = sorted(PLACEHOLDER.findall(old_val))
    zh_slots = sorted(PLACEHOLDER.findall(new_val))
    if en_slots != zh_slots:
        errors.append(f"{key}: placeholder drift {en_slots} vs {zh_slots}")
        continue
    if not re.search(r"[一-鿿]", new_val):
        errors.append(f"{key}: new value carries no Chinese character")
        continue
    plan[idx] = f'  "{key}": "{new_val}",'

if errors or len(plan) != len(ROWS):
    print(f"rows_in_order={len(ROWS)} matched={len(plan)} refused={len(errors)}")
    for e in errors:
        print("REFUSED " + e)
    print("VERDICT=ABORT nothing was written")
    sys.exit(1)

for idx, text in plan.items():
    lines[idx] = text

after = "\n".join(lines)
open(PATH, "wb").write(after.encode("utf-8"))

# read back from disk, independent of the plan above
check = open(PATH, "rb").read().decode("utf-8").split("\n")
if len(check) != before_count:
    print(f"VERDICT=ABORT line count moved {before_count} -> {len(check)}")
    sys.exit(1)

bad = []
for key, line_no, old_val, new_val in ROWS:
    want = f'  "{key}": "{new_val}",'
    if check[line_no - 1] != want:
        bad.append(f"{key} line {line_no} did not read back as written: {check[line_no-1]!r}")
print(f"rows_in_order={len(ROWS)} written={len(plan)} readback_bad={len(bad)} lines={len(check)}")
for b in bad:
    print("BAD " + b)
if bad:
    print("VERDICT=ABORT read-back failed")
    sys.exit(1)
print("VERDICT=PASS all 22 Chinese-side values written and read back, placeholders preserved")
