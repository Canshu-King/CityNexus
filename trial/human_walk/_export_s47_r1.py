import pathlib

path = pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md")
text = path.read_text(encoding="utf-8")
marker = "## 47."
index = text.index(marker)
if text.count(marker) != 1:
    raise SystemExit(f"ABORT marker count={text.count(marker)}")
pathlib.Path(r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/_s47_restore.md").write_text(
    text[index:], encoding="utf-8", newline="\n"
)
print("FRAG_CHARS", len(text[index:]), "PREFIX_CHARS", index)
