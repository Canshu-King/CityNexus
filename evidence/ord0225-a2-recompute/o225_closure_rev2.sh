#!/usr/bin/env bash
# ORD-0225 · 10-process closure 的**一条命令**交接件（lane F，2026-09-23）
#
# 禁制已遵守：本脚本不改那把尺（`_qoder_streak_receipt.py` 一行都不动）、不预跑 closure
# （前置不成立时它跑不到第 1 个进程就退出）、不碰 C/D/B 的文件（只 git archive 导出、只读）。
# 唯一实现仍是 <tree>/backend/tests/_qoder_streak_receipt.py；live_checks/gate_streak.py 是薄适配器。
#
# 用法（等 C 的 ORD-0224 ② 给出 exact SHA 之后）：
#   CNX_CLOSURE_SHA=<C 的 corrected g3 exact SHA> \
#   CNX_G3_LABEL=G3_CONCURRENT_OPEN_GENERATION \
#   CNX_CLAUSE6="只用 pytest <nodeid> 单节点形制，10 个独立进程，无 sleep/重试/退避/降并发/放宽断言" \
#   CNX_REVERSE_MUTATION=KILLED \
#   CNX_AUTH_REF=refs/remotes/<远端>/<被推送的分支> \
#   bash /d/moodle/_qoder_f_run/o225_closure.sh
#   （CNX_AUTH_REF 不给 ⇒ 守卫 22 直接拒跑：本地未推送的 SHA 不是坐标。它指向哪个 ref 由
#     Commander 在并线/推送之后定，我不替你选。）
#
# 为什么要两步（2026-09-23 更新：Commander 已修适配器，blob 4510825b2d803d37 —— clause6_declared
# 现在可传，且只有 closure_grade=CLOSED 才返 0）：
#   第 1 步 = 纯测量。故意**不传**自证文本、也不带 CNX_ORD0210_REVERSE_MUTATION，免得声明污染读数；
#             不传时适配器自己会印那句"到不了 CLOSED"。
#   第 2 步 = 判级。用**同一把尺**（从被测树 importlib）再判一次，只把两句声明递进入参，
#             并硬要求两次 verdict 串逐字相等，不等 ⇒ 19 且撤等级。
#   两步是同一条尺的**两个调用点**，不是两把尺；19 那一格就是专门用来抓"两把尺"的。
#
# 退出码（每格具名；没达成前置时绝不印绿）：
#   0  = 第 2 步 closure_grade=CLOSED（唯一允许说"closure 达成"的出口）
#   10 = 缺 CNX_CLOSURE_SHA（scope 第一把键是 exact SHA）
#   11 = SHA 在集成线解析不到（本地幽灵 SHA 不算证据）
#   12 = 导出树建不出来 / 没有 backend/tests
#   13 = 导出树里没有共享尺 ⇒ 先去并线，**不许复制第二把尺**去绕
#   14 = label 解析到的 nodeid 不是恰好 1 条（0 条=门还没落地；2 条=两把门不许合跑）
#   15 = 该 nodeid 收集到的用例数不是 1（没有分母就没有红绿）
#   16 = 缺 CNX_CLAUSE6 或 CNX_REVERSE_MUTATION ⇒ **开跑之前**就拒绝（默认不给人"先跑 10 个进程"的默认路径）；
#        确实只要一次纯测量要显式 CNX_ALLOW_MEASUREMENT_ONLY=1，跑完仍以 16 收尾，不出结案文件
#   17 = STREAK_MET(10) 但等级停在 STREAK_GREEN（结案独立证据不齐）
#   18 = streak 未达成 / verdict 具名不合法
#   19 = 两次 verdict 串不一致（第二把尺嫌疑）
#   20 = 观测批次（observation_runs），按第 2/8 条不许结案
#   21 = CNX_DRY_RUN=1：所有前置守卫都过了，只打印将要执行的命令，不起子进程。
#        0 这个出口**只**留给 closure_grade=CLOSED，干跑不许借用它。
#   22 = 权威坐标不成立：没给 CNX_AUTH_REF / ref 解析不到 / SHA 不是该 ref 的祖先
#        （= 只是本机未推送的提交，本地 SHA 不是坐标）⇒ 开跑之前就拒。
#   23 = 判级器现场再证时发现**尺不在被测 SHA 的树里** ⇒ 我 import 的尺与被测 SHA 不同源，等级撤销
#        （脚本侧的同一件事由 13 拦，并且会把发现落成 o225_receipts/finding_no_ruler_<SHA>.json）
#
# 入口变量（除 CNX_CLOSURE_SHA/CNX_G3_LABEL 外都有默认，真跑 closure 时不要设 CNX_TREE）：
#   CNX_REPO=集成线仓库路径（git cat-file 与 git archive 的来源）
#   CNX_GATE_STREAK=薄适配器路径（默认 Commander 的 live_checks/gate_streak.py）
#   CNX_TREE=替身导出树，只用于跑守卫 12/13/14/15/16 的自检；设了它就跳过 git archive，脚本会醒目警告
#   CNX_ALSO=同一 (SHA,node,shape) 三元组的另一份 step1 收据 ⇒ 第 2 步并批定性（批次是 provenance）
#   CNX_ALLOW_MEASUREMENT_ONLY=1 才允许"无声明只测量"那一趟
set -uo pipefail

REPO="${CNX_REPO:-/d/moodle/_qoder_integration_20260919}"
TOOL="${CNX_GATE_STREAK:-/d/moodle/_qoder_cmdr_ref_20260921/live_checks/gate_streak.py}"
RUNDIR=/d/moodle/_qoder_f_run
PY=D:/moodle/CityNexus/.venv/Scripts/python.exe
SHA="${CNX_CLOSURE_SHA:-}"
LABEL="${CNX_G3_LABEL:-G3_CONCURRENT_OPEN_GENERATION}"
OUT_DIR="$RUNDIR/o225_receipts"
mkdir -p "$OUT_DIR"

say() { printf '[o225] %s\n' "$*" >&2; }
die() { say "$1"; exit "$2"; }

say "禁制：不改尺、不预跑、不碰他车道文件；尺的唯一实现 = <tree>/backend/tests/_qoder_streak_receipt.py"
say "被测线 $REPO；适配器 $TOOL（sha256 前 12 位 = $(sha256sum "$TOOL" 2>/dev/null | cut -c1-12 || echo 读不到)）"

[ -n "$SHA" ] || die "缺 CNX_CLOSURE_SHA：closure 的 scope 第一把键是 exact SHA" 10
git -C "$REPO" cat-file -e "${SHA}^{commit}" 2>/dev/null \
  || die "SHA $SHA 在集成线解析不到（本地幽灵 SHA 不能当 closure 证据）" 11

# ---- 权威（Commander 输入一）：默认 = "已发布在证据分支上，blob sha1 逐字相等" ----------
# CNX_AUTH_MODE=published  ⇒ 权威 = Canshu-King/CityNexus @ commander/control 上有没有被主张的那件东西
# CNX_AUTH_MODE=ancestor   ⇒ 旧的"某 ref 的祖先"模型；本机分支只能当**管道夹具**，不许当权威
AUTH_MODE="${CNX_AUTH_MODE:-published}"
PRODUCT="${CNX_PRODUCT_SHA:-}"
AUTH_REPO="${CNX_AUTH_REPO:-$REPO}"
AUTH_SUBJECT="${PRODUCT:-$SHA}"
EVID="$OUT_DIR/authority_${SHA}.json"

if [ "$AUTH_MODE" = "published" ]; then
  CLAIMS=()
  [ -n "${CNX_PRODUCT_PATCH:-}" ] && CLAIMS+=(--claim "$CNX_PRODUCT_PATCH")
  [ -n "${CNX_RULER_PATCH:-}" ] && CLAIMS+=(--claim "$CNX_RULER_PATCH")
  if [ -n "$PRODUCT" ] && [ -z "${CNX_PRODUCT_PATCH:-}" ]; then
    die "composite 模式（给了 CNX_PRODUCT_SHA=$PRODUCT）却没给 CNX_PRODUCT_PATCH=<证据分支路径>=<blob sha1> ⇒ 被主张的产品候选没有外部坐标，权威不成立；少报一项就等于绕过守卫，不给走" 22
  fi
  REC_JSON="$RUNDIR/evidence_pkg/composite_commit_record.json"
  if [ -n "$PRODUCT" ] && [ -f "$REC_JSON" ]; then
    CP_BLOB=$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['patch_blob_sha1'])" "$REC_JSON")
    CP_PATH="${CNX_COMPOSITE_PATCH_PATH:-evidence/ord0225-composite/composite.patch}"
    CLAIMS+=(--claim "$CP_PATH=$CP_BLOB")
    CLAIMS+=(--claim "${CNX_COMPOSITE_RECORD_PATH:-evidence/ord0225-composite/composite_commit_record.json}=$(git hash-object --no-filters "$REC_JSON")")
    CLAIMS+=(--claim "${CNX_COMPOSITE_BUILDER_PATH:-evidence/ord0225-composite/o225_composite.sh}=$(git hash-object --no-filters "$RUNDIR/o225_composite.sh")")
  fi
  [ "${#CLAIMS[@]}" -gt 0 ] || die "CNX_AUTH_MODE=published 但一个 --claim 都没有（产品候选的已发布 patch 坐标没给）⇒ 权威无从证明" 22
  "$PY" "$RUNDIR/o225_evidence.py" assert-authority "${CLAIMS[@]}" --out "$EVID" >&2
  EV_RC=$?
  case "$EV_RC" in
    0) say "权威 = published（证据分支 blob 逐字相等）；回执 $EVID；pushed=false（不 push 分支，可审路径＝已发布 patch + 构造器）" ;;
    52) die "权威不成立（22）：被主张的东西没有全部发布在证据分支上（逐项读数见 $EVID）。本地 SHA 不是坐标。" 22 ;;
    54) die "权威不成立（22）：claim 不是 `路径=<满 40 位 blob sha1>` 的形式 ⇒ 前缀只能说明'东西在'，不能当闭包坐标（先把 40 位补全再跑；探针没坏，坏的是输入）" 22 ;;
    *)  die "权威探针自身故障（26，**不是**'未发布'）：rc=$EV_RC ⇒ 量具坏了不许冒充判据，先看 $EVID 与上面的 stderr" 26 ;;
  esac
  AUTH_ARGS_EXTRA=(--authority-receipt "$EVID")
else
  AUTH_ARGS_EXTRA=()
  AUTH_REF="${CNX_AUTH_REF:-}"
  [ -n "$AUTH_REF" ] || die "CNX_AUTH_MODE=ancestor 但没给 CNX_AUTH_REF ⇒ 拒跑（默认不放行）" 22
  git -C "$AUTH_REPO" cat-file -e "${AUTH_SUBJECT}^{commit}" 2>/dev/null \
    || die "被主张的提交 $AUTH_SUBJECT 在 $AUTH_REPO 里解析不到" 22
  git -C "$AUTH_REPO" rev-parse --verify "${AUTH_REF}^{commit}" >/dev/null 2>&1 \
    || die "权威 ref $AUTH_REF 在 $AUTH_REPO 里解析不到 ⇒ 拒跑" 22
  AUTH_TIP=$(git -C "$AUTH_REPO" rev-parse --short=7 "${AUTH_REF}^{commit}")
  git -C "$AUTH_REPO" merge-base --is-ancestor "$AUTH_SUBJECT" "$AUTH_REF" 2>/dev/null \
    || die "$AUTH_SUBJECT 不是 $AUTH_REF（tip $AUTH_TIP）的祖先 ⇒ 只是本机未推送的提交 ⇒ 拒跑" 22
  say "权威 = ancestor 模式（本机 ref 只能当管道夹具，**不要**拿它当外部坐标）"
fi

# ---- (iii) composite：跑 closure 的那棵树有自己的 SHA，且必须可审 ------------------------
# 仲裁压轴（要求写进交接与收据）："跑绿属于 composite，不属于 mainline；
# 主线想要 GREEN，就拿主线自己的 exact SHA 再跑。"
RULER_PATH_IN_TREE="backend/tests/_qoder_streak_receipt.py"
PRODUCT="${CNX_PRODUCT_SHA:-}"
if [ -n "$PRODUCT" ]; then
  git -C "$REPO" cat-file -e "${PRODUCT}^{commit}" 2>/dev/null \
    || die "CNX_PRODUCT_SHA=$PRODUCT 解析不到 ⇒ composite 的归因链断了" 24
  PARENT=$(git -C "$REPO" rev-parse "$SHA^" 2>/dev/null || echo "无父提交")
  [ "$(git -C "$REPO" rev-parse --short=7 "$PRODUCT")" = "$(printf '%s' "$PARENT" | cut -c1-7)" ] \
    || die "被测 SHA $SHA 的父提交是 ${PARENT:0:7}，不是产品候选 $PRODUCT ⇒ 这不是那把门的 composite" 24
  DIFFPATHS=$(git -C "$REPO" diff --name-only "$PRODUCT" "$SHA" | tr '\n' ' ')
  [ "$DIFFPATHS" = "$RULER_PATH_IN_TREE " ] \
    || die "composite 相对产品候选多了别的东西（$DIFFPATHS）⇒ 产品候选没保持干净，归因会被污染" 24
  RSHA=$(git -C "$REPO" cat-file blob "$SHA:$RULER_PATH_IN_TREE" 2>/dev/null | sha256sum | cut -c1-12)
  say "composite 自证：父 = 产品 $PRODUCT；差异只有 $RULER_PATH_IN_TREE；尺 sha256[:12] = $RSHA"
  say "  ⇒ 本轮任何\"绿\"都记在 composite $SHA 名下，**不是**主线 $PRODUCT 的绿"
  REF=$(git -C "$REPO" for-each-ref --format='%(refname)' --points-at "$SHA" refs/heads/composite/ | head -1)
  PUBLISHED_OK=""
  if [ "$AUTH_MODE" = "published" ] && [ -f "$EVID" ]; then
    PUBLISHED_OK=$("$PY" -c "
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
print('yes' if any(c.get('proven') and c.get('repo_path','').endswith('composite.patch') for c in r.get('checks') or []) else '')" "$EVID")
  fi
  if [ -z "$REF" ] && [ -z "$PUBLISHED_OK" ]; then
    die "composite 既没有具名 ref、也没有已发布且 blob 相等的 composite.patch ⇒ 不可审 ⇒ 拒跑（决定一 (b)）" 25
  fi
  say "  可审凭据：本机 ref=${REF:-无}；已发布 composite.patch=${PUBLISHED_OK:-否}（pushed=false 照写）"
else
  say "⚠ 没给 CNX_PRODUCT_SHA ⇒ 按\"被测 SHA 就是产品本身\"处理（尺必须在它自己的树里，否则守卫 13 会拦）。"
  say "   走 (iii) 的 composite 跑法请给 CNX_PRODUCT_SHA，否则收据里写不出\"绿属于谁\"。"
fi

TREE="${CNX_TREE:-$RUNDIR/e_o225_$SHA}"
if [ -n "${CNX_TREE:-}" ]; then
  say "⚠ CNX_TREE 被显式覆盖成 $TREE —— 这只用于验证守卫 13/14/15 的替身树；"
  say "   真正的 closure 必须由 git archive \$SHA 导出，不要用覆盖口"
else
  if [ ! -d "$TREE/backend/tests" ]; then
    rm -rf "$TREE"; mkdir -p "$TREE"
    git -C "$REPO" archive "$SHA" | tar -x -C "$TREE" || die "导出树建不出来：$TREE" 12
  fi
fi
[ -d "$TREE/backend/tests" ] || die "导出树没有 backend/tests：$TREE" 12
if [ ! -f "$TREE/backend/tests/_qoder_streak_receipt.py" ]; then
  RPATH="backend/tests/_qoder_streak_receipt.py"
  RCHK_RC=0
  git -C "$REPO" cat-file -e "${SHA}:$RPATH" 2>/dev/null || RCHK_RC=$?
  IN_SHA=$(git -C "$REPO" rev-parse "${SHA}:$RPATH" 2>&1 >/dev/null | head -1 | tr -d '\r\n')
  RSRC="${CNX_RULER_SOURCE_REPO:-/d/moodle/_qoder_f_o210b_20260922}"
  RHEAD=$(git -C "$RSRC" rev-parse --short=7 HEAD 2>/dev/null || echo MEASUREMENT_FAILED)
  RBLOB=$(git -C "$RSRC" rev-parse "HEAD:$RPATH" 2>/dev/null || echo MEASUREMENT_FAILED)
  RBTYPE=$(git -C "$RSRC" cat-file -t "HEAD:$RPATH" 2>/dev/null || echo MEASUREMENT_FAILED)
  if [ "$RBTYPE" = "blob" ]; then
    RBYTES=$(wc -c < "$RSRC/$RPATH" | tr -d ' '); RSHA=$(sha256sum "$RSRC/$RPATH" | cut -c1-12)
  else
    RBYTES=MEASUREMENT_FAILED; RSHA=MEASUREMENT_FAILED
  fi
  cat > "$OUT_DIR/finding_no_ruler_${SHA}.json" <<JSON
{
  "finding": "RULER_NOT_IN_TESTED_SHA",
  "meaning": "被测 SHA 的树里没有那把唯一的尺 ⇒ 谁都不能拿这把尺给这个 SHA 出结案判词；并线是 Commander 的决定",
  "tested_sha": "$SHA",
  "repo": "$REPO",
  "export_tree": "$TREE",
  "ruler_in_export_tree": false,
  "cat_file_rc_for_ruler_in_sha": $RCHK_RC,
  "git_stderr_first_line": "$(printf '%s' "$IN_SHA" | cut -c1-160)",
  "ruler_where_it_does_live": {
    "measured_from": "$RSRC",
    "branch_head": "$RHEAD",
    "path": "$RPATH",
    "git_object_type": "$RBTYPE",
    "blob": "$(printf '%s' "$RBLOB" | cut -c1-40)",
    "bytes": $([ "$RBYTES" = MEASUREMENT_FAILED ] && echo '"MEASUREMENT_FAILED"' || echo "$RBYTES"),
    "sha256_12": "$RSHA"
  }
}
JSON
  say "发现已落文件：$OUT_DIR/finding_no_ruler_${SHA}.json"
  die "导出树里没有共享尺 _qoder_streak_receipt.py ⇒ 唯一实现不在被测 SHA 内（$SHA）；先去并线，别复制第二把尺" 13
fi

NODE=$("$PY" "$RUNDIR/o225_resolve_node.py" --tree "$TREE/backend" --label "$LABEL") \
  || die "按 label 解析 target nodeid 失败（上面已打印候选与原因）。两把门各自成单：tail-A 是独立一把，不许与 G3_CONCURRENT_OPEN_GENERATION 合跑" 14
NODE=$(printf '%s' "$NODE" | tr -d '\r\n')
[ -n "$NODE" ] || die "解析器返回空 nodeid" 14
say "scope = ($SHA, $NODE, single-node)"

cd "$TREE/backend"
COLLECT=$(PYTHONIOENCODING=utf-8 "$PY" -m pytest "$NODE" --collect-only -q -p no:randomly 2>&1 \
          | grep -oE "[0-9]+ tests? collected" | grep -oE "^[0-9]+" || echo 0)
[ "$COLLECT" = "1" ] || die "single-node 形制要求该 nodeid 恰好收集 1 条，实到 ${COLLECT:-0}（没有分母就没有红绿）" 15

DECL="${CNX_CLAUSE6:-}"; REV="${CNX_REVERSE_MUTATION:-}"
RECEIPT_A="$OUT_DIR/step1_gate_streak_${SHA}_${LABEL}.json"
MEASUREMENT_ONLY=0
if [ -z "$DECL" ] || [ -z "$REV" ]; then
  if [ "${CNX_ALLOW_MEASUREMENT_ONLY:-0}" = "1" ]; then
    MEASUREMENT_ONLY=1
    say "缺 CNX_CLAUSE6 或 CNX_REVERSE_MUTATION，但显式允许只测量 ⇒ 跑第 1 步，跑完仍以 16 收尾"
  else
    die "缺 CNX_CLAUSE6 或 CNX_REVERSE_MUTATION ⇒ 开跑之前就拒绝（不许拿『先跑 10 个进程再说』当默认）；确实只要一次测量请显式 CNX_ALLOW_MEASUREMENT_ONLY=1" 16
  fi
fi

# ── 第 1 步：10 个独立进程（适配器；反向突变/自证文本不进这一步，避免它污染测量）────
unset CNX_ORD0210_REVERSE_MUTATION
say "第 1 步：$PY $TOOL --tree $TREE/backend --node $NODE --sha $SHA --runs 10"
if [ "${CNX_DRY_RUN:-0}" = "1" ]; then
  say "CNX_DRY_RUN=1 ⇒ 只打印将要执行的命令，不起任何子进程；**这不是测量，更不是 streak**"
  say "  $PY $TOOL --tree $TREE/backend --node $NODE --sha $SHA --runs 10 --out $RECEIPT_A"
  say "  然后 $RUNDIR/o225_closure_judge.py --tree $TREE/backend --receipt $RECEIPT_A --clause6 <自证文本> --reverse-mutation $REV"
  exit 21
fi
PYTHONIOENCODING=utf-8 "$PY" "$TOOL" --tree "$TREE/backend" --node "$NODE" --sha "$SHA" \
  --runs 10 --out "$RECEIPT_A" 2>&1 | tail -14
ADAPTER_RC=${PIPESTATUS[0]}
[ -f "$RECEIPT_A" ] || die "第 1 步没写出收据：$RECEIPT_A" 18
# 与 Commander 的适配器口径对齐：0 只给 CLOSED，观察达标是 rc=2（收据里 observation_claim=OBSERVATION_MET）
case "$ADAPTER_RC" in
  0) say "适配器已自行判到 CLOSED（它拿到了声明才会给 0）⇒ 第 2 步只做交叉核对" ;;
  2) die "适配器报 OBSERVATION_MET（rc=2）：观测达标不是闭合 ⇒ 我这侧统一走 20" 20 ;;
  *) say "适配器 rc=$ADAPTER_RC（非 0 非 2 ⇒ 未闭合，继续第 2 步交叉核对）" ;;
esac

[ -n "$DECL" ] && [ -n "$REV" ] || die "只到测量：第 1 步收据在 $RECEIPT_A；结案需要自证文本 + 反向突变结果" 16

# ── 第 2 步：用同一把尺判到结案等级（只递声明入参，强制两次 verdict 相等）────────
ENVELOPE_B="$OUT_DIR/step2_closure_${SHA}_${LABEL}.json"
ALSO_ARGS=()
[ -n "${CNX_ALSO:-}" ] && ALSO_ARGS=(--also "$CNX_ALSO")
AUTH_ARGS=(--repo "$AUTH_REPO" ${AUTH_ARGS_EXTRA[@]:+${AUTH_ARGS_EXTRA[@]}})
[ "$AUTH_MODE" = "published" ] || AUTH_ARGS+=(--auth-ref "${CNX_AUTH_REF:-}")
[ -n "$PRODUCT" ] && AUTH_ARGS+=(--product-sha "$PRODUCT")
[ -n "${CNX_AUTH_URL:-}" ] && [ -n "${CNX_AUTH_BRANCH:-}" ] \
  && AUTH_ARGS+=(--auth-url "$CNX_AUTH_URL" --auth-branch "$CNX_AUTH_BRANCH")
PYTHONIOENCODING=utf-8 "$PY" "$RUNDIR/o225_closure_judge.py" \
  --tree "$TREE/backend" --receipt "$RECEIPT_A" --out "$ENVELOPE_B" \
  "${AUTH_ARGS[@]}" "${ALSO_ARGS[@]}" --clause6 "$DECL" --reverse-mutation "$REV" 2>&1 | tail -24
rc=$?
say "第 2 步退出码 = $rc；判级信封 = $ENVELOPE_B"
case "$rc" in
  0)  say "closure_grade=CLOSED ⇒ 这一格才可以写进结案叙事" ;;
  17) say "STREAK_MET(10) 但等级停在 STREAK_GREEN ⇒ 最多签 streak 达成，不签 CLOSED" ;;
  19) say "两次 verdict 不一致 ⇒ 第二把尺嫌疑，结论已撤（文件里等级被写成 WITHHELD_REFUSED）" ;;
  20) say "观测批次不许结案" ;;
  22) say "判级器也认为权威坐标不成立 ⇒ 等级已撤；先推送/发布再开 closure" ;;
  23) say "尺不在被测 SHA 的树里 ⇒ 我 import 的尺与被测 SHA 不同源，等级已撤（并线决定在你）" ;;
  *)  say "streak 未达成或 verdict 不合法 ⇒ 交回读数，不定性" ;;
esac
exit "$rc"
