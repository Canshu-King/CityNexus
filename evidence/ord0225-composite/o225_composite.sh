#!/usr/bin/env bash
# ORD-0225 续 · (iii) composite 树的**可推送**构造器（lane F，2026-09-23 03:0x）
#
# 仲裁选的形状：**产品候选保持干净；尺作为显式依赖；真正跑 closure 的那棵树有自己的 SHA。**
# 压轴那句（要求写进交接与收据）：
#   "closure 跑在具名、可推送、可审的 composite commit；跑绿属于 composite，不属于 mainline。
#    主线想要 GREEN，就拿主线自己的 exact SHA 再跑。"
#
# 本脚本只做一件事：把 <产品 SHA> 的树 + 尺（从我的分支头取）**组一枚新提交**，落在
# 我自己仓的一个具名 ref 上（`composite/<产品>-<尺前缀>`），因此它可推送、可被任何人复查。
# 不碰任何人的工作树：只用 git 管道（read-tree / update-index --cacheinfo / write-tree /
# commit-tree），从不 checkout、从不写工作区。
#
# 退出码：
#   0   composite 建好、且四条自证全过（下面 [check] 那四行）
#   30  缺入参（产品 SHA 或尺来源）
#   31  产品 SHA 解析不到（幽灵提交不做 composite）
#   32  产品树里**已经有尺** ⇒ 那就不叫 composite，去跑产品 SHA 自己（别造重影）
#   33  composite 建不出来（git 管道任何一步失败）
#   34  自证失败：diff 不只有尺 / 树里没有尺 / ref 不是合法 SHA / 尺字节与来源不一致
set -uo pipefail

PRODUCT="${CNX_PRODUCT_SHA:-}"
RULER_REPO="${CNX_RULER_SOURCE_REPO:-/d/moodle/_qoder_f_o210b_20260922}"
RULER_REF="${CNX_RULER_REF:-HEAD}"
RULER_PATH="backend/tests/_qoder_streak_receipt.py"
OUT_REPO="${CNX_COMPOSITE_REPO:-$RULER_REPO}"      # composite 落在尺所在那枚仓（lane F 自己的仓）
RUNDIR=/d/moodle/_qoder_f_run

say() { printf '[o225-composite] %s\n' "$*" >&2; }
die() { say "$1"; exit "$2"; }

[ -n "$PRODUCT" ] || die "缺 CNX_PRODUCT_SHA：composite = 产品候选 + 尺，两者都得具名" 30
git -C "$OUT_REPO" cat-file -e "${PRODUCT}^{commit}" 2>/dev/null \
  || die "产品 SHA $PRODUCT 在 $OUT_REPO 里解析不到 ⇒ 不给幽灵提交造 composite" 31
if git -C "$OUT_REPO" cat-file -e "${PRODUCT}:${RULER_PATH}" 2>/dev/null; then
  die "产品树里已经有 ${RULER_PATH} ⇒ 不需要 composite，直接对被测 SHA 跑 closure（重影只会让归因更难）" 32
fi

RULER_HEAD=$(git -C "$RULER_REPO" rev-parse --short=7 "$RULER_REF" 2>/dev/null) \
  || die "尺来源 $RULER_REPO@$RULER_REF 解析不到" 31
RULER_BLOB=$(git -C "$RULER_REPO" rev-parse "${RULER_REF}:${RULER_PATH}" 2>/dev/null) \
  || die "尺不在 $RULER_REPO@$RULER_HEAD 的树里 ⇒ 尺自己得先落到某个提交上" 33
git -C "$OUT_REPO" cat-file -e "$RULER_BLOB" 2>/dev/null || {
  say "尺的 blob 不在目标仓的对象库里 ⇒ 先本地 fetch 过来（只读对端，不写任何东西）"
  git -C "$OUT_REPO" fetch -q "$RULER_REPO" "$RULER_REF" || die "fetch 尺失败" 33
  git -C "$OUT_REPO" cat-file -e "$RULER_BLOB" || die "fetch 完仍取不到尺 blob" 34
}

# ---- composite 树 = 产品树 + 尺一个路径（**全部走临时索引**，绝不含真实 .git/index）----
IDX="$RUNDIR/.o225_idx_$$"        # 只取路径，不创建 0 字节文件（git 会拒读空索引）
rm -f "$IDX"; export GIT_INDEX_FILE="$IDX"
TREE=""
if git -C "$OUT_REPO" read-tree "$PRODUCT" 2>/dev/null \
   && git -C "$OUT_REPO" update-index --add --cacheinfo 100644,"$RULER_BLOB","$RULER_PATH" 2>/dev/null; then
  TREE=$(git -C "$OUT_REPO" write-tree 2>/dev/null)
fi
unset GIT_INDEX_FILE; rm -f "$IDX"
[ -n "$TREE" ] || die "write-tree 没出东西 ⇒ 管道某一步失败（不猜哪一步，直接拒）" 33

COMPOSITE=$(git -C "$OUT_REPO" commit-tree "$TREE" -p "$PRODUCT" \
  -m "test(instrument): composite for the g3 closure run = product candidate $PRODUCT + lane F's shared streak ruler

The product candidate stays exactly as it is; the only added path is
\`$RULER_PATH\` (blob $RULER_BLOB, from $RULER_REPO@$RULER_HEAD).

Per the arbiter (iii): the closure run is attributed to THIS commit, not to mainline.
Mainline wants GREEN, it re-runs with its own exact SHA." 2>/dev/null) \
  || die "commit-tree 失败" 33
COMPOSITE=$(git -C "$OUT_REPO" rev-parse "$COMPOSITE")

# ---- 可推送：落一个具名 ref（可 fetch / 可 push），并证明 ref 真存在 -------------------
BRANCH="composite/$(git -C "$OUT_REPO" rev-parse --short=7 "$PRODUCT")-$(printf '%s' "$RULER_BLOB" | cut -c1-8)"
git -C "$OUT_REPO" update-ref "refs/heads/$BRANCH" "$COMPOSITE" || die "update-ref 失败 ⇒ 不可推送" 33
git -C "$OUT_REPO" rev-parse --verify "refs/heads/$BRANCH" >/dev/null || die "ref 建了又不在 ⇒ 不可推送" 34

# ---- 四条自证（全部现量，不写字面量）--------------------------------------------------
ok=1
DIFF=$(git -C "$OUT_REPO" diff --name-only "$PRODUCT" "$COMPOSITE" | tr '\n' ' ')
[ "$DIFF" = "$RULER_PATH " ] && say "[check] diff(产品, composite) 只有尺一个路径：$DIFF" \
  || { say "[check] 差异不止尺：$DIFF"; ok=0; }
if git -C "$OUT_REPO" cat-file -e "$COMPOSITE:$RULER_PATH"; then
  CBLOB=$(git -C "$OUT_REPO" rev-parse "$COMPOSITE:$RULER_PATH")
  [ "$CBLOB" = "$RULER_BLOB" ] && say "[check] composite 树里的尺与来源 blob 逐字相等：$CBLOB" \
    || { say "[check] 尺 blob 不等：$CBLOB ≠ $RULER_BLOB"; ok=0; }
else say "[check] composite 树里没有尺"; ok=0; fi
PARENT=$(git -C "$OUT_REPO" rev-parse "$COMPOSITE^" 2>/dev/null | cut -c1-7)
[ "$PARENT" = "$(git -C "$OUT_REPO" rev-parse --short=7 "$PRODUCT")" ] \
  && say "[check] composite 的父提交 = 产品候选 $PARENT（产品保持干净）" \
  || { say "[check] 父提交是 $PARENT，不是产品 $PRODUCT"; ok=0; }
RB=$(git -C "$OUT_REPO" cat-file -s "$RULER_BLOB"); RH=$(printf '%s\n' "$(git -C "$OUT_REPO" cat-file blob "$RULER_BLOB")" | wc -c | tr -d ' ')
say "[check] 尺 $RB 字节，blob sha1 ${RULER_BLOB:0:16}；sha256 前缀 $(git -C "$OUT_REPO" cat-file blob "$RULER_BLOB" | sha256sum | cut -c1-12)"

[ "$ok" = "1" ] || die "自证未全过 ⇒ 不出 composite" 34
say "composite = $COMPOSITE  ref = refs/heads/$BRANCH（可推送、可审）"
say "跑 closure 时：CNX_CLOSURE_SHA=$COMPOSITE，并且收据必须写清"
say "  「这轮的绿属于 composite $COMPOSITE，不属于主线；主线要 GREEN 就拿主线自己的 exact SHA 再跑」"
printf '%s\n' "$COMPOSITE"
