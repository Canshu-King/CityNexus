// ORD-0553-r2 arm, JourneyInboxWorkbench datetime-local pair.  Runs the shipped conversion
// module (no copy, no re-implementation) through the matrix that decides this cell: the same
// instant read on different devices, an edit made on a foreign device, the Z-form, the legacy
// bare wall, and a negative-offset stamp.  Expected strings are written out in full so a
// regression reads as a diff, not a shrug.
import { localWallToStored, storedToLocalWall, zoneSuffixOf } from "../../frontend/src/lib/inboxScheduleClock.ts";
import { writeFileSync, mkdirSync } from "node:fs";

const cases = [];
const check = (id, got, want) => cases.push({ id, got, want, pass: got === want });

// A: the reading stays byte-identical on a device inside the stored offset (+08:00).
check("A_wall_+08_device", storedToLocalWall("2026-10-09T18:00:00+08:00", 480), "2026-10-09T18:00");
check("A_roundtrip_unchanged", localWallToStored("2026-10-09T18:00", "+08:00", 480), "2026-10-09T18:00:00+08:00");

// B: a UTC device reads the same instant as its own wall clock, and an untouched save lands
// back on the same instant in the stored zone.
check("B_wall_UTC_device", storedToLocalWall("2026-10-09T18:00:00+08:00", 0), "2026-10-09T10:00");
check("B_roundtrip_instant_kept", localWallToStored("2026-10-09T10:00", "+08:00", 0), "2026-10-09T18:00:00+08:00");

// C: an edit typed on the UTC device means 11:30 UTC -- 19:30 in the stored zone.
check("C_edit_foreign_device", localWallToStored("2026-10-09T11:30", "+08:00", 0), "2026-10-09T19:30:00+08:00");

// D: the Z-form keeps its own shape through the loop.
check("D_wall_Z_stored", storedToLocalWall("2026-10-09T10:00:00Z", 480), "2026-10-09T18:00");
check("D_roundtrip_Z", localWallToStored("2026-10-09T18:00", "Z", 480), "2026-10-09T10:00:00Z");

// E: the legacy bare wall keeps the old save shape and shows unchanged on a +08:00 device.
check("E_wall_legacy_bare", storedToLocalWall("2026-10-09T18:00", 480), "2026-10-09T18:00");
check("E_save_legacy_bare", localWallToStored("2026-10-09T18:00", "+08:00", 480), "2026-10-09T18:00:00+08:00");

// F: a negative-offset stamp round-trips without drifting an hour across midnight.
check("F_wall_-05_stored_UTC_device", storedToLocalWall("2026-10-09T18:00:00-05:00", 0), "2026-10-09T23:00");
check("F_roundtrip_-05", localWallToStored("2026-10-09T23:00", "-05:00", 0), "2026-10-09T18:00:00-05:00");

// H: a New York device reads the Beijing-evening instant as early morning, its own wall.
check("H_wall_NY_device", storedToLocalWall("2026-10-09T18:00:00+08:00", -300), "2026-10-09T05:00");

// G: the zone reader recognises every stamp the server has been seen to write.
check("G_zone_Z", zoneSuffixOf("2026-10-09T10:00:00Z"), "Z");
check("G_zone_offset", zoneSuffixOf("2026-10-09T18:00:00+08:00"), "+08:00");
check("G_zone_nocolon", zoneSuffixOf("2026-10-09T18:00:00+0800"), "+08:00");
check("G_zone_bare_falls_back", zoneSuffixOf("2026-10-09T18:00"), "+08:00");

const outDir = new URL("./readouts/", import.meta.url);
mkdirSync(outDir, { recursive: true });
const passed = cases.filter((c) => c.pass).length;
const summary = { total: cases.length, passed, failed: cases.length - passed, cases };
writeFileSync(new URL("./ord0553_inbox_clock_matrix_r1.json", outDir), JSON.stringify(summary, null, 2));
const lines = cases.map((c) => `${c.pass ? "PASS" : "FAIL"} ${c.id}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`);
lines.push(`SUMMARY ${passed}/${cases.length} passed`);
writeFileSync(new URL("./ord0553_inbox_clock_matrix_r1.txt", outDir), lines.join("\n") + "\n");
console.log(lines.join("\n"));
if (passed !== cases.length) process.exit(1);
