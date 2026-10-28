"""Reword the certificate: the run log is gitignored, so the certificate must not cite it as a retrievable file.

Found while staging: the repository's .gitignore excludes *.log, which means the line
"日志 <path>.log" pointed a reader at a file that only exists on this machine.  The digest (.txt, tracked)
and the verbatim summary line inside this certificate are the retrievable parts, so the wording says so.

Bash eats backticks inside double quotes -- that is why this is a file and not a -c one-liner.
"""
import io

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261029_BACKEND_CERTIFICATE_24a342198d.md"
text = io.open(PATH, encoding="utf-8", newline="").read()
old = "Windows 11，日志 `trial/results/20261026_gozero/bt143-backend-full-24a342198d.log`。"
new = ("Windows 11。原始日志在本机 `trial/results/20261026_gozero/bt143-backend-full-24a342198d.log`，"
       "但仓库的 .gitignore 排除 `*.log`、它不入库 —— 所以能取回的两件是本证书里逐字抄下的末行，"
       "与入库的分组摘要 `trial/results/20261026_gozero/bt143-backend-digest.txt`。")
if text.count(old) != 1:
    raise SystemExit("ABORT the sentence to reword is not uniquely present: %d" % text.count(old))
io.open(PATH, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
back = io.open(PATH, encoding="utf-8").read()
print("REWORDED", "不入库" in back, "OLD_GONE", old not in back)
print("BYTES", len(back.encode("utf-8")))
