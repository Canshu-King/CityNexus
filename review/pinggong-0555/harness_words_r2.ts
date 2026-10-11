import { basisWord, evidenceWord } from "./src/lib/sceneClock";

const L: string[] = [];
L.push("# real-module, real-dictionary readings for the six routed rows of sceneClock, both locales");
for (const v of ["CURSOR", "JOURNEY_START", null]) {
  for (const zh of [true, false]) {
    L.push("basisWord(" + String(v) + ", " + String(zh) + ") locale=" + (zh ? "zh-CN" : "en") +
      " text=" + JSON.stringify(basisWord(v, zh)));
  }
}
for (const s of ["REFERENCED", "NO_FROZEN_EVIDENCE", "NO_SCENARIO"]) {
  for (const zh of [true, false]) {
    L.push("evidenceWord(" + s + ", " + String(zh) + ") locale=" + (zh ? "zh-CN" : "en") +
      " text=" + JSON.stringify(evidenceWord(s, zh)));
  }
}
process.stdout.write(L.join("\n") + "\n");
