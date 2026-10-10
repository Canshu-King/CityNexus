// ORD-0558 路牌工甲: calls the copy module's own export for a set of counts, both languages.
const mod = require(process.argv[2]);
const cases = [
  { label: "planned_1_walked_0", activities: [{ id: "a", status: "PLANNED" }] },
  { label: "planned_2_walked_0", activities: [{ id: "a", status: "PLANNED" }, { id: "b", status: "PLANNED" }] },
  { label: "planned_1_walked_1", activities: [{ id: "a", status: "COMPLETED" }] },
  { label: "planned_2_walked_1", activities: [{ id: "a", status: "COMPLETED" }, { id: "b", status: "SKIPPED" }] },
];
for (const item of cases) {
  const p = mod.journeyProgress({
    serverDayCount: 3,
    days: [
      { key: "2031-05-01", activityIds: item.activities.map((a) => a.id) },
      { key: "2031-05-02", activityIds: [] },
      { key: "2031-05-03", activityIds: [] },
    ],
    activities: item.activities,
    currentActivityId: null,
  });
  console.log(JSON.stringify({
    arm: process.argv[3],
    label: item.label,
    planned_total: p.planned_total,
    completed_count: p.completed_count,
    en: mod.progressContractCopy(p, false),
    zh: mod.progressContractCopy(p, true),
  }));
}
