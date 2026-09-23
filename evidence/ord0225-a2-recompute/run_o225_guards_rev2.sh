#!/usr/bin/env bash
# ORD-0225 · 守卫矩阵实测：每一格都必须"没跑一个 closure 进程就非零退出"
# 注意（本机已知坑）：`env VAR=x cmd` 前缀在这台机器上可能什么都没启动却返回 0，
# 所以这里一律用 bash -c 的内联赋值，不用 env 前缀。
F=/d/moodle/_qoder_f_run/o225_closure.sh
S15=/d/moodle/_qoder_f_run/o225_fixtures/tree_s15
SNAME=/d/moodle/_qoder_f_run/o225_fixtures/tree_nameonly
NR=/d/moodle/_qoder_f_run/o225_fixtures/tree_no_ruler
fail=0
cells=0
# 本矩阵里凡是用 CNX_AUTH_REF=HEAD 的格子都在 **ancestor 模式**（本机分支只当管道夹具）；
# 真跑 closure 用的是 CNX_AUTH_MODE=published（证据分支上 blob 逐字相等），格子列在最后。
export CNX_AUTH_MODE=ancestor

check() {  # check <期望码> <格名> <bash -c  body>
  local want="$1" name="$2" body="$3" out rc
  cells=$((cells + 1))
  out=$(bash -c "$body" 2>&1); rc=$?
  local tail
  tail=$(printf '%s' "$out" | grep -a '\[o225\]' | tail -1 | cut -c1-170)
  if [ "$rc" = "$want" ]; then
    printf '✓ %-20s rc=%s（期望 %s）| %s\n' "$name" "$rc" "$want" "$tail"
  else
    printf '✗ %-20s rc=%s（期望 %s）| %s\n' "$name" "$rc" "$want" "$tail"
    fail=$((fail + 1))
  fi
}

# CNX_AUTH_REF=HEAD 只是**管道夹具**（让守卫 22 放行，好让后面的格被测到）：
# HEAD 是本机分支、不是权威 ref。真正的权威 ref 要等 Commander 推送/并线之后指定。
A=HEAD
# 跑之前先拍一份"已存在的 step1 收据"名单，结尾只比对**新增**，历史收据不参与判红。
BEFORE=$(ls -1 /d/moodle/_qoder_f_run/o225_receipts/ 2>/dev/null | grep -a step1 | sort)
check 10 no_sha            "unset CNX_CLOSURE_SHA; bash $F"
check 11 bogus_sha         "CNX_CLOSURE_SHA=ffffffffffffffff bash $F"
# ↓ 决定二补的三格：权威坐标
check 22 auth_ref_missing  "CNX_CLOSURE_SHA=0748a1f bash $F"
check 22 auth_ref_unresolved "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=refs/remotes/origin/no_such_ref bash $F"
check 22 auth_sha_local_only "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=refs/remotes/origin/HEAD bash $F"
check 12 no_tests_dir       "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=/d/moodle/_qoder_f_run/o225_fixtures/tree_empty bash $F"
check 13 no_ruler_in_tree  "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$NR bash $F"
check 14 label_hits_two    "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$S15 CNX_G3_LABEL=G3_TWIN_DOORS bash $F"
check 14 label_hits_zero   "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$S15 CNX_G3_LABEL=NO_SUCH_LABEL_AT_ALL bash $F"
check 15 collects_two      "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$S15 CNX_G3_LABEL=G3_CONCURRENT_OPEN_GENERATION bash $F"
# 解析器规则二：label 只出现在函数名里也要钉到（否则 C 不把名字重复写进函数体就会被我假拒）
check 21 resolver_rule2_by_function_name "CNX_DRY_RUN=1 CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$SNAME CNX_G3_LABEL=G3_CONCURRENT_OPEN_GENERATION CNX_CLAUSE6='单节点形制 10 进程，无 sleep/重试/退避/降并发/放宽断言' CNX_REVERSE_MUTATION=KILLED bash $F"
check 14 resolver_rule2_does_not_pass_anything "CNX_DRY_RUN=1 CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$SNAME CNX_G3_LABEL=G3_TAIL_A_GENERATION bash $F"

# (iii) composite 守卫：用**真造出来的** composite（o225_composite.sh 落在 lane F 自己的仓里）。
# 权威 ref 这里同样是本机管道夹具：实测 refs/heads/integration/frontend-apple-pass1 含 f92f9e9。
MINE=/d/moodle/_qoder_f_o210b_20260922
MREF=refs/heads/integration/frontend-apple-pass1     # 本机管道夹具：实测它含 f92f9e9
COMP=$(git -C "$MINE" rev-parse refs/heads/composite/f92f9e9-fcf76941 2>/dev/null | tr -d '\r\n')
NOREF=$(tr -d '\r\n' < o225_receipts/noref_composite_sha.txt 2>/dev/null)
COM_ARGS="CNX_REPO=$MINE CNX_AUTH_REPO=$MINE CNX_AUTH_REF=$MREF CNX_DRY_RUN=1 CNX_CLAUSE6='单节点形制 10 进程，无 sleep/重试/退避/降并发/放宽断言' CNX_REVERSE_MUTATION=KILLED"
if [ -n "$COMP" ] && [ -n "$NOREF" ]; then
  check 24 composite_wrong_parent "$COM_ARGS CNX_CLOSURE_SHA=$COMP CNX_PRODUCT_SHA=50d1c4d bash $F"
  check 25 composite_no_named_ref "$COM_ARGS CNX_CLOSURE_SHA=$NOREF CNX_PRODUCT_SHA=f92f9e9 bash $F"
  check 21 composite_all_guards_pass "$COM_ARGS CNX_CLOSURE_SHA=$COMP CNX_PRODUCT_SHA=f92f9e9 CNX_G3_LABEL=G3_CONCURRENT_OPEN_GENERATION bash $F"
else
  echo "✗ composite 三格没跑：真 composite 不在（COMP=$COMP NOREF=$NOREF）—— 没跑不算通过"; fail=$((fail + 1))
fi

# 第 8/9 格：守卫顺序。声明不齐 ⇒ 16 必须在开跑之前；声明齐 ⇒ 守卫全过，干跑打印命令并以 21 收尾
check 16 decl_missing_blocks_run "CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$S15 CNX_G3_LABEL=G3_SINGLE_OK bash $F"
check 21 all_guards_pass_dry_run "CNX_DRY_RUN=1 CNX_CLOSURE_SHA=0748a1f CNX_AUTH_REF=$A CNX_TREE=$S15 CNX_G3_LABEL=G3_SINGLE_OK CNX_CLAUSE6='只用单节点形制 10 个独立进程，无 sleep/重试/退避/降并发/放宽断言' CNX_REVERSE_MUTATION=KILLED bash $F"

# ---- published 权威模式（Commander 输入一：权威 = 证据分支上 blob 逐字相等）----
CB=$(git hash-object --no-filters evidence_pkg/composite.patch 2>/dev/null | tr -d '\r\n')
check 22 published_missing_product_patch_coord \
  "CNX_AUTH_MODE=published CNX_REPO=$MINE CNX_CLOSURE_SHA=$COMP CNX_PRODUCT_SHA=f92f9e9 bash $F"
check 22 published_wrong_blob \
  "CNX_AUTH_MODE=published CNX_REPO=$MINE CNX_CLOSURE_SHA=$COMP CNX_PRODUCT_SHA=f92f9e9 CNX_PRODUCT_PATCH=evidence/ord0225-composite/composite.patch=0000000000000000000000000000000000000000 bash $F"
# 抄来的前缀不许当权威（今天真踩过：拿 16 位前缀去核，对上了却被读成"没发布"，反过来更糟）
check 22 published_prefix_claim_rejected \
  "CNX_AUTH_MODE=published CNX_REPO=$MINE CNX_CLOSURE_SHA=$COMP CNX_PRODUCT_SHA=f92f9e9 CNX_PRODUCT_PATCH=evidence/ord0225-composite/composite.patch=${CB:0:16} bash $F"
# ③机制探针：claim 用我自己已发布的 composite.patch —— 这一格只证明"blob 逐字相等就放行"这条
#   机械通路是通的，**不是**把它当成产品候选的 patch 报出去（真跑必须填 C 发布的那件）。
check 21 published_mechanism_probe \
  "CNX_AUTH_MODE=published CNX_REPO=$MINE CNX_CLOSURE_SHA=$COMP CNX_PRODUCT_SHA=f92f9e9 CNX_DRY_RUN=1 CNX_G3_LABEL=G3_CONCURRENT_OPEN_GENERATION CNX_CLAUSE6='单节点形制 10 进程，无 sleep/重试/退避/降并发/放宽断言' CNX_REVERSE_MUTATION=KILLED CNX_PRODUCT_PATCH=evidence/ord0225-composite/composite.patch=$CB bash $F"

echo "--- 有没有哪一格偷偷写出了**新的** step1 收据 ---"
# 旧写法是"目录里不该有 step1 文件"，可真跑过一次 closure 之后那份合法收据会一直在，
# 于是每次守卫矩阵都假红。正确的判据是"本矩阵没跑出**新的**收据"，与历史收据无关。
AFTER=$(ls -1 /d/moodle/_qoder_f_run/o225_receipts/ 2>/dev/null | grep -a step1 | sort)
NEW=$(comm -13 <(printf '%s\n' "$BEFORE" | sort) <(printf '%s\n' "$AFTER" | grep -v '^$' | sort))
if [ -n "$NEW" ]; then
  echo "✗ 本矩阵跑期间新增了收据 ⇒ 有格子真的跑了 closure 进程："; printf '%s\n' "$NEW"
  fail=$((fail + 1))
else
  echo "✓ 新增 0 份（历史 $(( $(printf '%s\n' "$AFTER" | grep -c . ) )) 份原样保留）：$cells 格全部在第一个子进程之前就退出"
fi
echo "矩阵不符格数 = $fail"
exit $((fail > 0 ? 1 : 0))
