"""Regression arm: CnxMeasuredFacts stops hand-writing copy the dictionary ALREADY owns.

The defect is a second source of truth, not a missing translation: at the parent bytes
every one of the eight sentences this component hand-wrote already existed as a
`detail.*` key in LocaleContext.tsx (both arms). So this change adds ZERO dictionary
keys, and the arm's centre of gravity is:

  (a) the component now reads the keys, and
  (b) LocaleContext.tsx is byte-identical to the parent (proving no new key was minted), and
  (c) the rendered text is unchanged, proven by comparing each arm's dictionary value
      against the string the component used to hand-write (both taken from the parent bytes).

Q70/Q71 load-bearing shapes are asserted too: the `data-cnx-field` anchors and the fold's
`open` attribute must survive, because the fold hiding that line is X-5's defect.

MUTUALLY_EXCLUSIVE_VARIANT: 撤掉改动（恢复到父字节）⇒ 本臂必须红。
父字节从 git 对象直接取（`git show <parent>:<path>`），所以对照不依赖任何工作树状态。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

COMPONENT_REL = "frontend/src/components/CnxMeasuredFacts.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
PARENT = "cf5915ea948579b4dc80aa57a299639b5440150e"

# (key, the en string the component used to hand-write, the zh string it used to hand-write)
CONVERGED = [
    ("detail.measuredHttpLabel", "This device's reading: HTTP", "这台设备看到的回读：HTTP"),
    ("detail.measuredContentType", "Media type read back", "回读的媒体类型"),
    ("detail.measuredBytes", "Octets this device counted", "这台设备数到的字节"),
    ("detail.receiptFoldSummary",
     "What this device read back, and the server's receipt", "这台设备量到的回读与服务器回执号"),
    ("detail.receiptHttpNone", "This device's reading: HTTP measured none",
     "这台设备看到的回读：HTTP 没量到"),
    ("detail.receiptLabel", "server receipt", "服务器回执号"),
    ("detail.receiptLabelAbsent", "no server receipt", "服务器未给回执号"),
]
INTERPOLATED = ("detail.measuredNoneSuffix", "{label}: this device measured none",
                "{label}：这台设备没量到")


def git_show(rel: str, rev: str = PARENT) -> str:
    out = subprocess.run(
        ["git", "show", f"{rev}:{rel}"],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit("cannot read parent bytes: " + rel)
    return out.stdout.decode("utf-8")


def dict_value(d: str, key: str, want: str) -> bool:
    return re.search(r'^\s*"%s":\s*"%s",?$' % (re.escape(key), re.escape(want)), d, re.M) is not None


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    comp = (root / COMPONENT_REL).read_text(encoding="utf-8")
    d = (root / DICT_REL).read_text(encoding="utf-8")
    parent_comp = git_show(COMPONENT_REL)
    parent_dict = git_show(DICT_REL)

    checks: list[tuple[str, bool]] = []
    def ck(name: str, ok: bool) -> None:
        checks.append((name, bool(ok)))

    # (a) the component reads the keys
    for key, _en, _zh in CONVERGED:
        ck(f"组件读 {key}", f't("{key}")' in comp)
    ck("组件读插值那枚 measuredNoneSuffix", 't("detail.measuredNoneSuffix"' in comp)
    ck("组件里已无手写的 这台设备看到的回读", "这台设备看到的回读" not in comp)
    ck("组件里已无手写的 服务器回执号", "服务器回执号" not in comp)

    # (b) zero new dictionary keys: dict is byte-identical to parent
    ck("词典字节与父笔逐字相同（零枚新键）", d == parent_dict)

    # (c) rendered text unchanged: dict values equal the strings parent hand-wrote
    for key, en, zh in CONVERGED:
        ck(f"{key} 两臂值等于父笔手写那两串",
           dict_value(parent_dict, key, en) and dict_value(parent_dict, key, zh))
    ikey, ien, izh = INTERPOLATED
    ck("插值键两臂值等于父笔手写那两串",
       dict_value(parent_dict, ikey, ien) and dict_value(parent_dict, ikey, izh))
    ck("父笔组件确实手写过这些串（对照非空）", "这台设备看到的回读：HTTP" in parent_comp)

    # load-bearing shapes survive
    ck("data-cnx-field 锚位数量不变",
       comp.count('"data-cnx-field"') == parent_comp.count('"data-cnx-field"'))
    ck("data-cnx-value 锚位数量不变",
       comp.count('"data-cnx-value"') == parent_comp.count('"data-cnx-value"'))
    ck("回执折仍默认 open（折叠藏行是 X-5 的缺陷）",
       re.search(r'receipt-fold`[^>]*open', comp) is not None)
    ck("组件仍接 zh 这枚入参（调用点零改动）", re.search(r"\bzh:\s*boolean", comp) is not None)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(f"total={len(checks)} failed={len(failed)}")
    if failed:
        print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
        return 1
    print("VERDICT: MUTUALLY_EXCLUSIVE_VARIANT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
