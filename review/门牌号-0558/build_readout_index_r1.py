"""门牌号 ORD-0558 读数件跑批：把交块里每一条"命令原样"当场跑一遍，stdout 原样落 readout_index_r1.txt。

只跑只读命令（ls-remote / cat-file / rev-list / diff / 打包探针），不改任何字节；每条前面先写一行 `#CMD <命令原样>`，
所以读数与命令逐行配对，交块引用行号时是现读的。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

TREE = Path("D:/moodle/_qoder_menpaaihao_0558")
OUT = Path("D:/moodle/_menph_0558_readout_index_r1.txt")
ESBUILD = "D:/moodle/CityNexus/frontend/node_modules/esbuild/bin/esbuild"
TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"
BRANCH_REF = "refs/heads/review/门牌号-0558-r1"
REPO = "D:/moodle/CityNexus"
PRODUCT = "frontend/src/features/pending/pendingSetCopy.ts"

lines: list[str] = []


def run(label: str, args: list[str], cwd: Path) -> None:
    lines.append(f"#CMD {label}")
    done = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = (done.stdout or "") + (done.stderr or "")
    for one in body.rstrip("\n").split("\n"):
        lines.append(one)
    lines.append(f"#RC {done.returncode}")


run(
    f"git -C {REPO} ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1",
    ["git", "-C", REPO, "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
    TREE,
)
run(f"git -C {REPO} cat-file -t {TIP}", ["git", "-C", REPO, "cat-file", "-t", TIP], TREE)
run(f"git rev-parse HEAD", ["git", "rev-parse", "HEAD"], TREE)
run(f"git ls-remote origin {BRANCH_REF}", ["git", "ls-remote", "origin", BRANCH_REF], TREE)
run(f"git cat-file -t $(git rev-parse HEAD)", ["git", "cat-file", "-t", TIP[:0] or "HEAD"], TREE)
run(
    f"git rev-list --count {TIP}..HEAD",
    ["git", "rev-list", "--count", f"{TIP}..HEAD"],
    TREE,
)
run(
    f"git rev-list --count HEAD..{TIP}",
    ["git", "rev-list", "--count", f"HEAD..{TIP}"],
    TREE,
)
run(
    f"git -c core.quotepath=off diff --name-status {TIP} HEAD -- frontend",
    ["git", "-c", "core.quotepath=off", "diff", "--name-status", TIP, "HEAD", "--", "frontend"],
    TREE,
)
run(
    f"git -c core.quotepath=off diff --numstat {TIP} HEAD",
    ["git", "-c", "core.quotepath=off", "diff", "--numstat", TIP, "HEAD"],
    TREE,
)
run(
    f"git rev-parse HEAD:{PRODUCT}",
    ["git", "rev-parse", f"HEAD:{PRODUCT}"],
    TREE,
)
run(
    f"git rev-parse {TIP}:{PRODUCT}",
    ["git", "rev-parse", f"{TIP}:{PRODUCT}"],
    TREE,
)
run(f"git cat-file -t HEAD 的该文件 blob", ["git", "cat-file", "-t", f"HEAD:{PRODUCT}"], TREE)
run(
    f"node {ESBUILD} review/门牌号-0558/probe_0558_r1.ts --bundle --platform=node --format=cjs --outfile=_probe_rezip.cjs",
    ["node", ESBUILD, "review/门牌号-0558/probe_0558_r1.ts", "--bundle", "--platform=node",
     "--format=cjs", "--outfile=_probe_rezip.cjs"],
    TREE,
)
run("node _probe_rezip.cjs 的头两行之后即删", ["node", "_probe_rezip.cjs"], TREE)
lines.append("#NOTE push 当时 stdout 里那行 new branch 是从那次 push 的原始输出复述（已落本次会话流水），重跑 push 不会再现它")
lines.append("#NOTE 本件只跑只读命令；改字节的腿在 apply_0558_r1.py，两语读数在 probe_before_r1.txt 与 probe_after_r1.txt")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {OUT} lines={len(lines)}")
