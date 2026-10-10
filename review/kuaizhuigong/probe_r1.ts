import {
  ENTRY_FIELDS,
  entryFieldLabel,
  entryFieldName,
  entryFieldRange,
  entryFieldSuffix,
} from "../../frontend/src/lib/entryLimits";

const langs: Array<[string, boolean | string | null | undefined]> = [
  ["zh-bool", true],
  ["en-bool", false],
  ["zh-str", "zh-CN"],
  ["en-str", "en"],
  ["undef", undefined],
  ["null", null],
];

for (const [lname, lang] of langs) {
  for (const key of Object.keys(ENTRY_FIELDS)) {
    console.log(
      [
        lname,
        key,
        "name=" + JSON.stringify(entryFieldName(key as never, lang)),
        "range=" + JSON.stringify(entryFieldRange(key as never, lang)),
        "suffix=" + JSON.stringify(entryFieldSuffix(key as never, lang)),
        "label=" + JSON.stringify(entryFieldLabel(key as never, lang)),
      ].join(" | "),
    );
  }
}
