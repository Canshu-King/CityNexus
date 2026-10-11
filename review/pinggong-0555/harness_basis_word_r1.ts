import { basisWord } from "./src/lib/sceneClock";
import { dictionaryCopy } from "./src/i18n/LocaleContext";

const L: string[] = [];
L.push("# real-module, real-dictionary readings for basisWord's three rows, both locales");
for (const basis of ["CURSOR", "JOURNEY_START", null]) {
  for (const zh of [true, false]) {
    const locale = zh ? "zh-CN" : "en";
    const got = basisWord(basis, zh);
    L.push(
      "basis=" + String(basis) + " locale=" + locale +
      " text=" + JSON.stringify(got) +
      " bytes=" + String(Buffer.byteLength(got, "utf-8")),
    );
  }
}
L.push("accessor en executionCursor=" +
  JSON.stringify(dictionaryCopy("en", "sceneClock.executionCursor")));
L.push("accessor zh executionCursor=" +
  JSON.stringify(dictionaryCopy("zh-CN", "sceneClock.executionCursor")));
process.stdout.write(L.join("\n") + "\n");
