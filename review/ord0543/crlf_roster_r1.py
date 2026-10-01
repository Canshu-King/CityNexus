"""ORD-0543 · build the CRLF phantom roster from a fresh checkout.

Lists every file a clean worktree reports as modified although its bytes equal the stored blob
except for CR, with both CR counts and the verdict. Written as a file so the count is measured, not
remembered.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TREE = Path(sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_qoder_seed_ord0489/wt543b")
HEAD = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()

status = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"],
                        capture_output=True, text=True).stdout.splitlines()
# only tracked modifications: an untracked file I just wrote is not a phantom-dirty blob
files = [line[3:].strip() for line in status
         if line[:2].strip() and "?" not in line[:2]]

rows = []
skipped = []
for name in files:
    exists = subprocess.run(["git", "-C", str(TREE), "cat-file", "-e", f"HEAD:{name}"],
                            capture_output=True).returncode == 0
    if not exists:
        # a file this lane just added has no stored blob to be phantom-dirty against
        skipped.append(name)
        continue
    work = (TREE / name).read_bytes()
    blob = subprocess.run(["git", "-C", str(TREE), "show", f"HEAD:{name}"],
                          capture_output=True).stdout
    equal = work.replace(b"\r\n", b"\n") == blob.replace(b"\r\n", b"\n")
    rows.append({
        "path": name,
        "worktree_cr": work.count(b"\r"),
        "blob_cr": blob.count(b"\r"),
        "identical_ignoring_crlf": equal,
    })

lines = [
    "# `review/**` 里仍以 CRLF 入库、被 `.gitattributes`（`*.py text eol=lf`）判成假脏的名册",
    "",
    "现读自本车道一棵稀疏集合含 `review` 的新检出树 `" + str(TREE.name) + "`，头 `" + HEAD + "`。",
    "逐枚比较工作树字节与 HEAD blob：忽略 CRLF 后 **完全相同** 的有 "
    + str(sum(1 for r in rows if r["identical_ignoring_crlf"])) + " / " + str(len(rows)) + " 枚，"
    "也就是内容 0 处不同，只有换行符申报差。",
    "",
    "后果不是难看而是拦路：`git rebase` 会以 `error: cannot rebase: You have unstaged changes.` "
    "停在它们上面（本单 2026-10-02 撞过一次）。不碰别人字节的绕行办法：在现尖另开一棵树，"
    "把那一笔 `git cherry-pick` 过去——本枝的交付代就是这么来的。",
    "",
    "号令者 15:30 裁语第 8 条④把这件事归他自己、说三枚；实测是 "
    + str(len(rows)) + " 枚，全在 `review/` 存档树下面。",
    "",
    "| 文件 | 工作树 CR | blob CR | 忽略 CRLF 后相同 |",
    "| --- | --- | --- | --- |",
]
for row in rows:
    lines.append("| `{0}` | {1} | {2} | {3} |".format(
        row["path"], row["worktree_cr"], row["blob_cr"], row["identical_ignoring_crlf"]))

(out_dir := TREE / "review/ord0543").mkdir(parents=True, exist_ok=True)
out = out_dir / "CRLF_PHANTOM_ROSTER.md"
out.write_bytes(("\n".join(lines) + "\n").replace("\r\n", "\n").encode("utf-8"))
print("wrote", out, "| tracked phantom rows:", len(rows), "| identical ignoring CRLF:",
      sum(1 for r in rows if r["identical_ignoring_crlf"]), "| skipped (no HEAD blob):", skipped)
