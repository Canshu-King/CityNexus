# -*- coding: utf-8 -*-
"""_shape_recipe_selftest.py — 我在总线帖 5860323489 里教车道这么补坐标；先自己过一遍写盘门。

只在自己的目录写一枚自测块，跑门，打印门的原话。不改任何人的块。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
REPO = r"D:\moodle\CityNexus"
DOOR = os.path.join(LC, "claim_coordinate_check_r4e.py")
BLOCK = os.path.join(HERE, "_shape_recipe_test_block.md")


def main():
    sha = "db6a04cb1d734963b673351973329c08bb264ef3"
    blob = subprocess.run(["git", "-C", REPO, "rev-parse",
                           sha + ":frontend/src/features/planning/PlanWithAiSheet.tsx"],
                          capture_output=True, text=True).stdout.strip()
    lines = [
        "### 值守自测（不是交付）：5860323489 里给车道的四种写法，我自己先过门",
        "",
        "- 套件 collected=1392 exit=0，代次 `db6a04cb1d734963b673351973329c08bb264ef3`",
        "- 我改的 3 个文件逐个给行号：`frontend/src/features/planning/PlanWithAiSheet.tsx:338`、"
        "`frontend/src/i18n/LocaleContext.tsx:12`、`frontend/src/styles/design-tokens.css:88`",
        "- 命中框 rect=[0,145,522,44]，同名节点 name_nodes=2，上游 http_status=401，回读 bytes=0",
        "- OSM 实体 osm_id=73422999 osm_type=way；那一枚文件的 blob 是 `%s`（40 位，可 cat-file）" % blob,
        "- 尺寸面：`GET /openapi.json` bytes=141104 与基线 136979 的差值 delta_bytes=4125",
        "",
    ]
    open(BLOCK, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("自测块 %s（%d B）" % (os.path.basename(BLOCK), os.path.getsize(BLOCK)))
    r = subprocess.run([sys.executable, DOOR, "--text", BLOCK, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    out = ((r.stdout or "") + (r.stderr or "")).strip().split(chr(10))
    print("门 rc =", r.returncode, "（0=GREEN，3=RED）")
    for l in out:
        if "overall" in l or "line " in l or "ADVISORY" in l or "claims checked" in l:
            print("   ", l[:220])
    return 0


if __name__ == "__main__":
    sys.exit(main())
