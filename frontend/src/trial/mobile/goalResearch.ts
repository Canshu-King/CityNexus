import type { DraftGoalTask, GoalResearchLead } from "../../api/citynexus";

// Historical geocoder records kept location granularity in category. Keep their
// data intact while distinguishing a district/village from a venue in the UI.
const AREA = new Set(["administrative", "city", "town", "village", "county", "boundary", "district", "street", "house", "address", "locality", "suburb", "hamlet", "neighbourhood", "state", "province", "postcode"]);

export function isAreaGoalResearchLead(lead: GoalResearchLead): boolean {
  return lead.location_kind === "AREA" || AREA.has(lead.category.toLowerCase());
}

export function splitGoalResearch(task: DraftGoalTask | null) {
  const areaIds = new Set((task?.research_areas ?? []).map((point) => point.id));
  const combined = new Map<string, GoalResearchLead>();
  for (const lead of [...(task?.research_places ?? []), ...(task?.research_areas ?? [])]) combined.set(lead.id, lead);
  const places: GoalResearchLead[] = [], areas: GoalResearchLead[] = [], unknown: GoalResearchLead[] = [], conflicts: GoalResearchLead[] = [];
  for (const lead of combined.values()) {
    if (lead.region_status === "CONFLICT") conflicts.push(lead);
    else if (lead.region_status !== "MATCHED") unknown.push(lead);
    else if (areaIds.has(lead.id) || isAreaGoalResearchLead(lead)) areas.push(lead);
    else places.push(lead);
  }
  return { places, areas, unknown, conflicts };
}
