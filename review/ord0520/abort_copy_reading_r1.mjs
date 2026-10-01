import { abortCopy, fillAbort, ABORT_REFUSAL_COPY, journeyAbortCopy } from
  "./abortcopy.mjs";
const zh = abortCopy("zh-CN", "abort.explains");
const en = abortCopy("en", "abort.explains");
const cjk = (zh.match(/[\u4e00-\u9fff]/g) || []).length;
const checks = {
  keys_en: Object.keys(journeyAbortCopy.en).length,
  keys_zh: Object.keys(journeyAbortCopy["zh-CN"]).length,
  keys_equal: JSON.stringify(Object.keys(journeyAbortCopy.en).sort()) === JSON.stringify(Object.keys(journeyAbortCopy["zh-CN"]).sort()),
  zh_names_live_screen: zh.includes("实时行程"),
  zh_names_trip_list: zh.includes("行程列表"),
  zh_says_no_way_back: zh.includes("没有把中止撤回的门"),
  zh_separates_from_bin: zh.includes("中止不等于丢弃"),
  en_says_no_way_back: en.includes("no door that un-aborts"),
  zh_cjk_count: cjk,
  refusal_names_covered: Object.keys(ABORT_REFUSAL_COPY).sort(),
  // a promise the server cannot keep must not appear anywhere in this screen's words
  no_unabort_promise: !Object.values(journeyAbortCopy["zh-CN"]).join("|").match(/撤销中止|取消中止|恢复这趟|把中止恢复/),
  no_second_action_on_dropped: !Object.values(journeyAbortCopy["zh-CN"]).join("|").match(/丢弃这趟|把它丢弃/),
};
console.log(JSON.stringify(checks, null, 1));
console.log("SENTENCE_ZH=" + zh);
console.log("FILLED=" + fillAbort(abortCopy("zh-CN", "abort.done"), { title: "厦门" }));
const counts = new Set(["keys_en", "keys_zh", "zh_cjk_count", "refusal_names_covered"]);
const all_ok = Object.entries(checks).every(([k, v]) => counts.has(k) || v === true);
console.log("COPY_READING_VERDICT=" + (all_ok ? "PASSED" : "FAILED"));
process.exit(all_ok ? 0 : 1);
