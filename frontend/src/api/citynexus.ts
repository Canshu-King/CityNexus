import type { JourneyTwin } from "../contracts/journeyTwin";
import type { ReplanProposal } from "../contracts/replan";
import { fetchWithReadDeadline } from "../lib/readDeadline";
import { OriginResponseUnusableError } from "../lib/failureAttribution";
import { beginNonIdempotentRequest } from "../lib/inFlightWrites";
import { travelerAuthHeaders } from "../lib/travelerSession";

export interface Money {
  amount_minor: number;
  currency: string;
}

export interface Activity {
  id: string;
  sequence_no: number;
  title: string;
  activity_type: string;
  place_id: string | null;
  city_service_id: string | null;
  start_at: string;
  end_at: string;
  travel_from_prev_min: number;
  estimated_cost: Money;
  status: string;
  locked: boolean;
}

export interface PlanVersion {
  id: string;
  journey_id: string;
  version_no: number;
  planning_mode: string;
  status: string;
  source: string;
  parent_plan_version_id: string | null;
  total_cost: Money;
  utility_score: number | null;
  score_breakdown: Record<string, number> | null;
  activities: Activity[];
}

export interface DemoIds {
  traveler_id: string;
  journey_id: string;
  city_code: string;
}

export interface JourneyRecord {
  id: string;
  traveler_id: string;
  title: string;
  city_code: string;
  timezone: string;
  status: string;
}

export interface PlaceRecord {
  id: string;
  name: string;
  category: string;
  city_code: string;
  location: { latitude: number; longitude: number };
  tags: string[];
  external_id: string;
  provider_key: string;
  coordinate_system: string;
  /** Null means the capture never recorded what system the provider handed us --
      which is not the same fact as a stored system, so it stays null. */
  source_coordinate_system: string | null;
  opening_hours: Record<string, unknown>;
  /** `status: UNKNOWN` with a null amount is not a free-price claim. */
  cost_evidence: {
    status?: string;
    amount_minor?: number | null;
    currency?: string;
    [key: string]: unknown;
  };
}

export interface AgentPolicy {
  traveler_id: string;
  mode: "ADVISORY" | "ASSISTED" | "AUTONOMOUS";
  auto_accept_replan: boolean;
  max_auto_replan_cost_delta_minor: number;
  max_auto_loss_minor: number;
  max_auto_schedule_drift_min: number;
  allowed_activity_types: string[];
  allowed_booking_types: string[];
  protected_commitment_levels: string[];
  allow_auto_commitment_management: boolean;
  allow_auto_when_provider_degraded: boolean;
  allow_auto_on_critical_event: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Booking {
  id: string;
  journey_id: string;
  activity_id: string | null;
  commitment_id: string | null;
  provider_key: string;
  external_ref: string | null;
  status: string;
  amount: Money;
}

export interface EventRecord {
  id: string;
  journey_id: string;
  provider_key?: string;
  provenance?: string;
  severity?: string;
  occurred_at: string;
  detected_at?: string;
  event_type: string;
  affected_activity_id: string | null;
  status: string;
  resolved_at?: string | null;
  resolution_reason?: string | null;
  payload?: Record<string, unknown>;
}

export interface AgentFeedEntry {
  id: string;
  timestamp: string;
  event_type: string;
  type: string;
  summary: string;
  actor_type: string;
  actor_id: string | null;
  tool: string | null;
  journey_id: string | null;
  proposal_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  decision: string | null;
  reason_codes: string[];
  trace_id: string;
  source: string;
  facts: Record<string, unknown>;
}

export interface AgentFeedResponse {
  journey_id: string;
  source: string;
  events: AgentFeedEntry[];
}

export interface AgentMission {
  id: string;
  journey_id: string;
  trigger_event_id: string | null;
  user_text: string;
  objective_codes: string[];
  protected_activity_ids: string[];
  mutable_activity_ids: string[];
  resolved_intent: Record<string, unknown>;
  allowed_action_classes: string[];
  unresolved_references: string[];
  compiler: { provider_key: string; model_key: string; confidence: number };
  reasoning_summary: string;
  is_standing: boolean;
  max_cost_delta_minor: number;
  max_loss_minor: number;
  max_schedule_drift_min: number;
  preferences: Record<string, unknown>;
  capabilities?: TravelerCapability[];
  requested_autonomy: "PLAN_ONLY" | "EXECUTE_WITHIN_BOUNDS";
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  failure_reason: string | null;
  mission_plan?: AgentMissionPlan;
  parent_mission_id?: string | null;
  clarification?: JourneyClarification;
}

export interface CollectiveCandidateOption {
  proposal_id: string;
  plan_id?: string;
  status?: string;
  fit_subject_place_ids?: string[];
  fit_subject_tags?: string[];
  fit_subject_basis?: string;
  display_places?: Array<{
    place_id: string;
    name: string;
    category?: string | null;
  }>;
  fairness?: {
    minimum_member_fit?: number;
    unacceptable_member_ids?: string[];
    [key: string]: unknown;
  };
  member_fits?: Record<string, { effective_fit?: number; [key: string]: unknown }>;
  [key: string]: unknown;
}

export interface JourneyClarification {
  clarification_id?: string;
  question?: string;
  option_keys?: string[];
  option_to_strategy?: Record<string, string>;
  preference_dimension?: string;
  decision_epoch?: string;
  kind?: "COLLECTIVE_TRADEOFF" | string;
  status?: string;
  policy?: string;
  required_member_ids?: string[];
  responses?: Record<string, { member_id?: string; proposal_id?: string }>;
  candidate_options?: CollectiveCandidateOption[];
  selected_proposal_id?: string | null;
}

export interface PendingJourneyViewer {
  traveler_id: string;
  member_id: string;
  role: string;
  auth_method: string;
}

export interface PendingCollectiveMember {
  member_id: string;
  traveler_id: string;
  role: string;
  display_name: string | null;
  responded: boolean;
  is_viewer: boolean;
}

export interface PendingCollectiveView {
  status: string | null;
  policy: string | null;
  required_count: number;
  response_count: number;
  required_members: PendingCollectiveMember[];
  viewer_member_id: string | null;
  viewer_has_responded: boolean;
  candidate_options: CollectiveCandidateOption[];
  selected_proposal_id: string | null;
}

export interface PendingContinuationView {
  pending_action_id: string;
  pending_status: string;
  tool_name: string;
  approval_id: string;
  approval_status: string | null;
  required_decision: string | null;
  approved_by: string | null;
  viewer_can_approve: boolean;
}

export interface PendingJourneyMission {
  mission: AgentMission;
  run: AgentRun | null;
  collective?: PendingCollectiveView | null;
  continuation?: PendingContinuationView | null;
}

export interface ClarificationAnswerResponse {
  parent_mission: AgentMission;
  child_mission: AgentMission;
  strategy: string;
  scope: "THIS_JOURNEY" | "REMEMBER_FOR_FUTURE_TRIPS";
  active_plan_unchanged: boolean;
  resume: { required: boolean; mission_id: string };
}

export interface CollectiveClarificationAnswerResponse {
  journey_id: string;
  mission_id: string;
  clarification_id: string;
  status: string;
  responses: Record<string, { member_id?: string; proposal_id?: string }>;
  baseline_preferences_unchanged: boolean;
  traveler_twin_unchanged: boolean;
  child_mission: AgentMission | null;
}

export interface GuardianRun {
  id: string;
  journey_id: string;
  decision: "NO_ACTION" | "WATCH" | "RECOVERY_REQUIRED" | "PREEMPTIVE_RECOVERY";
  status: string;
  action_status: string;
  deduplicated: boolean;
  standing_mission: AgentMission | null;
  trigger_event_id: string | null;
  trigger_kind?: "REACTIVE" | "PREDICTIVE";
  resilience_snapshot_id?: string | null;
  proposal_id: string | null;
  agent_run_id: string | null;
  agent_runtime: { provider_key: string; runtime_identity?: string; model_key: string; status: string } | null;
  tool_steps: AgentRunStep[];
  evidence: {
    observation?: Record<string, unknown>;
    inference?: Record<string, unknown>;
    solver?: Record<string, unknown> | null;
    policy?: Record<string, unknown> | null;
    mutation?: Record<string, unknown> | null;
    prediction?: ResilienceSnapshot | null;
  };
  reasoning_summary: string;
  active_plan_before_id: string | null;
  active_plan_after_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface GuardianStatus {
  journey_id: string;
  standing_mission: AgentMission | null;
  current_active_plan_version_id: string | null;
  latest: GuardianRun | null;
  runs: GuardianRun[];
  readiness?: DepartureReadiness | null;
  autopilot?: {
    enabled: boolean;
    interval_seconds: number;
    signal_provider: string;
    last_pulse_at: string | null;
    last_error: string | null;
    watch?: GuardianWatch | null;
    enrolled_journey_ids?: string[];
    enrollment?: {
      journey_id: string;
      enabled: boolean;
      interval_seconds: number;
      provider_mesh: Record<string, string>;
      last_pulse_at: string | null;
      last_error: string | null;
    } | null;
  };
  signal_fixture?: {
    journey_id: string;
    provider_key: string;
    state: string;
    revision: number;
    payload: Record<string, unknown>;
    updated_at: string;
  } | null;
}

export interface JourneyOperatorTimelineItem {
  at: string;
  label: string;
  kind: string;
}

export interface JourneyIntentProjection {
  id: string;
  source_text: string;
  intent_kind: string;
  scope_kind: string | null;
  scope_start_at: string | null;
  scope_end_at: string | null;
  local_date: string | null;
  target_activity_ids: string[];
  source: string;
  status: string;
  evaluation_state: string;
  created_at: string;
  expired_at?: string | null;
  planned_separation?: {
    kind: "PLANNED_SEPARATION";
    active_plan_version_id: string;
    rendezvous_activity_id: string;
    rendezvous_place_id: string;
    rendezvous_title: string;
    rendezvous_place_name: string;
    scheduled_at?: string | null;
    safety_buffer_min?: number | null;
    resolution_basis: string;
    member_id: string;
    side_destination_authority: "DESCRIPTIVE_ONLY_UNLESS_SEPARATELY_VERIFIED";
  };
  clarification?: { question?: string; status?: string; options?: Array<{ value: string; label: string }> };
}

export interface JourneyOperatorAttention {
  kind: string;
  title: string;
  body: string;
  action_label: string | null;
  action_type: string | null;
  priority: number;
  blocking: boolean;
  semantic_id: string;
  source_ref: Record<string, string>;
  created_at?: string | null;
  options?: Array<{ value: string; label: string }>;
  pending_count: number;
}

export interface JourneyOperatorInboxProjection {
  latest: { id: string; kind: string; headline: string; status: string; impact: string; provenance: string; candidates?: Array<{ id: string; label: string }> } | null;
  pending_count: number;
}

export interface JourneyRealityConflictProjection {
  id: string;
  generation: number;
  status: string;
  title: string;
  body: string;
  choices: Array<{ claim_id: string; label: string }>;
}

export interface JourneyOperatorBrainProjection {
  state: "READY" | "UNCONFIGURED" | "CONFIGURED_UNKNOWN" | "TEMPORARILY_UNAVAILABLE" | "RECOVERING" | "ACTIVE" | "ATTENTION_REQUIRED";
  headline: string;
  configured_runtimes: string[];
  preferred_runtime: string | null;
  last_failure_reason: string | null;
  recovery_resume: {
    pending: boolean;
    status?: string | null;
    recovery_resume_id?: string;
    recovery_epoch_id?: string;
    incident_id?: string | null;
    incident_fingerprint?: string;
    safe_to_resume: boolean;
    blocked_reason?: string;
    failure_classification?: string;
    retry_count?: number;
    next_retry_at?: string | null;
    last_attempt_at?: string | null;
  };
  runtime_candidates?: Array<{
    key: string;
    provider: string;
    model: string | null;
    status: string;
    next_retry_at?: string | null;
  }>;
}

export interface JourneyOperatorCollectiveProjection {
  state: "SINGLE_TRAVELLER" | "WAITING_FOR_MEMBERS" | "MEDIATING" | "COLLECTIVE_READY" | "COLLECTIVE_AUTHORIZED" | "COLLECTIVE_STALE" | "COLLECTIVE_NEEDS_ATTENTION";
  status?: string | null;
  mission_id: string | null;
  clarification_id?: string | null;
  decision_epoch?: string | null;
  required_count: number;
  response_count: number;
  waiting_for_member_count?: number;
  viewer_member_id?: string | null;
  viewer_has_responded: boolean;
  viewer_can_respond?: boolean;
  members: Array<{ member_id: string | null; display_name: string; role: string; responded: boolean; is_viewer: boolean; needs_response?: boolean }>;
  options: Array<{ proposal_id: string | null; label: string; schedule_delta_min?: number | null; cost_delta_minor?: number | null; fit_subject_place_ids?: string[] }>;
  selected_proposal_id?: string | null;
  authority_receipt_id?: string | null;
  mediation_mission_id?: string | null;
  timeline?: JourneyOperatorTimelineItem[];
}

export interface GroupRecoveryCollectiveDecisionProjection {
  mission_id: string;
  state: JourneyOperatorCollectiveProjection["state"] | "RECOVERY_APPLIED";
  required_count: number;
  response_count: number;
  waiting_for_member_count: number;
  viewer_has_responded: boolean;
  viewer_can_apply?: boolean;
  authority_receipt_id: string | null;
  selected_proposal_id?: string | null;
  selected_plan_version_id?: string | null;
  selected_option_label?: string | null;
  reconsent_required?: boolean;
  decision_epoch?: string | null;
  proposal_ids?: string[];
}

export interface JourneyOperatorDiscoveryProjection {
  state: "IDLE" | "DISCOVERY_IN_PROGRESS" | "DISCOVERY_EXHAUSTED" | "DISCOVERY_DEGRADED";
  attempt_count: number;
  max_attempts: number;
  raw_candidate_count: number;
  materialized_place_count: number;
  provider_mode?: string | null;
  runtime_provenance?: string | null;
  query?: string | null;
}

export interface JourneyOperatorOperationsProjection {
  plan_id: string;
  status: "PLANNED" | "WAITING_FOR_APPROVAL" | "EXECUTING" | "PARTIALLY_APPLIED" | "COMPLETED" | "FAILED_SAFE" | "NEEDS_ATTENTION";
  planned_action_count: number;
  completed_action_count: number;
  approval_id?: string | null;
  provider_label?: string | null;
  actions: Array<{
    sequence_no: number;
    kind: string;
    status: string;
    provider_label?: string | null;
    target_type: string;
  }>;
}

export interface JourneyOperatorProjection {
  journey_id: string;
  state: "OFF" | "WATCHING" | "INVESTIGATING" | "WAITING_FOR_APPROVAL" | "APPLYING" | "RECOVERED" | "NEEDS_ATTENTION" | "DEGRADED";
  headline: string;
  enabled: boolean;
  standing_mission_id: string | null;
  autonomy: string | null;
  incident: { id: string; kind: string; severity: string; activity_id: string | null; provenance: string } | null;
  decision: {
    proposal_id: string;
    status: string;
    summary?: string | null;
    cost_delta_minor?: number | null;
    schedule_delta_min?: number | null;
    changes?: Record<string, unknown>;
  } | null;
  approval: {
    required: boolean;
    approval_id: string;
    status: string;
    action_label: string;
    pending_action_id: string;
  } | null;
  brain: JourneyOperatorBrainProjection;
  collective: JourneyOperatorCollectiveProjection;
  discovery: JourneyOperatorDiscoveryProjection;
  operations?: JourneyOperatorOperationsProjection | null;
  flow?: JourneyContinuousFlow | null;
  transit?: JourneyTransitProjection | null;
  group_presence?: JourneyGroupPresenceProjection | null;
  member_side_quest?: MemberSideQuestProjection | null;
  member_place_invitations?: MemberPlaceInvitationProjection | null;
  group_recovery?: GroupRecoveryProjection | null;
  progress?: JourneyProgressProjection;
  ahead?: JourneyAheadProjection | null;
  overnight?: JourneyOvernightProjection | null;
  timeline: JourneyOperatorTimelineItem[];
  operator: { watching: boolean; will_continue_after_approval: boolean };
  intents?: JourneyIntentProjection[];
  attention?: JourneyOperatorAttention | null;
  inbox?: JourneyOperatorInboxProjection;
  reality_conflict?: JourneyRealityConflictProjection | null;
  quiet_mode?: "QUIET" | "NORMAL";
  intent_clarification_result?: { intent_id: string; mission_id: string; outcome: string; agent_status: string };
}

export interface JourneyGroupPresenceProjection {
  state:
    | "MEMBER_IDENTITY_UNAVAILABLE"
    | "SINGLE_TRAVELLER"
    | "MEMBER_LOCATION_MISSING"
    | "GROUP_LOCATION_STALE"
    | "TOGETHER"
    | "GROUP_SPLIT_ADVISORY"
    | "PLANNED_SPLIT_ON_TRACK"
    | "PLANNED_SPLIT_RETURN_RISK"
    | "PLANNED_SPLIT_RETURN_UNKNOWN"
    | "GROUP_LOCATION_UNKNOWN";
  authority: string;
  members: Array<{
    member_id: string;
    display_name: string;
    is_viewer: boolean;
    location_state: "MISSING" | "STALE" | "IMPRECISE" | "UNKNOWN" | "RECENT";
    group_state: "UNKNOWN" | "WITH_GROUP" | "SPLIT_FROM_GROUP";
    age_seconds: number | null;
    authority: string;
    route_eta_minutes: number | null;
    route_eta_provenance: string | null;
    route_eta_state?: string;
    planned_separation?: boolean;
    personal_stop?: {
      planned_personal_stop: true;
      state: "PLANNED" | "ACTIVE_SELF_REPORTED" | "FINISHED_RETURN_UNCONFIRMED" | "RETURN_STARTED_REPORTED";
    };
    return_state?: string | null;
    planned_rendezvous?: { activity_id: string; title: string; place_name: string; scheduled_at?: string | null } | null;
    shared_commitment_risk?: {
      state: string;
      authority?: string;
      next_commitment?: { activity_id?: string; title?: string; scheduled_at?: string; safety_buffer_min?: number } | null;
      slack_after_buffer_min?: number | null;
      route_duration_min?: number;
    } | null;
  }>;
  rendezvous: { activity_id: string; title: string; place_name: string; basis: string } | null;
  rendezvous_state:
    | "RENDEZVOUS_TARGET_UNAVAILABLE"
    | "RENDEZVOUS_TARGET_READY"
    | "RENDEZVOUS_ROUTE_READY";
  viewer_route: { eta_minutes: number | null; provenance: string | null; evidence_state?: string } | null;
  planned_separation?: {
    state: "PLANNED_SPLIT_ON_TRACK" | "PLANNED_SPLIT_RETURN_RISK" | "PLANNED_SPLIT_RETURN_UNKNOWN";
    active_plan_version_id: string;
    rendezvous: { activity_id: string; title: string; place_name: string; scheduled_at?: string | null } | null;
    members: Array<{
      member_id: string;
      display_name: string;
      is_viewer: boolean;
      planned_separation: boolean;
      return_state: string;
      route_provenance: string | null;
      rendezvous: { activity_id: string; title: string; place_name: string; scheduled_at?: string | null } | null;
    }>;
    viewer_next_action: "CONTINUE_PERSONAL_EXCURSION" | "ROUTE_TO_RENDEZVOUS" | "RETURN_SOON" | null;
    shared_plan_changed: false;
  } | null;
  can_guide: boolean;
  meetup_handshake?: {
    owner: {
      id: string | null;
      owner_member_id: string;
      state: "NOT_REPORTED" | "PENDING" | "PEER_ACKNOWLEDGED" | "NOT_CONFIRMED" | "EXPIRED" | "INVALIDATED";
      result: "MEETUP_REPORTED" | "USER_REPORTED_REJOIN_ACKNOWLEDGED" | null;
      planned_split_state: "PLANNED_SPLIT_ENDED" | null;
      reported_at: string | null;
      expires_at: string | null;
      rendezvous: { title: string | null; place_name: string | null };
      responder_display_name: string | null;
      physical_presence_verified: false;
      shared_plan_changed: false;
      can_report: boolean;
      blocked_reason: "R62_REJOIN_REQUIRED" | "NO_PEER_AVAILABLE" | null;
    } | null;
    incoming: Array<{
      id: string;
      owner_display_name: string;
      reported_at: string;
      expires_at: string;
      rendezvous: { title: string; place_name: string };
      physical_presence_verified: false;
    }>;
    resolved: Array<{
      id: string;
      owner_display_name: string;
      responder_display_name: string;
      viewer_acknowledged: boolean;
      rendezvous: { title: string; place_name: string };
      reported_at: string;
      decided_at: string | null;
      state: "PEER_ACKNOWLEDGED";
      result: "USER_REPORTED_REJOIN_ACKNOWLEDGED";
      planned_split_state: "PLANNED_SPLIT_ENDED";
      physical_presence_verified: false;
      shared_plan_changed: false;
    }>;
  } | null;
}

export interface MemberSideQuestProjection {
  id: string;
  state: "DESTINATION_UNRESOLVED" | "READY" | "EN_ROUTE" | "ARRIVED" | "COMPLETED" | "CANCELLED" | "INVALIDATED";
  destination: {
    place_id: string | null;
    title: string;
    authority: "EXACT_KNOWN_PLACE" | "DESCRIPTIVE_ONLY";
  };
  rendezvous: {
    activity_id: string;
    title: string;
    place_name: string;
    scheduled_at: string | null;
  };
  return_state: string;
  return_report?: {
    status: "RETURN_STARTED_REPORTED";
    reported_at: string;
    physical_presence_verified: false;
  } | null;
  shared_plan_changed: false;
  arrival_claim: "MEMBER_REPORTED_NOT_PHYSICAL_PRESENCE_PROOF" | null;
  created_at: string;
  started_at: string | null;
  arrived_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
}

export interface MemberPlaceInvitationPlace {
  place_id: string;
  name: string;
  category: string;
  source: string;
  latitude: number;
  longitude: number;
  coordinate_system: string;
}

export interface MemberPlaceInvitationRendezvous {
  activity_id: string;
  title: string;
  place_name: string;
  scheduled_at: string | null;
}

export interface MemberPlaceInvitationPreview {
  side_quest_id: string;
  place: MemberPlaceInvitationPlace;
  rendezvous: MemberPlaceInvitationRendezvous;
  recipient_count: number;
  audience_snapshot: string;
  expires_in_minutes: number;
  disclosure: string;
}

export interface MemberPlaceInvitationProjection {
  sent: Array<{
    invitation_id: string;
    side_quest_id: string;
    state: "OPEN" | "WITHDRAWN" | "EXPIRED" | "STALE";
    created_at: string;
    expires_at: string;
    place: MemberPlaceInvitationPlace;
    rendezvous: MemberPlaceInvitationRendezvous;
    recipients: Array<{ member_id: string; display_name: string; state: string }>;
  }>;
  incoming: Array<{
    invitation_id: string;
    state: string;
    inviter_display_name: string;
    created_at: string;
    expires_at: string;
    place: MemberPlaceInvitationPlace;
    rendezvous: MemberPlaceInvitationRendezvous;
    can_respond: boolean;
  }>;
}

export type MomentScoutInterest = "ANYTHING" | "COFFEE_FOOD" | "CULTURE" | "NATURE";

export interface MomentScoutCandidate {
  place_id: string;
  name: string;
  category: string;
  straight_line_distance_m: number;
  place_provenance: string;
  opening_state: "UNKNOWN";
  fit_authority: "UNVERIFIED";
}

export interface MomentScoutResult {
  scout_state: "OPTIONS_AVAILABLE" | "NO_GROUNDED_OPTIONS";
  budget_minutes: 15 | 30 | 45;
  interest: MomentScoutInterest;
  observed_at: string;
  scout_context: string;
  evidence_boundary: string;
  rendezvous: {
    activity_id: string;
    title: string;
    place_name: string;
    scheduled_at: string | null;
    time_state: "AVAILABLE" | "UNKNOWN" | "PAST";
    minutes_until: number | null;
  };
  candidates: MomentScoutCandidate[];
}

export interface LiveMomentScoutCandidate {
  candidate_id: string;
  name: string;
  category: string;
  straight_line_distance_m: number;
  osm_type: "node" | "way" | "relation";
  osm_id: string;
  source_url: string;
  opening_state: "UNKNOWN";
  availability_confidence: "UNVERIFIED";
  fit_authority: "UNVERIFIED";
}

export interface LiveMomentScoutResult {
  scout_state:
    | "LIVE_RESULTS"
    | "LIVE_ZERO_RESULTS"
    | "PROVIDER_UNAVAILABLE"
    | "PROVIDER_DISABLED"
    | "LOCATION_UNAVAILABLE";
  budget_minutes: 15 | 30 | 45;
  interest: MomentScoutInterest;
  radius_m: number;
  message: string;
  provider?: string;
  provider_provenance?: string;
  captured_at?: string;
  receipt_id?: string;
  expires_at?: string;
  attribution?: string;
  attribution_url?: string;
  attempts?: Array<{
    endpoint: string;
    answered: boolean;
    http_status: number | null;
    elapsed_ms: number | null;
    elements: number | null;
    failure_class: string | null;
  }>;
  rendezvous?: MomentScoutResult["rendezvous"];
  evidence_boundary?: string;
  candidates: LiveMomentScoutCandidate[];
}

export interface MemberSideQuestRouteCapture {
  duration_min: number;
  distance_m: number | null;
  provider: string;
  provenance: string;
  captured_at: string;
  age_seconds: number;
  mode: string;
  geometry: number[][];
}

export interface MemberSideQuestNavigationResult {
  status: "COMPLETED" | "UNKNOWN";
  destination: { title: string };
  route: MemberSideQuestRouteCapture | null;
  authority: string;
  origin_basis: "AUTHENTICATED_FRESH_MEMBER_LOCATION";
  plan_unchanged: true;
}

export interface MemberSideQuestNavigationTarget {
  kind: "PRIVATE_STOP" | "SHARED_RENDEZVOUS";
  place_id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  coordinate_system: string;
  provenance: {
    provider_key: string;
    external_id: string;
    source_coordinate_system: string | null;
  };
  navigation_available: boolean;
  unavailable_reason: string | null;
}

export interface MemberSideQuestNavigationTargetResult {
  target: MemberSideQuestNavigationTarget;
}

export interface MemberSideQuestFitPreview {
  state: "FITS_WITH_BUFFER" | "TIGHT_RETURN" | "DOES_NOT_FIT" | "UNKNOWN";
  dwell_minutes: number;
  outbound_eta_minutes: number | null;
  return_eta_minutes: number | null;
  recommended_leave_by: string | null;
  rendezvous_scheduled_at: string | null;
  safety_buffer_minutes: number | null;
  provenance: {
    outbound: MemberSideQuestRouteCapture | null;
    return: MemberSideQuestRouteCapture | null;
  };
  origin_basis: {
    outbound: "AUTHENTICATED_FRESH_MEMBER_LOCATION" | null;
    return: "HYPOTHETICAL_SIDE_PLACE";
  };
  authority: string;
  reason_code: string | null;
  plan_unchanged: true;
}

export interface GroupRecoveryProjection {
  state: string;
  headline: string;
  foreground?: boolean;
  incident_key?: string | null;
  failed_proposal_id?: string | null;
  cause_class?: string | null;
  current_recovery_epoch_id?: string | null;
  old_decision?: {
    clarification_id?: string | null;
    authority_receipt_id?: string | null;
    selected_proposal_id?: string | null;
  } | null;
  reground_mission?: {
    id: string;
    status: string;
    recovery_epoch_generation?: number | null;
  } | null;
  reground_result?: {
    state: string;
    collective_classification?: string | null;
    current_proposal_ids?: string[];
    grounded_feasible_proposal_ids?: string[];
    current_options?: Array<{
      proposal_id: string;
      status: string;
      place_names: string[];
      fit_subject_tags: string[];
    }>;
    plan_unchanged: boolean;
  } | null;
  affected_member: {
    member_id: string;
    display_name: string;
    authority: string;
    eta_minutes: number;
    route_provenance: string | null;
    route_evidence_state: string;
  } | null;
  shared_commitment: {
    activity_id: string | null;
    title: string;
    slack_after_buffer_min: number | null;
  } | null;
  options: Array<{ kind: string; mutates_plan: boolean }>;
  decision_authority: string;
  can_request_planning: boolean;
  mission?: { mission_id: string; status: string; failure_reason?: string | null; created_at?: string; run_id?: string | null } | null;
  collective_decision?: GroupRecoveryCollectiveDecisionProjection | null;
  applied?: {
    selected_proposal_id: string;
    before_plan_version_id: string;
    after_plan_version_id: string;
    authority_receipt_id: string;
    decision_epoch?: string | null;
    material_world_epoch?: string | null;
    recovery_epoch_id?: string | null;
    recovery_epoch_generation?: number | null;
    applied_at: string;
    applied_by_member_id?: string | null;
    applied_by_role?: string | null;
  } | null;
  followthrough?: GroupRecoveryFollowThroughProjection | null;
}

export interface GroupRecoveryFollowThroughProjection {
  state: "RECOVERY_APPLIED_REJOIN_PENDING" | "REJOIN_IN_PROGRESS" | "REJOIN_CONFIRMATION_REQUIRED" | "RECOVERY_CLOSED" | string;
  headline: string;
  applied_plan_version_id: string;
  applied_proposal_id?: string | null;
  recovery_epoch_id?: string | null;
  rendezvous: { activity_id: string; title: string; place_id: string; place_name: string } | null;
  members: Array<{
    member_id: string;
    display_name: string;
    role: string;
    is_viewer: boolean;
    state: "REJOINED" | "MOVING" | "WAITING" | "NO_LONGER_REQUIRED";
    confirmed_at?: string | null;
    confirmation_kind?: string | null;
    physical_presence_verified?: boolean;
  }>;
  required_count: number;
  confirmed_count: number;
  viewer_has_confirmed: boolean;
  viewer_can_confirm: boolean;
  membership_reconfirmation_required: boolean;
  evidence_level: "AUTHENTICATED_ACTIVITY_EXECUTION_TRUTH";
  physical_presence_verified: boolean;
  physical_presence_verified_member_count?: number;
  arrival_progress_authority?: "DURABLE_MEMBER_EXECUTION_RECEIPTS" | "ACTIVITY_EXECUTION_HISTORY_FALLBACK" | string;
  plan_unchanged_by_closure: boolean;
  closed_at?: string | null;
}

export interface GroupRecoveryPlanResult {
  status: string;
  reused: boolean;
  mission: { id: string; status: string; failure_reason?: string | null };
  run?: { run_id: string; status?: string; runtime_identity: string; events_url?: string; timeline_url?: string } | null;
  group_recovery: GroupRecoveryProjection;
}

export interface GroupRecoveryApplyResult {
  journey: { id: string; active_plan_version_id: string };
  proposal: { id: string; status: string };
  collective_authority_receipt_id: string;
  group_recovery_apply: {
    result: "APPLIED";
    selected_proposal_id: string;
    authority_receipt_id: string;
    before_plan_version_id: string;
    after_plan_version_id: string;
    decision_epoch?: string | null;
    material_world_epoch?: string | null;
    recovery_epoch_id: string;
    recovery_epoch_generation?: number | null;
    applied_at: string;
    journey_member_id: string;
    member_role: string;
  };
  replayed?: boolean;
}

export interface GroupRendezvousRouteResult {
  status: string;
  outcome?: string | null;
  target: { activity_id: string; title: string; place_name: string };
  route: {
    duration_min?: number | null;
    distance_m?: number | null;
    provider?: string | null;
    provenance?: string | null;
  };
  authority: "ADVISORY_FOREGROUND_LOCATION" | "TRUSTED_MEMBER_LOCATION_ROUTE";
  shared_commitment_risk?: {
    state: string;
    authority?: string;
    next_commitment?: {
      commitment_id?: string;
      activity_id?: string;
      title?: string;
      scheduled_at?: string;
      safety_buffer_min?: number;
    } | null;
    predicted_arrival_at?: string | null;
    slack_after_buffer_min?: number | null;
    route_duration_min?: number;
    basis?: string;
  } | null;
  member_risk_event_id?: string | null;
  guardian_triggered: boolean;
  guardian_deduplicated?: boolean;
  guardian?: Record<string, unknown> | null;
  plan_unchanged: boolean;
}

export interface JourneyTransitProjection {
  state: string;
  activity_id?: string | null;
  activity_title?: string | null;
  activity_status?: string | null;
  location_observation_id?: string | null;
  location_source?: string | null;
  location_age_seconds?: number | null;
  location_accuracy_m?: number | null;
  location_fresh?: boolean;
  route_shape_available?: boolean;
  distance_to_route_m?: number | null;
  deviation_threshold_m?: number | null;
  authoritative?: boolean;
  material?: boolean;
  can_reroute?: boolean;
  route_authority?: string;
  reason?: string;
  active_plan_version_id?: string | null;
  read_only?: boolean;
}

export interface InTransitRerouteResult {
  status: string;
  outcome?: string | null;
  reroute_state: string;
  reused?: boolean;
  active_plan_unchanged: boolean;
  current_activity_status: string;
  provider?: string | null;
  provider_provenance?: string | null;
  provenance_statement?: string;
  result?: {
    duration_min?: number;
    distance_m?: number;
    provider?: string;
    provenance?: string;
    mode?: string;
    geometry?: unknown;
  } | null;
  commitment_risk?: {
    state: string;
    authority?: string;
    next_commitment?: {
      title?: string;
      scheduled_at?: string;
      safety_buffer_min?: number;
    } | null;
    predicted_arrival_at?: string | null;
    slack_after_buffer_min?: number | null;
    future_mobility_basis?: string;
  } | null;
}

export interface JourneyProgressProjection {
  state: string;
  headline: string;
  drift_min: number | null;
  material?: boolean;
  basis?: {
    activity_id: string;
    activity_title?: string;
    milestone: string;
    planned_at: string;
    actual_at: string;
    truth_kind: string;
  } | null;
  next_risk?: {
    commitment_id: string;
    activity_id: string;
    activity_title: string;
    start_at: string;
    slack_before_min: number | null;
    slack_after_min?: number | null;
  } | null;
  read_only?: boolean;
}

export interface JourneyIntentSteeringResponse {
  outcome: string;
  message: string;
  source?: string;
  intent?: JourneyIntentProjection | null;
  proposal_ids?: string[];
}

export interface JourneyContinuousFlow {
  state: string;
  recommended_action: string;
  can_confirm: boolean;
  current: { id: string; title: string; status: string; place_id?: string | null; start_at?: string; end_at?: string } | null;
  next: { id: string; title: string; status: string; place_id?: string | null; start_at?: string; end_at?: string } | null;
  previous_completed?: { id: string; title: string; status: string; place_id?: string | null } | null;
  presence?: { state?: string; reason_code?: string };
  readiness?: { state?: string; must_leave_by?: string | null; target_title?: string | null; recommended_action?: string };
  route?: { state?: string; exact?: boolean; reason_code?: string; duration_min?: number | null; must_leave_by?: string | null; origin_place_id?: string | null; destination_place_id?: string | null };
  notification_key?: string;
  captured_at?: string;
  read_only?: boolean;
}

export interface JourneyAheadProjection {
  state: string;
  headline: string;
  recommended_action: string;
  horizon: { remaining_activity_count: number; lookahead_until: string; bounded_hours?: number };
  top_risk?: { activity_id?: string; title?: string; risk_kind?: string; start_at?: string; starts_at?: string; lead_time_minutes?: number; grounded?: boolean; risk_identity?: string } | null;
  risks?: Array<Record<string, unknown>>;
  snapshot_id?: string | null;
  snapshot_captured_at?: string | null;
  current_activity_id?: string | null;
  read_only?: boolean;
  predictive_only?: boolean;
}

export interface JourneyOvernightProjection {
  state: string;
  reason?: string;
  local_date?: string | null;
  next_local_date?: string | null;
  cycle_key?: string | null;
  learning_summary?: { summary?: string; changed_dimensions?: string[]; learning_count?: number } | null;
  briefing?: {
    state?: string;
    first_activities?: Array<{ id: string; title: string; status: string; start_at: string }>;
    route?: { state?: string; exact?: boolean; duration_min?: number | null; must_leave_by?: string | null };
    readiness?: { state?: string; route_status?: string; must_leave_by?: string | null };
    future_risk?: { title?: string; lead_time_minutes?: number; grounded?: boolean } | null;
  } | null;
  read_only?: boolean;
}

export interface ExecutionTransitionPayload {
  truth_kind: "OPERATOR_CONFIRMED_EXECUTION";
  operator_confirmed: true;
}

export interface DepartureReadiness {
  state: "READY" | "READY_WITH_UNCERTAINTY" | "ACTION_NEEDED" | "BLOCKED" | "NOT_DUE" | "COMPLETE" | "UNKNOWN";
  target_activity_id: string | null;
  target_title: string | null;
  starts_at: string | null;
  minutes_until_start: number | null;
  must_leave_by: string | null;
  must_leave_by_absent_reason?: string | null;
  safety_buffer_minutes?: number | null;
  launch_origin?: { source?: string | null; name?: string | null; captured_at?: string | null } | null;
  launch_edge?: { state?: string | null; duration_min?: number | null; captured_at?: string | null; provider?: string | null } | null;
  blocking_reasons: string[];
  warning_reasons: string[];
  checks: Record<string, string | null>;
  recommended_action: string;
  authority: string;
  captured_at?: string;
}

export interface GuardianWatch {
  watch_state: "QUIET" | "DAY_AHEAD" | "TODAY" | "APPROACHING" | "INCIDENT_ACTIVE";
  reason_code: string;
  configured_interval_seconds: number;
  effective_interval_seconds: number;
  next_due_at: string | null;
  next_activity_id: string | null;
  next_activity_start_at: string | null;
  next_activity_horizon_seconds: number | null;
  open_material_event_ids: string[];
  event_newer_than_last_pulse: boolean;
  journey_phase: string;
  phase_reason_code: string;
  phase_authority: string;
  current_activity_id: string | null;
  monitored_activity_ids: string[];
  next_move?: {
    copy: string;
    authority: string;
    journey_phase: string | null;
    phase_authority: string | null;
    presence?: {
      state?: string;
      authority?: string;
      distance_to_target_m?: number | null;
      age_seconds?: number | null;
      accuracy_m?: number | null;
      arrival_transition_allowed?: boolean;
    };
    venue_readiness?: { state?: string; activity_id?: string | null };
    route_evidence?: { state?: string; provider?: string | null; provenance?: string | null; degraded?: boolean };
  } | null;
}

export interface ResilienceSnapshot {
  id: string;
  journey_id: string;
  score: number;
  risk_score: number;
  status: string;
  captured_at: string;
  expires_at: string | null;
  components: Record<string, number>;
  activity_risks: Array<Record<string, unknown>>;
  commitment_buffers: Array<Record<string, unknown>>;
  dominant_failure_modes: string[];
  preventive_recommendation: Record<string, unknown>;
  evidence_provenance: Array<Record<string, unknown>>;
  fingerprint: string;
}

export interface CounterfactualSimulation {
  id: string;
  journey_id: string;
  snapshot_id: string | null;
  scenario_key: string;
  scenario_type: string;
  parameters: Record<string, unknown>;
  feasible: boolean;
  c4_preserved: boolean;
  cost_delta_minor: number;
  schedule_drift_min: number;
  plan_changes: Array<Record<string, unknown>>;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface ProviderMeshResponse {
  journey_id: string;
  providers: Array<{
    provider_key: string;
    observation_type: string;
    state: string;
    provenance: string;
    captured_at: string;
    expires_at: string | null;
  }>;
  real_place_candidates: Array<{
    id: string;
    provider_key: string;
    external_id: string;
    name: string;
    category: string;
    location: { latitude: number; longitude: number };
    tags: string[];
    captured_at: string;
    expires_at: string | null;
    materialized_place_id: string | null;
    status: string;
    opening_hours: Record<string, unknown>;
    cost_evidence: Record<string, unknown>;
    facts_source: "CANONICAL_PLACE" | "CAPTURED_CANDIDATE";
    facts_updated_at: string;
  }>;
}

export interface AgentRunStep {
  id?: string;
  sequence_no: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  decision: string | null;
  status: string;
  created_at?: string;
  completed_at?: string;
}

export interface AgentRunOutcome {
  status: string;
  reason_code?: string;
  user_summary?: string;
  recommended_action?: string;
  [key: string]: unknown;
}

export interface AgentRun {
  run_id: string | null;
  mission_id: string;
  journey_id?: string;
  provider_key: string;
  runtime_identity?: string;
  model_key: string;
  status: string;
  completion_contract?: {
    kind?: string;
    reason_code?: string;
    source?: string;
    [key: string]: unknown;
  } | null;
  outcome: string | AgentRunOutcome | null;
  failure_reason: string | null;
  mission_status?: string | null;
  created_at?: string;
  started_at?: string;
  completed_at?: string | null;
  mission?: AgentMission;
  tool_steps: AgentRunStep[];
  mission_plan?: AgentMissionPlan;
  native_events_url?: string;
  events_url?: string;
  timeline_url?: string;
  initial_events?: NativeRuntimeEvent[];
  protected_commitments?: Array<Record<string, unknown>>;
}

export interface AgentMissionPlanStep {
  id: string;
  operation: string;
  tool_name: string | null;
  status: string;
  requires_authority: boolean;
}

export interface AgentMissionPlan {
  version: string;
  autonomy: string;
  steps: AgentMissionPlanStep[];
  protected_activity_ids: string[];
  allowed_tools: string[];
  read_only_tools?: string[];
  approval_required_tools?: string[];
  authority: string;
}

export interface NativeRuntimeEvent {
  event_type: string;
  run_id: string | null;
  event_id?: string | null;
  sequence?: number | null;
  tool_name: string | null;
  friendly_label: string;
  status: string;
  timestamp?: string | number | null;
  duration_ms?: number | null;
  result_summary?: Record<string, unknown> | string | null;
  policy_decision?: string | null;
  raw_event_type?: string;
  source?: string;
  approval_id?: string;
  proposal_id?: string;
  mission_id?: string;
  approval_status?: string;
  approval_method?: string | null;
}

export interface AgentCommandResponse {
  mission: AgentMission;
  event_id: string | null;
  run: AgentRun;
}

/* ORD-0387: the four words `backend/app/agent/ai_availability.py` produces and nowhere else.
   `(string & {})` keeps them as the listed choices without claiming a fifth can never arrive --
   an unlisted word must fall through to "the server said something we do not name", not be
   silently typed as known. */
export type AiStateWord =
  | "CONFIGURED_UNVERIFIED"
  | "NOT_CONFIGURED"
  | "DISABLED_BY_OPS"
  | "PROVIDER_REFUSED";

export interface AgentRuntimeStatus {
  runtime_identity:
    | "HERMES_NATIVE_MCP"
    | "NATIVE_DEEPSEEK_TOOL_LOOP"
    | "HERMES_COMPAT_ENDPOINT"
    | "NOT_CONFIGURED"
    | string;
  native_binary_detected: boolean;
  native_mcp_proven: boolean;
  mcp_server: string;
  deepseek_configured: boolean;
  hermes_compat_configured: boolean;
  /* ORD-0359 keeps this out of the contract's `required`, so absence is a real answer here:
     an older server, or one that never learned the field, and this client must not invent one. */
  ai_state?: AiStateWord | (string & {});
  hermes_native_gateway?: {
    configured: boolean;
    reachable: boolean;
    ready?: boolean;
    runs: boolean;
    events: boolean;
    approval: boolean;
    profile?: string;
  };
}

export interface CopilotResponse {
  message: string;
  mode: "AI" | "FALLBACK";
  verified_context_used: boolean;
  intent: {
    name: string;
    confidence: number;
    reason: string;
    entities: Record<string, unknown>;
    provider: string;
    mode: "AI" | "FALLBACK";
    semantic_envelope?: {
      intent: string;
      assertion_status: string;
      effective_time: string;
      event_type: string;
      requested_action: string;
      confidence: number;
      reasoning_summary: string;
      entities: Record<string, unknown>;
      constraints: Array<Record<string, unknown>>;
      capabilities?: TravelerCapability[];
      route_intent?: string;
      server_action?: string;
      create_event?: boolean;
      verify_evidence?: boolean;
    };
  };
  action: { type: string } | null;
  what_if: {
    simulation_only: boolean;
    status: string;
    feasibility: string;
    before: Record<string, unknown>;
    after: Record<string, unknown>;
    deltas: Record<string, number | null>;
    affected_activities: Array<Record<string, unknown>>;
    protected_commitments: { count: number; preserved: boolean; ids: string[] };
    proposed_changes: Array<Record<string, unknown>>;
    provenance: Record<string, unknown>;
    explanation: string;
    next_action: string | null;
  } | null;
  event: {
    id: string;
    event_type: string;
    status: string;
    affected_activity_id?: string | null;
    occurred_at?: string;
    target_resolution?: string;
    requires_review?: boolean;
  } | null;
  verification?: {
    status: string;
    query?: string;
    event_created: boolean;
    observations: Array<Record<string, unknown>>;
  } | null;
  agent_run?: {
    run_id: string;
    status: string;
    runtime_identity: string;
    provider_key: string;
    events_url?: string;
    timeline_url?: string;
    mission_id?: string;
    model_key?: string;
    mission_plan?: AgentMissionPlan;
    initial_events?: NativeRuntimeEvent[];
    protected_commitments?: Array<Record<string, unknown>>;
  } | null;
  protected_commitments: Array<Record<string, unknown>>;
  evidence: Record<string, unknown>;
  recommendations: Array<Record<string, unknown>>;
}

export interface ReflectSummary {
  journey_id: string;
  status: string;
  completed: boolean;
  timeline: {
    actual_time_available: boolean;
    actual_time_note: string;
    activities: Array<{
      activity_id: string;
      title: string;
      activity_type: string;
      planned_start_at: string;
      planned_end_at: string;
      observed_status: string;
      actual_start_at: string | null;
      actual_end_at: string | null;
    }>;
  };
  replan_history: Array<Record<string, unknown>>;
  agent_action_history: AgentFeedEntry[];
  provider_disruptions: Array<Record<string, unknown>>;
  cost_summary: {
    currency: string;
    initial_estimated_minor: number;
    final_estimated_minor: number;
    estimated_delta_minor: number;
    confirmed_booking_minor: number;
    captured_payment_minor: number;
  };
  plan_version_chain: Array<Record<string, unknown>>;
  preference_feedback_hook: {
    available: boolean;
    traveler_id: string;
    endpoint: string;
    mode: string;
  };
  traveler_twin: TravelerTwinEvidence;
}

export interface TravelerTwinEvidence {
  traveler_id: string;
  explicit_preferences: Array<Record<string, unknown>>;
  explicit_capabilities?: TravelerCapability[];
  capability_summary?: {
    items: TravelerCapability[];
    hard: TravelerCapability[];
    strong: TravelerCapability[];
    soft: TravelerCapability[];
    unknown_accessibility_is_not_accessible?: boolean;
  };
  learned_soft_preferences: Array<{
    dimension?: string;
    direction?: string;
    strength?: number;
    confidence?: number;
    evidence_count?: number;
    explanation?: string;
    journey_ids?: string[];
    last_evidence_at?: string;
    expires_at?: string | null;
    conflict?: Record<string, unknown> | null;
  }>;
  confidence: number;
  evidence_count: number;
  conflicts: Array<Record<string, unknown>>;
  provenance: Record<string, unknown>;
  updated_at: string;
}

export interface TravelerCapability {
  id?: string;
  traveler_id?: string;
  journey_id?: string | null;
  code: string;
  class?: string;
  severity: "HARD" | "STRONG" | "SOFT";
  params: Record<string, unknown>;
  scope: "TRAVELER" | "JOURNEY";
  source?: string;
  provenance?: string;
  explicit?: boolean;
  confirmed?: boolean;
  active?: boolean;
  confirmed_at?: string | null;
}

export interface TravelerCapabilityResponse {
  traveler_id?: string;
  journey_id?: string;
  capabilities: TravelerCapability[];
  summary: TravelerTwinEvidence["capability_summary"];
  traveler_twin?: TravelerTwinEvidence;
}

export interface AgentToolResponse {
  tool: string;
  decision: "ALLOW_AUTO" | "REQUIRE_CONFIRMATION" | "REQUIRE_STEP_UP" | "DENY";
  reason_codes: string[];
  policy_version?: number;
  request_id?: string;
  executed?: boolean;
  user_confirmed?: boolean;
  approval_id?: string;
  approval_status?: "PENDING" | "APPROVED" | "CONSUMED" | "EXPIRED" | "REVOKED";
  approval_method?: "USER_CONFIRMATION" | "STEP_UP" | "WEBAUTHN" | null;
  expires_at?: string;
  facts?: Record<string, unknown>;
  result?: AcceptReplanResponse;
  proposal_id?: string;
  status?: string;
}

export interface AgentApprovalResponse {
  approval_id: string;
  journey_id: string;
  action: string;
  target_type: string;
  target_id: string;
  status: "PENDING" | "APPROVED" | "CONSUMED" | "EXPIRED" | "REVOKED";
  required_decision?: string;
  approval_method: "USER_CONFIRMATION" | "STEP_UP" | "WEBAUTHN" | null;
  approved_by?: string | null;
  created_at: string;
  expires_at: string;
  approved_at: string | null;
  consumed_at: string | null;
  continuation?: {
    status: string;
    pending_action_id?: string;
    run_id?: string;
    mission_id?: string;
    replayed?: boolean;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface RouteFeature {
  type: "Feature";
  properties: {
    provider: string;
    provider_backed: boolean;
    fallback: boolean;
    fallback_reason: string | null;
    plan_version_id: string;
  };
  geometry: { type: "LineString"; coordinates: [number, number][] };
}

export interface RouteEvidence {
  journey_id: string;
  proposal_id: string | null;
  snapshot_id: string | null;
  provider: string;
  frozen: boolean;
  old_route: RouteFeature;
  new_route: RouteFeature | null;
  disruption_scope?: {
    type: "Feature";
    properties: Record<string, unknown>;
    geometry: { type: "Polygon" | "MultiPolygon"; coordinates: unknown };
  } | null;
  impacted_activity_ids?: string[];
  markers: {
    type: "FeatureCollection";
    features: Array<{
      type: "Feature";
      properties: { role: string; title: string; activity_id: string | null };
      geometry: { type: "Point"; coordinates: [number, number] };
    }>;
  };
  fallback: boolean;
  fallback_reason: string | null;
  source: string;
}

export interface AcceptReplanResponse {
  journey: {
    id: string;
    status: string;
    active_plan_version_id: string | null;
    current_activity_id: string | null;
  };
  proposal: ReplanProposal;
  twin: JourneyTwin;
}

export class CityNexusApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown,
    message: string,
  ) {
    super(message);
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const releaseInFlight = beginNonIdempotentRequest(init?.method);
  try {
    return await requestJsonInner<T>(path, init);
  } finally {
    releaseInFlight();
  }
}

async function requestJsonInner<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithReadDeadline("/api/v1" + path, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const text = await response.text();
  /* ORD-0263: this channel used to hand the undecodable answer straight back as data (`body = text`),
     so nothing threw, nothing was classified and the screen simply said nothing.  Only a *failed*
     parse or a 2xx with no bytes at all counts -- a legitimate bare JSON string or a 204 stays as it
     was, because neither of those is this defect. */
  const emptyAnswer = text.trim() === "";
  let body: unknown = null;
  let parseFailed = false;
  if (!emptyAnswer) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
      parseFailed = true;
    }
  }
  if (!response.ok) {
    throw new CityNexusApiError(
      response.status,
      body,
      "CityNexus API " + response.status + ": " + path,
    );
  }
  if (parseFailed || (emptyAnswer && response.status !== 204)) {
    const contentType = response.headers.get("content-type");
    throw new OriginResponseUnusableError(
      response.status,
      contentType,
      emptyAnswer ? "empty" : (contentType ?? "").includes("html") ? "html" : "not_json",
    );
  }
  return body as T;
}

/** `GET /destinations/capability` -- the server's structural verdict about a destination. */
export interface DestinationCapability {
  query: string;
  /** READY / HYDRATABLE / UNAVAILABLE, decided server-side. */
  capability: string;
  reason_code: string;
  recommended_action: string;
  destination_state: string;
  destination_resolution: string;
  retryable: boolean;
  /** Present only for AMBIGUOUS: what the traveller has to choose between. */
  candidates?: Array<Record<string, unknown>>;
  matched_label?: string | null;
  canonical_destination_id?: string | null;
  /** The traveller's exact raw words, kept separately from the normalised resolver query. */
  pending_destination_label?: string | null;
  resolver_query_normalized?: string | null;
  coverage: Record<string, string>;
  missing_categories: string[];
  place_count: number;
  /** Absent unless something actually looked -- a default `OK` would be a fabricated measurement. */
  provider_status?: Array<{ provider?: string; status?: string; message?: string }>;
}

/** `POST/GET /catalog-hydrations[/{id}]` -- the job's own record.  No percentage by design. */
export interface CatalogHydrationOperation {
  operation_id: string;
  status: string;
  recorded_status: string;
  /** The stage the worker is genuinely inside; one of the server's PHASES. */
  phase: string;
  outcome: string | null;
  terminal: boolean;
  elapsed_ms: number;
  retry_after_ms: number;
  retryable: boolean;
  reused: boolean;
  canonical_destination_id: string | null;
  pending_destination_label: string | null;
  resolver_query_normalized: string | null;
  destination_state: string;
  result: Record<string, unknown> | null;
  /** The server's own error object; its `message_key` still has to be rendered as words. */
  error: Record<string, unknown> | null;
  journey_id: string | null;
  submitted_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  abandon_requested_at?: string | null;
}

export const cityNexusApi = {
  resetDemo(): Promise<DemoIds> {
    return requestJson<DemoIds>("/demo/reset", { method: "POST" });
  },

  /* ORD-0193: the destination-preparation surface.  These mirror the server's own projections --
     `GET /destinations/capability` (anywhere_capability.evaluate_capability) and the three
     catalog-hydration calls -- so the screen shows what the server decided rather than guessing a
     verdict from a place count.  There is deliberately no progress percentage: the payload carries
     `phase` and `elapsed_ms` and the backend refuses to invent a denominator. */
  getDestinationCapability(query: string): Promise<DestinationCapability> {
    return requestJson<DestinationCapability>(
      "/destinations/capability?query=" + encodeURIComponent(query),
    );
  },

  startCatalogHydration(
    query: string,
    options: { journeyId?: string | null; requestedCategories?: string[] } = {},
  ): Promise<CatalogHydrationOperation> {
    return requestJson<CatalogHydrationOperation>("/catalog-hydrations", {
      method: "POST",
      body: JSON.stringify({
        query,
        journey_id: options.journeyId ?? null,
        requested_categories: options.requestedCategories,
      }),
    });
  },

  getCatalogHydration(operationId: string): Promise<CatalogHydrationOperation> {
    return requestJson<CatalogHydrationOperation>(
      "/catalog-hydrations/" + encodeURIComponent(operationId),
    );
  },

  abandonCatalogHydration(operationId: string): Promise<CatalogHydrationOperation> {
    return requestJson<CatalogHydrationOperation>(
      "/catalog-hydrations/" + encodeURIComponent(operationId) + "/abandon",
      { method: "POST" },
    );
  },

  getJourney(journeyId: string): Promise<JourneyRecord> {
    return requestJson<JourneyRecord>("/journeys/" + journeyId);
  },

  listPlaces(cityCode: string): Promise<PlaceRecord[]> {
    return requestJson<PlaceRecord[]>("/places?city_code=" + encodeURIComponent(cityCode));
  },

  listEvents(journeyId: string): Promise<EventRecord[]> {
    return requestJson<EventRecord[]>("/journeys/" + journeyId + "/events");
  },

  getAgentPolicy(travelerId: string): Promise<AgentPolicy> {
    return requestJson<AgentPolicy>("/travelers/" + travelerId + "/agent-policy");
  },

  updateAgentPolicy(
    travelerId: string,
    policy: Pick<
      AgentPolicy,
      | "mode"
      | "auto_accept_replan"
      | "max_auto_replan_cost_delta_minor"
      | "max_auto_loss_minor"
      | "max_auto_schedule_drift_min"
      | "allowed_activity_types"
      | "allowed_booking_types"
      | "protected_commitment_levels"
      | "allow_auto_commitment_management"
      | "allow_auto_when_provider_degraded"
      | "allow_auto_on_critical_event"
    >,
  ): Promise<AgentPolicy> {
    return requestJson<AgentPolicy>("/travelers/" + travelerId + "/agent-policy", {
      method: "PUT",
      body: JSON.stringify(policy),
    });
  },

  generatePlans(journeyId: string, candidateCount = 1): Promise<PlanVersion[]> {
    return requestJson<PlanVersion[]>("/journeys/" + journeyId + "/plans/generate", {
      method: "POST",
      body: JSON.stringify({ candidate_count: candidateCount }),
    });
  },

  selectPlan(journeyId: string, planId: string): Promise<unknown> {
    return requestJson("/journeys/" + journeyId + "/plans/" + planId + "/select", {
      method: "POST",
    });
  },

  getPlan(planId: string): Promise<PlanVersion> {
    return requestJson<PlanVersion>("/plans/" + planId);
  },

  createBooking(journeyId: string, activityId: string): Promise<Booking> {
    return requestJson<Booking>("/journeys/" + journeyId + "/bookings", {
      method: "POST",
      body: JSON.stringify({ activity_id: activityId }),
    });
  },

  captureBooking(journeyId: string, booking: Booking, idempotencyKey: string): Promise<unknown> {
    return requestJson("/journeys/" + journeyId + "/transactions", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        booking_id: booking.id,
        transaction_type: "CAPTURE",
        amount: booking.amount,
      }),
    });
  },

  startJourney(journeyId: string): Promise<JourneyTwin> {
    return requestJson<JourneyTwin>("/journeys/" + journeyId + "/start", { method: "POST" });
  },

  completeActivity(journeyId: string, activityId: string, payload?: ExecutionTransitionPayload): Promise<JourneyTwin> {
    return requestJson<JourneyTwin>(
      "/journeys/" + journeyId + "/activities/" + activityId + "/complete",
      { method: "POST", headers: travelerAuthHeaders(), body: payload ? JSON.stringify(payload) : undefined },
    );
  },

  transitionActivity(
    journeyId: string,
    activityId: string,
    transition: "depart" | "arrive" | "begin" | "complete",
  ): Promise<JourneyTwin> {
    return requestJson<JourneyTwin>(
      "/journeys/" + journeyId + "/activities/" + activityId + "/" + transition,
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({ truth_kind: "OPERATOR_CONFIRMED_EXECUTION", operator_confirmed: true }),
      },
    );
  },

  getTwin(journeyId: string, now?: string): Promise<JourneyTwin> {
    const suffix = now ? "?now=" + encodeURIComponent(now) : "";
    return requestJson<JourneyTwin>("/journeys/" + journeyId + "/twin" + suffix);
  },

  getAgentFeed(journeyId: string, limit = 100): Promise<AgentFeedResponse> {
    return requestJson<AgentFeedResponse>(
      "/journeys/" + journeyId + "/agent-feed?limit=" + encodeURIComponent(String(limit)),
    );
  },

  getAgentRuntimeStatus(): Promise<AgentRuntimeStatus> {
    return requestJson<AgentRuntimeStatus>("/agent/runtime-status");
  },

  runAgentCommand(
    journeyId: string,
    command: string,
    requestedAutonomy: "PLAN_ONLY" | "EXECUTE_WITHIN_BOUNDS" = "EXECUTE_WITHIN_BOUNDS",
  ): Promise<AgentCommandResponse> {
    return requestJson<AgentCommandResponse>("/journeys/" + journeyId + "/agent/commands", {
      method: "POST",
      body: JSON.stringify({ command, requested_autonomy: requestedAutonomy }),
    });
  },

  steerJourneyIntent(journeyId: string, command: string): Promise<JourneyIntentSteeringResponse> {
    return requestJson<JourneyIntentSteeringResponse>("/journeys/" + journeyId + "/agent/commands", {
      method: "POST",
      headers: travelerAuthHeaders(),
      body: JSON.stringify({ command, requested_autonomy: "PLAN_ONLY" }),
    });
  },

  sendCopilotMessage(
    journeyId: string,
    message: string,
    locale: "zh" | "en",
  ): Promise<CopilotResponse> {
    return requestJson<CopilotResponse>("/journeys/" + journeyId + "/copilot/messages", {
      method: "POST",
      body: JSON.stringify({ message, locale }),
    });
  },

  getNativeHermesRun(journeyId: string, runId: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(
      "/journeys/" + journeyId + "/agent/hermes/runs/" + encodeURIComponent(runId),
    );
  },

  getNativeHermesTimeline(journeyId: string, runId: string): Promise<{
    run_id: string;
    journey_id: string;
    runtime_identity: string;
    events: NativeRuntimeEvent[];
    observability?: {
      run_id: string;
      runtime_identity: string;
      current_mission: string | null;
      tool_count: number;
      current_tool: string | null;
      completion_status: string;
      gateway_decision: string | null;
      guardian_decision: string | null;
      total_duration_ms: number;
    };
  }> {
    return requestJson(
      "/journeys/" + journeyId + "/agent/hermes/runs/" + encodeURIComponent(runId) + "/timeline",
    );
  },

  stopNativeHermesRun(journeyId: string, runId: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(
      "/journeys/" + journeyId + "/agent/hermes/runs/" + encodeURIComponent(runId) + "/stop",
      { method: "POST" },
    );
  },

  getAgentRun(journeyId: string, runId: string): Promise<AgentRun> {
    return requestJson<AgentRun>(
      "/journeys/" + journeyId + "/agent/runs/" + runId,
    );
  },

  getPendingJourneyMissions(journeyId: string): Promise<{
    journey_id: string;
    viewer: PendingJourneyViewer | null;
    items: PendingJourneyMission[];
  }> {
    return requestJson("/journeys/" + journeyId + "/missions/pending", {
      headers: travelerAuthHeaders(),
    });
  },

  answerJourneyClarification(
    journeyId: string,
    missionId: string,
    clarificationId: string,
    optionKey: string,
  ): Promise<ClarificationAnswerResponse> {
    return requestJson("/journeys/" + journeyId + "/missions/" + missionId + "/clarification", {
      method: "POST",
      body: JSON.stringify({ clarification_id: clarificationId, option_key: optionKey, scope: "THIS_JOURNEY" }),
    });
  },

  answerCollectiveClarification(
    journeyId: string,
    missionId: string,
    memberId: string,
    clarificationId: string,
    proposalId: string,
  ): Promise<CollectiveClarificationAnswerResponse> {
    return requestJson(
      "/journeys/" + journeyId + "/missions/" + missionId
        + "/collective-clarification/" + encodeURIComponent(memberId),
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({ clarification_id: clarificationId, proposal_id: proposalId }),
      },
    );
  },

  resumeJourneyMission(journeyId: string, missionId: string): Promise<{
    mission: AgentMission;
    run: AgentRun;
  }> {
    return requestJson("/journeys/" + journeyId + "/missions/" + missionId + "/resume", { method: "POST" });
  },

  putGuardianMission(
    journeyId: string,
    command: string,
    requestedAutonomy: "PLAN_ONLY" | "EXECUTE_WITHIN_BOUNDS" = "EXECUTE_WITHIN_BOUNDS",
  ): Promise<AgentMission> {
    return requestJson<AgentMission>("/journeys/" + journeyId + "/guardian/mission", {
      method: "PUT",
      body: JSON.stringify({ command, requested_autonomy: requestedAutonomy }),
    });
  },

  scanGuardian(journeyId: string): Promise<GuardianRun> {
    return requestJson<GuardianRun>("/journeys/" + journeyId + "/guardian/scan", {
      method: "POST",
    });
  },

  getGuardianStatus(journeyId: string): Promise<GuardianStatus> {
    return requestJson<GuardianStatus>("/journeys/" + journeyId + "/guardian/status");
  },

  getGuardianReadiness(journeyId: string): Promise<DepartureReadiness> {
    return requestJson<DepartureReadiness>("/journeys/" + journeyId + "/guardian/readiness");
  },

  getResilience(journeyId: string): Promise<ResilienceSnapshot> {
    return requestJson<ResilienceSnapshot>("/journeys/" + journeyId + "/resilience");
  },

  refreshResilience(
    journeyId: string,
    mode: "replay" | "live" = "replay",
  ): Promise<{
    snapshot: ResilienceSnapshot;
    counterfactuals: CounterfactualSimulation[];
    discovery: Record<string, unknown> | null;
  }> {
    return requestJson("/journeys/" + journeyId + "/resilience/refresh", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
  },

  getProviderMesh(journeyId: string): Promise<ProviderMeshResponse> {
    return requestJson<ProviderMeshResponse>("/journeys/" + journeyId + "/provider-mesh");
  },

  discoverRealCity(
    journeyId: string,
    query = "indoor",
    mode: "replay" | "captured_replay" | "live" = "captured_replay",
  ): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>("/journeys/" + journeyId + "/real-city/discover", {
      method: "POST",
      body: JSON.stringify({ query, mode, limit: 8, radius_m: 2500 }),
    });
  },

  startGuardianAutopilot(journeyId: string, intervalSeconds = 0.5): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(
      "/journeys/" + journeyId + "/guardian/autopilot/start",
      {
        method: "POST",
        body: JSON.stringify({ interval_seconds: intervalSeconds }),
      },
    );
  },

  stopGuardianAutopilot(journeyId: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(
      "/journeys/" + journeyId + "/guardian/autopilot/stop",
      { method: "POST" },
    );
  },

  getJourneyOperator(journeyId: string): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>("/journeys/" + journeyId + "/operator", {
      headers: travelerAuthHeaders(),
    });
  },

  createMemberSideQuest(
    journeyId: string,
    destination: { destinationText?: string; placeId?: string },
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-side-quests",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          destination_text: destination.destinationText,
          place_id: destination.placeId,
        }),
      },
    );
  },

  getMemberPlaceInvitationPreview(
    journeyId: string,
    sideQuestId: string,
  ): Promise<MemberPlaceInvitationPreview> {
    return requestJson<MemberPlaceInvitationPreview>(
      "/journeys/" + journeyId + "/member-side-quests/" + sideQuestId + "/place-invitation-preview",
      { headers: travelerAuthHeaders() },
    );
  },

  createMemberPlaceInvitation(
    journeyId: string,
    sideQuestId: string,
    audienceSnapshot: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-side-quests/" + sideQuestId + "/place-invitations",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          confirm_public_place_sharing: true,
          audience_snapshot: audienceSnapshot,
        }),
      },
    );
  },

  respondToMemberPlaceInvitation(
    journeyId: string,
    invitationId: string,
    decision: "ACCEPT" | "DECLINE",
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-place-invitations/" + invitationId + "/respond",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          decision,
          confirm_exact_public_place: decision === "ACCEPT" ? true : undefined,
        }),
      },
    );
  },

  withdrawMemberPlaceInvitation(
    journeyId: string,
    invitationId: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-place-invitations/" + invitationId + "/withdraw",
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  scoutMemberMoment(
    journeyId: string,
    locationObservationId: string,
    budgetMinutes: 15 | 30 | 45,
    interest: MomentScoutInterest,
  ): Promise<MomentScoutResult> {
    return requestJson<MomentScoutResult>(
      "/journeys/" + journeyId + "/moment-scout",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          location_observation_id: locationObservationId,
          budget_minutes: budgetMinutes,
          interest,
        }),
      },
    );
  },

  scoutLiveMemberMoment(
    journeyId: string,
    locationObservationId: string,
    budgetMinutes: 15 | 30 | 45,
    interest: MomentScoutInterest,
    radiusM = 1200,
  ): Promise<LiveMomentScoutResult> {
    return requestJson<LiveMomentScoutResult>(
      "/journeys/" + journeyId + "/moment-scout/live",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          consent_external_location: true,
          location_observation_id: locationObservationId,
          budget_minutes: budgetMinutes,
          interest,
          radius_m: radiusM,
        }),
      },
    );
  },

  selectLiveMomentScoutCandidate(
    journeyId: string,
    receiptId: string,
    candidateId: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/moment-scout/live/select",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          receipt_id: receiptId,
          candidate_id: candidateId,
          confirm_return_to_rendezvous: true,
        }),
      },
    );
  },

  selectMomentScoutCandidate(
    journeyId: string,
    locationObservationId: string,
    budgetMinutes: 15 | 30 | 45,
    interest: MomentScoutInterest,
    scoutContext: string,
    placeId: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/moment-scout/select",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          location_observation_id: locationObservationId,
          budget_minutes: budgetMinutes,
          interest,
          scout_context: scoutContext,
          place_id: placeId,
        }),
      },
    );
  },

  advanceMemberSideQuest(
    journeyId: string,
    sideQuestId: string,
    action: "start" | "arrive" | "complete" | "cancel",
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-side-quests/" + encodeURIComponent(sideQuestId) + "/" + action,
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  previewMemberSideQuestFit(
    journeyId: string,
    sideQuestId: string,
    locationObservationId: string | null,
    dwellMinutes: 10 | 20 | 30,
  ): Promise<MemberSideQuestFitPreview> {
    return requestJson<MemberSideQuestFitPreview>(
      "/journeys/" + journeyId + "/member-side-quests/" + encodeURIComponent(sideQuestId) + "/fit-preview",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({
          location_observation_id: locationObservationId,
          dwell_minutes: dwellMinutes,
          requested_mode: "WALK",
        }),
      },
    );
  },

  navigateMemberSideQuest(
    journeyId: string,
    sideQuestId: string,
    locationObservationId: string,
  ): Promise<MemberSideQuestNavigationResult> {
    return requestJson<MemberSideQuestNavigationResult>(
      "/journeys/" + journeyId + "/member-side-quests/" + encodeURIComponent(sideQuestId) + "/navigate",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({ location_observation_id: locationObservationId, requested_mode: "WALK" }),
      },
    );
  },

  getMemberSideQuestNavigationTarget(
    journeyId: string,
    sideQuestId: string,
  ): Promise<MemberSideQuestNavigationTargetResult> {
    return requestJson<MemberSideQuestNavigationTargetResult>(
      "/journeys/" + journeyId + "/member-side-quests/" + encodeURIComponent(sideQuestId) + "/navigation-targets",
      { headers: travelerAuthHeaders(), cache: "no-store" },
    );
  },

  startMemberSideQuestReturn(
    journeyId: string,
    sideQuestId: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-side-quests/" + encodeURIComponent(sideQuestId) + "/head-back",
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  reportMemberMeetupArrival(
    journeyId: string,
    sideQuestId: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/member-side-quests/" + encodeURIComponent(sideQuestId) + "/meetup-report",
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  decideMemberMeetupHandshake(
    journeyId: string,
    handshakeId: string,
    decision: "acknowledge" | "not-yet",
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/meetup-handshakes/" + encodeURIComponent(handshakeId) + "/" + decision,
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  rerouteInTransit(journeyId: string, locationObservationId: string): Promise<InTransitRerouteResult> {
    return requestJson<InTransitRerouteResult>(
      "/journeys/" + journeyId + "/in-transit/reroute",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({ location_observation_id: locationObservationId }),
      },
    );
  },

  routeToGroupRendezvous(
    journeyId: string,
    locationObservationId: string,
  ): Promise<GroupRendezvousRouteResult> {
    return requestJson<GroupRendezvousRouteResult>(
      "/journeys/" + journeyId + "/group-presence/route",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({ location_observation_id: locationObservationId, requested_mode: "WALK" }),
      },
    );
  },

  requestGroupRecoveryPlan(journeyId: string): Promise<GroupRecoveryPlanResult> {
    return requestJson<GroupRecoveryPlanResult>(
      "/journeys/" + journeyId + "/group-recovery/adjust",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({}),
      },
    );
  },

  applyGroupRecovery(journeyId: string, idempotencyKey: string): Promise<GroupRecoveryApplyResult> {
    return requestJson<GroupRecoveryApplyResult>(
      "/journeys/" + journeyId + "/group-recovery/apply",
      {
        method: "POST",
        headers: {
          ...travelerAuthHeaders(),
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({}),
      },
    );
  },

  submitJourneyInboxText(journeyId: string, text: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>("/journeys/" + journeyId + "/operator/inbox/intake", {
      method: "POST", headers: travelerAuthHeaders(), body: JSON.stringify({ source_kind: "PASTED_TEXT", text }),
    });
  },

  bindJourneyInboxItem(journeyId: string, itemId: string, reservationId: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>("/journeys/" + journeyId + "/operator/inbox/" + itemId + "/bind", {
      method: "POST", headers: travelerAuthHeaders(), body: JSON.stringify({ reservation_id: reservationId }),
    });
  },

  resolveJourneyRealityConflict(journeyId: string, conflictId: string, selectedClaimId: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>("/journeys/" + journeyId + "/operator/reality-conflicts/" + conflictId + "/resolve", {
      method: "POST", headers: travelerAuthHeaders(), body: JSON.stringify({ selected_claim_id: selectedClaimId }),
    });
  },

  answerJourneyIntentClarification(
    journeyId: string,
    intentId: string,
    answer: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/operator/intents/" + intentId + "/clarification",
      { method: "POST", body: JSON.stringify({ answer }) },
    );
  },

  startJourneyOperator(
    journeyId: string,
    objective?: string,
    requestedAutonomy: "PLAN_ONLY" | "EXECUTE_WITHIN_BOUNDS" = "EXECUTE_WITHIN_BOUNDS",
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>("/journeys/" + journeyId + "/operator/start", {
      method: "POST",
      headers: travelerAuthHeaders(),
      body: JSON.stringify({
        objective: objective ?? "Take care of this trip. Protect confirmed commitments, keep changes reasonable, and ask me before important changes.",
        requested_autonomy: requestedAutonomy,
      }),
    });
  },

  stopJourneyOperator(journeyId: string): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>("/journeys/" + journeyId + "/operator/stop", {
      method: "POST",
      headers: travelerAuthHeaders(),
    });
  },

  approveJourneyOperatorChange(
    journeyId: string,
    approvalId: string,
  ): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(
      "/journeys/" + journeyId + "/operator/approvals/" + approvalId + "/approve",
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  rejectJourneyOperatorChange(
    journeyId: string,
    approvalId: string,
  ): Promise<JourneyOperatorProjection> {
    return requestJson<JourneyOperatorProjection>(
      "/journeys/" + journeyId + "/operator/approvals/" + approvalId + "/reject",
      { method: "POST", headers: travelerAuthHeaders() },
    );
  },

  setGuardianProviderFixture(
    journeyId: string,
    state: "NORMAL" | "DISRUPTED" | "OUTAGE" | "RISK_FORECAST",
    payload: Record<string, unknown> = {},
  ): Promise<GuardianStatus["signal_fixture"]> {
    return requestJson<GuardianStatus["signal_fixture"]>(
      "/journeys/" + journeyId + "/guardian/provider-fixture",
      {
        method: "POST",
        body: JSON.stringify({ state, payload }),
      },
    );
  },

  getReflect(journeyId: string): Promise<ReflectSummary> {
    return requestJson<ReflectSummary>("/journeys/" + journeyId + "/reflect");
  },

  getTravelerTwin(travelerId: string): Promise<TravelerTwinEvidence> {
    return requestJson<TravelerTwinEvidence>("/travelers/" + travelerId + "/traveler-twin");
  },

  getTravelerCapabilities(travelerId: string): Promise<TravelerCapabilityResponse> {
    return requestJson<TravelerCapabilityResponse>(
      "/travelers/" + travelerId + "/capabilities",
    );
  },

  confirmTravelerCapabilities(
    travelerId: string,
    capabilities: Array<Pick<TravelerCapability, "code" | "severity" | "params"> & Partial<TravelerCapability>>,
  ): Promise<TravelerCapabilityResponse> {
    return requestJson<TravelerCapabilityResponse>(
      "/travelers/" + travelerId + "/capabilities/confirm",
      { method: "POST", body: JSON.stringify(capabilities) },
    );
  },

  getJourneyCapabilities(journeyId: string): Promise<TravelerCapabilityResponse> {
    return requestJson<TravelerCapabilityResponse>(
      "/journeys/" + journeyId + "/capabilities",
    );
  },

  confirmJourneyCapabilities(
    journeyId: string,
    capabilities: Array<Pick<TravelerCapability, "code" | "severity" | "params"> & Partial<TravelerCapability>>,
  ): Promise<TravelerCapabilityResponse> {
    return requestJson<TravelerCapabilityResponse>(
      "/journeys/" + journeyId + "/capabilities/confirm",
      { method: "POST", body: JSON.stringify(capabilities) },
    );
  },

  clearTravelerTwinLearned(travelerId: string): Promise<TravelerTwinEvidence> {
    return requestJson<TravelerTwinEvidence>("/travelers/" + travelerId + "/traveler-twin/learned", {
      method: "DELETE",
    });
  },

  callAgentTool(
    tool: string,
    payload: {
      request_id: string;
      agent_id?: string;
      journey_id?: string;
      proposal_id?: string;
      trigger_event_id?: string;
      candidate_count?: number;
      approval_id?: string;
      user_confirmed?: boolean;
    },
  ): Promise<AgentToolResponse> {
    return requestJson<AgentToolResponse>("/agent/tools/" + tool, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  approveAgentAction(
    journeyId: string,
    approvalId: string,
    approvalMethod: "USER_CONFIRMATION" | "STEP_UP" | "WEBAUTHN" = "USER_CONFIRMATION",
  ): Promise<AgentApprovalResponse> {
    return requestJson<AgentApprovalResponse>(
      "/journeys/" + journeyId + "/agent/approvals/" + encodeURIComponent(approvalId) + "/approve",
      {
        method: "POST",
        headers: travelerAuthHeaders(),
        body: JSON.stringify({ approval_method: approvalMethod }),
      },
    );
  },

  getRouteEvidence(journeyId: string, proposalId?: string): Promise<RouteEvidence> {
    const suffix = proposalId ? "?proposal_id=" + encodeURIComponent(proposalId) : "";
    return requestJson<RouteEvidence>("/journeys/" + journeyId + "/route-evidence" + suffix);
  },

  createClosureEvent(
    journeyId: string,
    activityId: string,
    occurredAt: string,
  ): Promise<EventRecord> {
    return requestJson<EventRecord>("/journeys/" + journeyId + "/events", {
      method: "POST",
      body: JSON.stringify({
        event_type: "CLOSURE",
        severity: "MAJOR",
        affected_activity_id: activityId,
        occurred_at: occurredAt,
        payload: { reason: "Demo Event Simulator" },
      }),
    });
  },

  createJourneyEvent(
    journeyId: string,
    eventType: "WEATHER" | "TRAFFIC_DELAY" | "CLOSURE" | "SCHEDULE_DELAY",
    severity: "INFO" | "MINOR" | "MAJOR" | "CRITICAL",
    activityId: string,
    occurredAt: string,
    payload: Record<string, unknown>,
  ): Promise<EventRecord> {
    return requestJson<EventRecord>("/journeys/" + journeyId + "/events", {
      method: "POST",
      body: JSON.stringify({
        event_type: eventType,
        severity,
        affected_activity_id: activityId,
        occurred_at: occurredAt,
        payload,
      }),
    });
  },

  generateReplans(
    journeyId: string,
    eventId: string,
    candidateCount = 3,
    idempotencyKey?: string,
  ): Promise<ReplanProposal> {
    return requestJson<ReplanProposal>("/journeys/" + journeyId + "/replans", {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      body: JSON.stringify({ trigger_event_id: eventId, candidate_count: candidateCount }),
    });
  },

  listReplans(journeyId: string): Promise<ReplanProposal[]> {
    return requestJson<ReplanProposal[]>("/journeys/" + journeyId + "/replans");
  },

  acceptReplan(proposalId: string, idempotencyKey: string): Promise<AcceptReplanResponse> {
    return requestJson<AcceptReplanResponse>("/replans/" + proposalId + "/accept", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    });
  },

  rejectReplan(proposalId: string, idempotencyKey?: string): Promise<ReplanProposal> {
    return requestJson<ReplanProposal>("/replans/" + proposalId + "/reject", {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    });
  },
};
