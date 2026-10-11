import { fillRank, planRankingCopy } from "./src/features/planning/planRankingCopy";

const L: string[] = [];
const tmpl = planRankingCopy.en["rank.evidenceNote"];
L.push("# real resolver, real table; control arm uses the base-commit literal bytes");
L.push("after template=" + JSON.stringify(tmpl));
const beforeTmpl =
  "{hard} of {total} legs on this plan rest on evidence the gate accepts as hard; the rest are {quality}.";
for (const total of [1, 2, 0, 56]) {
  const after = fillRank(tmpl, { hard: total, total, quality: "soft" });
  const before = fillRank(beforeTmpl, { hard: total, total, quality: "soft" });
  L.push("total=" + total + " before=" + JSON.stringify(before) + " after=" + JSON.stringify(after));
}
process.stdout.write(L.join("\n") + "\n");
