import { englishCountNoun } from "./src/lib/plural";
const L: string[] = [];
L.push("# real helper readings for the one row of aiGenerationRun.ts");
for (const n of [1, 2, 0, 56]) {
  L.push("count=" + n + " after=" + JSON.stringify(`GET /places?city_code=CN1 -> ${n} ${englishCountNoun(n, "place")}`) +
    " before=" + JSON.stringify(`GET /places?city_code=CN1 -> ${n} places`));
}
process.stdout.write(L.join("\n") + "\n");
