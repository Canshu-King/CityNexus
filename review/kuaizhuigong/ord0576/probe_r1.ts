import { catalogueCountSentence } from "../../../frontend/src/features/planning/catalogueReadback";

const states: Array<[string, unknown]> = [
  ["unreadable_503", { source: "unreadable", placeCount: null, httpStatus: 503 }],
  ["no_readback", null],
  ["zero", { source: "server", placeCount: 0, httpStatus: 200 }],
];

for (const [tag, readback] of states) {
  for (const zh of [true, false]) {
    console.log(`${tag} | ${zh ? "zh" : "en"} | ${catalogueCountSentence(readback as never, zh)}`);
  }
}

for (const count of [1, 2, 8, 11, 20, 101]) {
  for (const zh of [true, false]) {
    const readback = { source: "server", placeCount: count, httpStatus: 200 };
    console.log(`count_${count} | ${zh ? "zh" : "en"} | ${catalogueCountSentence(readback as never, zh)}`);
  }
}
