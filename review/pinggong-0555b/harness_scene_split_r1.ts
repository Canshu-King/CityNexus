import { evidenceWord } from "./src/lib/sceneClock";
const L: string[] = [];
for (const st of ["FROZEN_WITHOUT_TTL", "EVIDENCE_REFERENCE_INCONSISTENT"]) {
  for (const zh of [true, false]) {
    L.push(st + " locale=" + (zh ? "zh-CN" : "en") + " text=" + JSON.stringify(evidenceWord(st, zh)));
  }
}
process.stdout.write(L.join("\n") + "\n");
