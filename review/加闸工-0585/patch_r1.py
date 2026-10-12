# -*- coding: utf-8 -*-
"""ORD-0585 lane patch: the three traveller-visible literals in retryHint go to both dictionary arms.

Every replacement is asserted to match exactly once; the files stay LF (newline='' on read and write).
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WT = "D:/moodle/_jz_0585/wt/"
ADAPTER = WT + "frontend/src/features/simulation/simulationAdapter.ts"
DICT = WT + "frontend/src/i18n/LocaleContext.tsx"

EDITS = [
    (ADAPTER,
     'import { dictionaryCopy } from "../../i18n/LocaleContext";',
     'import { dictionaryCopy, dictionaryText, type TripLocale } from "../../i18n/LocaleContext";'),
    (ADAPTER,
     'function retryHint(error: unknown): string {\n'
     '  const details = (bodyOf(error)?.error?.details ?? {}) as { retry_after_ms?: unknown };\n'
     '  const ms = typeof details.retry_after_ms === "number" ? details.retry_after_ms : null;\n'
     '  if (ms === null) return "（服务器没说要等多久）";\n'
     '  return ms <= 0 ? "（现在就可以再试）" : `（约 ${Math.round(ms)} 毫秒后再试）`;\n'
     '}',
     'function retryHint(error: unknown, locale: TripLocale): string {\n'
     '  const details = (bodyOf(error)?.error?.details ?? {}) as { retry_after_ms?: unknown };\n'
     '  const ms = typeof details.retry_after_ms === "number" ? details.retry_after_ms : null;\n'
     '  if (ms === null) return dictionaryCopy(locale, "simulation.retryWaitNotGiven");\n'
     '  if (ms <= 0) return dictionaryCopy(locale, "simulation.retryRightNow");\n'
     '  return dictionaryText(locale, "simulation.retryInMs", { ms: Math.round(ms) });\n'
     '}'),
    (ADAPTER,
     '    const extra = busy ? retryHint(error) : fields;\n'
     '    return { code, status, zh: hit.zh(status, extra), en: hit.en(status, extra) };',
     '    const zhExtra = busy ? retryHint(error, "zh-CN") : fields;\n'
     '    const enExtra = busy ? retryHint(error, "en") : fields;\n'
     '    return { code, status, zh: hit.zh(status, zhExtra), en: hit.en(status, enExtra) };'),
    (DICT,
     '  "simulation.notGiven": "not given",',
     '  "simulation.notGiven": "not given",\n'
     '  /* ORD-0585: the store-busy wait hint. The Chinese screen already read these three bytes; the\n'
     '     English arm used to receive the same Chinese sentence because retryHint() had no language of\n'
     '     its own, so the English arms are the new half and the Chinese arms are a verbatim move. */\n'
     '  "simulation.retryWaitNotGiven": " (the server did not say how long to wait)",\n'
     '  "simulation.retryRightNow": " (you can try again right now)",\n'
     '  "simulation.retryInMs": " (try again in about {ms} ms)",'),
    (DICT,
     '  "simulation.notGiven": "服务器未给证据状态",',
     '  "simulation.notGiven": "服务器未给证据状态",\n'
     '  "simulation.retryWaitNotGiven": "（服务器没说要等多久）",\n'
     '  "simulation.retryRightNow": "（现在就可以再试）",\n'
     '  "simulation.retryInMs": "（约 {ms} 毫秒后再试）",'),
]

by_file = {}
for path, old, new in EDITS:
    if path not in by_file:
        by_file[path] = io.open(path, "r", encoding="utf-8", newline="").read()
    src = by_file[path]
    n = src.count(old)
    if n != 1:
        print("ABORT %s :: snippet matches %d times, not 1\n%s" % (path, n, old[:120]))
        raise SystemExit(1)
    by_file[path] = src.replace(old, new, 1)
    print("OK  %s <- %s…" % (path.split("/")[-1], old[:60].replace("\n", "\\n")))

for path, src in by_file.items():
    io.open(path, "w", encoding="utf-8", newline="").write(src)
    print("WROTE %s  %d B  LF=%d CRLF=%d" % (path, len(src.encode("utf-8")), src.count("\n"), src.count("\r\n")))
