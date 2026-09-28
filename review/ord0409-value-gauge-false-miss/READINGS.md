# ORD-0409 · 那一格两代都不在产物里的字典键：两种成因都不成立，量到了第三种

车道：Q（会话 8e5245f0）· 基线 = 现尖 `a7d852d47487f4073d63197e388f7ccb7406b762`
**本单产品字节改动数=0**：没有改任何字典值、没有删键、没有接新引用、没动别的键。
件里只有读数与复现方法。

## 号令者的判据我复跑通了，而且只多出这一格

同一把尺（`cmdr_bundle_copy_check_r2.py` 的 `PAIR_RE`，逐字照抄，不改）跑两代：

| 读数 | 值 | 坐标 |
| --- | --- | --- |
| 字典面文件数 | files=7 | `frontend/src` 下 `i18n/` + `*Copy.ts` 的 ls-tree 结果 |
| 分母（捕获到的键值对） | pairs=734 | 同上 |
| 手机链在服的那一代缺 | misses_served=17 | 件 `two_generation_read.json` 字段 `misses_served` |
| 现尖全新构建缺 | misses_fresh=1 | 件 `two_generation_read.json` 字段 `misses_fresh` |
| 两代都缺 | 1 格 = `shell.reservationReviewFields` | `frontend/src/i18n/LocaleContext.tsx:634` |

也就是说"两代都缺的只剩一格"这句是实的，我复现到了同一枚。差的是它的**成因**。

## 那一格为什么"缺"：尺的 needle 自己带了个反斜杠

`PAIR_RE = "([a-z]…\.[A-Za-z]…)"[\s:]*"([^"]{12,120})"` —— 值那一段是 `[^"]`，
遇到**转义引号**就断。这条英文值里有两处 `\"`：

```
"This cannot become a commitment yet - the server is still missing {fields}. It is in \"Confirmations waiting on you\" below: …, then press \"Confirm and protect\"."
```

于是尺捕到的是 86 字符的**前半截**，最后一个字节是反斜杠（件 `ruler_repro.json` 字段
`captured_values_ending_in_a_backslash`=1，`which` 就这一条）。而压缩器把这个字面量改用单引号重新
输出，`\"` 在产物里变成裸 `"`：

- 产物里实际在的（180 字节，未转义形态）：`… It is in "Confirmations waiting on you" below: fill in what is missing, then press "Confirm and protect"`
  → 在服代 present=True，现尖全新构建 present=True；
- 尺的 needle（以反斜杠结尾）→ 两代都 present=False；
- 源码那种转义形态（`\"`）在**两代产物里都找不到**（present=False）——这就是"缺"的全部来源。

产物窗口逐字（现尖构建 `index-C06ZwEPS.js`，量法：`str.find` 后取 180 字节）：
`This cannot become a commitment yet - the server is still missing {fields}. It is in "Confirmations waiting on you" below: fill in what is missing, then press "Confirm and protect"`

## 两个候选成因，各自怎么被判掉

**① 「英文串根本没进产物 = 那面英文屏永远显示不到这句话」——不成立。**
上面那 180 字节在两代产物里都在；而且这条键有活引用：
`frontend/src/app/V8Experience.tsx:1260` 在 `importReservation` 完成路径上
`setMessage(draft.status === "READY_FOR_CONFIRMATION" ? t("shell.reservationConfirmed") : t("shell.reservationReviewFields", { fields: … }))`
—— 旅客导入一张还缺字段的确认单就会走这一支。要"接上"的东西已经接上了。

**② 「键根本没人引用 = 死字典项」——不成立。**
`git grep -n reservationReviewFields a7d852d4` 命中 3 处：上面那处引用 + `LocaleContext.tsx:634`（en）
+ `LocaleContext.tsx:1422`（zh）。zh 侧捕到的 needle 是完整 58 字符（它用「」不用转义引号），所以
zh 在产物里判得到、en 判不到 —— 差的不是内容，是**引号写法**。

**③ 实际成因：尺对"含转义引号的值"必然误报。** 不是产品缺陷，也不该由产品改文案去迁就尺：
把 `\"` 换成「」或单引号确实能让 `values_not_found` 从 1 变 0，但那是**改用户可见文案去喂一把
有盲区的尺**，本车道不做，也不建议。

## 盲区有多大（这条是给尺的，不是给产品的）

734 对里，捕到的值以反斜杠结尾的只有 1 条（就是这格）；**"前缀侥幸命中"的假绿=0 条**
（`prefix_only_passes`=0）。所以这个盲区目前精确地就是这一格，不是一片。
修法形状（留给号令者，量具代码路径本车道不重写）：捕值时先按 JS 字面量把 `\"` 还原再截，
或者比对时把 needle 里的 `\"` 与产物里的 `"` 归一（两侧同做），二者都能让判据真地变 0。

## 没改善的部分

1. `values_not_found` 在这一代仍是 1。我**没有**把它做成 0，因为唯一诚实的 0 要改的是尺；
   改文案能拿到绿，但那会把一屏正确的英文句子换成另一种引号风格，只为了让一把量具闭嘴。
2. 手机链那 17 格缺是真缺（在服代比现尖旧），不是本单范围，也没去查。
3. 我没有屏读这一句英文：要走通得先造一张"缺字段的确认单"导入态，本单没造数据。
   产物字节 + 活引用两条已经足够判"能不能显示"，但"真显示出来那一屏"仍是一格没量的账。
4. 键值里那两处 `\"` 是英文排版上的选择（给 UI 标签加引号）。若号令者判"该统一成「」"，
   那是**文案口径**决定，请单开一格点名，我按那格的口径改并把尺的读数一起交。
