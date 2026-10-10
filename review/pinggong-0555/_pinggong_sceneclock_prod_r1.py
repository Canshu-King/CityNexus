import io, sys

P = r"D:/moodle/_qoder_pinggong_0555/frontend/src/lib/sceneClock.ts"
s = io.open(P, encoding="utf-8").read()

OLD = '''export function basisWord(basis: string | null, zh: boolean): string {
  if (basis === "CURSOR") return zh ? "执行游标" : "the execution cursor";
  if (basis === "JOURNEY_START") return zh ? "行程起点" : "the journey's start";
  return zh ? "服务器没有说明依据" : "the server gave no basis";
}'''
NEW = '''export function basisWord(basis: string | null, zh: boolean): string {
  const copy = (key: string) => dictionaryCopy(zh ? "zh-CN" : "en", key);
  if (basis === "CURSOR") return copy("sceneClock.executionCursor");
  if (basis === "JOURNEY_START") return copy("sceneClock.journeyStart");
  return copy("sceneClock.serverGaveNoBasis");
}'''

IMP_OLD = 'import { useQuery, type QueryClient } from "@tanstack/react-query";'
IMP_NEW = IMP_OLD + '\nimport { dictionaryCopy } from "../i18n/LocaleContext";'

for old, new in ((OLD, NEW), (IMP_OLD, IMP_NEW)):
    if s.count(old) != 1:
        sys.exit("ABORT needle hits=%d for %r" % (s.count(old), old[:40]))
    s = s.replace(old, new, 1)
    print("ok", old.split("\n")[0][:46])

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("PRODUCT_ROWS_ROUTED=3")
