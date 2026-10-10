import { catalogueCountSentence } from "./src/features/planning/catalogueReadback";

const CASES = [1, 2, 5, 0, null];
const out = [];
for (const zh of [false, true]) {
  for (const n of CASES) {
    const text = catalogueCountSentence(
      n === null ? null : { source: "server", placeCount: n, httpStatus: 200 },
      zh,
    );
    out.push(
      (zh ? "zh  " : "en  ") +
        "count=" + String(n) + " text=" + JSON.stringify(text),
    );
  }
}
console.log(out.join("\n"));
