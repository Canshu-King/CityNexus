"""ORD-0417 hub 那格：把「回到行程视野」控件的盒子量给相机 —— 改与退都只有这一处脚本做。

两种模式，同一把锚：

  apply    在 `MapPanel.tsx` 的底部叠层测量之后加一次顶部控件测量，并把 `top` 从裸侧边距改成
           `side + controlsHeight + safetyGap`；两处锚都必须在文件里恰好命中一次，命中数不对就
           REFUSE（ORD-0477 那一手就是因为锚悄悄不再命中，反件打印"No matches found"而套件仍绿）。
  revert   现尖那副字节原样写回（单变量反件用的就是这一形：只退顶部这笔预留，别的都不动）。

每次动作都按 sha256 记账：改前/改后/还原后三枚哈希，"还原"是文件的事实而不是意图的说法。

usage: python ord0417_top_reservation_r1.py <apply|revert> [--tree DIR]
"""
import argparse
import hashlib
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
TIP = "refs/tmp/line_now"
REL = "frontend/src/components/v8/MapPanel.tsx"

# 锚一：底部那叠量完之后紧接的两行常量声明。用它把控件测量插在中间。
ANCHOR_A = """      const overlayHeight = overlay?.getBoundingClientRect().height ?? 0;
      const side = 42;
      const safetyGap = 16;
""".replace("\n", chr(10))
REPLACEMENT_A = """      const overlayHeight = overlay?.getBoundingClientRect().height ?? 0;
      /* The named control is absolute over the top edge of the same panel
         (`map-controls.css`, `.v8-map-viewport-controls`), so at a narrow shape its box sits on top
         of the whole pin cluster: the hub gate's per-pair hit test read nine pin centres in a row
         landing on that control's glyph, which means neither the pin nor its name could be tapped.
         The camera is told about the bottom stack the same way already; telling it about this box
         is that one rule applied to the other edge, not a second reservation list. */
      const controls = host.current?.parentElement?.querySelector(
        ".v8-map-viewport-controls",
      ) as HTMLElement | null;
      const controlsHeight = controls?.getBoundingClientRect().height ?? 0;
      const side = 42;
      const safetyGap = 16;
""".replace("\n", chr(10))

ANCHOR_B = """          padding: {
            top: side,
""".replace("\n", chr(10))
REPLACEMENT_B = """          padding: {
            top: side + controlsHeight + safetyGap,
""".replace("\n", chr(10))
# The lean variant reserves the control's own box and nothing more: the extra `safetyGap` is what
# variant A paid for its green hub arm with -- on the same tree it reddened two arms of the accepted
# ORD-0512 glass gate, because the band lost more height than crowding can live with.
REPLACEMENT_B_LEAN = """          padding: {
            top: side + controlsHeight,
""".replace("\n", chr(10))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tip_bytes() -> bytes:
    return subprocess.run(["git", "-C", REPO, "show", f"{TIP}:{REL}"], capture_output=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("apply", "apply_lean", "revert"))
    ap.add_argument("--tree", default=r"D:/moodle/_qoder_b_ord0417_20260928/hubcut")
    args = ap.parse_args()
    path = pathlib.Path(args.tree) / REL
    before = path.read_bytes()
    if args.mode == "revert":
        path.write_bytes(tip_bytes())
        print("mode=revert before=%s after=%s equals_tip=%s" % (
            digest(before)[:16], digest(path.read_bytes())[:16],
            digest(path.read_bytes()) == digest(tip_bytes())))
        return 0
    text = before.decode("utf-8")
    if digest(before) == digest(tip_bytes()):
        state = "from_tip_bytes"
    else:
        state = "from_already_patched_bytes"
    top_replacement = REPLACEMENT_B_LEAN if args.mode == "apply_lean" else REPLACEMENT_B
    for anchor, replacement in ((ANCHOR_A, REPLACEMENT_A), (ANCHOR_B, top_replacement)):
        hits = text.count(anchor)
        if hits != 1:
            print("REFUSE: anchor hits=%d (must be exactly 1): %r" % (hits, anchor[:70]))
            return 2
        text = text.replace(anchor, replacement)
    path.write_text(text, encoding="utf-8", newline="")
    after = path.read_bytes()
    print("mode=apply state=%s before=%s after=%s bytes=%d->%d" % (
        state, digest(before)[:16], digest(after)[:16], len(before), len(after)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
