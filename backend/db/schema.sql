PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS travelers (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT,
    locale TEXT NOT NULL DEFAULT 'en-GB',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    preference_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0.5 CHECK (weight >= 0.0 AND weight <= 1.0),
    source TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(traveler_id, category, preference_key)
);

CREATE TABLE IF NOT EXISTS journey_outcome_events (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    occurred_at_actual TEXT NOT NULL,
    planned_start_at TEXT,
    planned_end_at TEXT,
    source TEXT NOT NULL DEFAULT 'DOMAIN',
    related_proposal_id TEXT,
    related_agent_run_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS overnight_steward_cycles (
    id TEXT PRIMARY KEY,
    cycle_key TEXT NOT NULL UNIQUE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    local_date TEXT NOT NULL,
    next_local_date TEXT NOT NULL,
    plan_version_id TEXT,
    state TEXT NOT NULL DEFAULT 'DAY_CLOSING',
    consumed_outcome_ids_json TEXT NOT NULL DEFAULT '[]',
    learning_summary_by_traveler_json TEXT NOT NULL DEFAULT '{}',
    briefing_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    morning_ready_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_overnight_steward_journey_day
    ON overnight_steward_cycles(journey_id, local_date, created_at);

CREATE TABLE IF NOT EXISTS traveler_preference_evidence (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    journey_id TEXT REFERENCES journeys(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    preference_dimension TEXT NOT NULL,
    direction TEXT NOT NULL,
    strength REAL NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0,
    source TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 1,
    explanation TEXT NOT NULL DEFAULT '',
    related_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS traveler_capabilities (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    journey_id TEXT REFERENCES journeys(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    capability_class TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('HARD','STRONG','SOFT')),
    params_json TEXT NOT NULL DEFAULT '{}',
    scope TEXT NOT NULL CHECK (scope IN ('TRAVELER','JOURNEY')),
    source TEXT NOT NULL DEFAULT 'USER_CONFIRMED',
    provenance TEXT NOT NULL DEFAULT 'USER_STATED',
    explicit INTEGER NOT NULL DEFAULT 1 CHECK (explicit IN (0,1)),
    confirmed INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0,1)),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    confirmed_at TEXT,
    UNIQUE(traveler_id, journey_id, scope, code)
);

CREATE TABLE IF NOT EXISTS traveler_twin_snapshots (
    traveler_id TEXT PRIMARY KEY REFERENCES travelers(id) ON DELETE CASCADE,
    explicit_preferences_json TEXT NOT NULL DEFAULT '[]',
    learned_soft_preferences_json TEXT NOT NULL DEFAULT '[]',
    conflicts_json TEXT NOT NULL DEFAULT '[]',
    explicit_capabilities_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outcome_events_journey ON journey_outcome_events(journey_id, occurred_at_actual);
CREATE INDEX IF NOT EXISTS idx_preference_evidence_traveler ON traveler_preference_evidence(traveler_id, status, created_at);

CREATE TABLE IF NOT EXISTS traveler_agent_policies (
    traveler_id TEXT PRIMARY KEY REFERENCES travelers(id) ON DELETE CASCADE,
    mode TEXT NOT NULL DEFAULT 'ADVISORY' CHECK (mode IN ('ADVISORY','ASSISTED','AUTONOMOUS')),
    auto_accept_replan INTEGER NOT NULL DEFAULT 0 CHECK (auto_accept_replan IN (0,1)),
    max_auto_replan_cost_delta_minor INTEGER NOT NULL DEFAULT 0 CHECK (max_auto_replan_cost_delta_minor >= 0),
    max_auto_loss_minor INTEGER NOT NULL DEFAULT 0 CHECK (max_auto_loss_minor >= 0),
    max_auto_schedule_drift_min INTEGER NOT NULL DEFAULT 0 CHECK (max_auto_schedule_drift_min >= 0),
    allowed_activity_types_json TEXT NOT NULL DEFAULT '[]',
    allowed_booking_types_json TEXT NOT NULL DEFAULT '[]',
    protected_commitment_levels_json TEXT NOT NULL DEFAULT '["C3_Guaranteed","C4_Anchored"]',
    allow_auto_commitment_management INTEGER NOT NULL DEFAULT 0 CHECK (allow_auto_commitment_management IN (0,1)),
    allow_auto_when_provider_degraded INTEGER NOT NULL DEFAULT 0 CHECK (allow_auto_when_provider_degraded IN (0,1)),
    allow_auto_on_critical_event INTEGER NOT NULL DEFAULT 0 CHECK (allow_auto_on_critical_event IN (0,1)),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journeys (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    city_code TEXT NOT NULL,
    timezone TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    budget_currency TEXT NOT NULL,
    budget_amount_minor INTEGER NOT NULL CHECK (budget_amount_minor >= 0),
    planning_mode TEXT NOT NULL DEFAULT 'balanced' CHECK (planning_mode IN ('balanced','budget','explore','strict_schedule')),
    status TEXT NOT NULL CHECK (status IN ('DRAFT','PLANNED','ACTIVE','COMPLETED','CANCELLED')),
    active_plan_version_id TEXT REFERENCES plan_versions(id) ON DELETE SET NULL,
    current_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    -- ORD-0383 slice 1: additive and deliberately without a DEFAULT.  A row that was never
    -- deleted is NULL, which is what every pre-existing row already is; a default would have
    -- to invent a deletion moment.  See `deleted_at` in `app/db/models.py`.
    deleted_at TEXT,
    CHECK (end_at > start_at)
);

CREATE TABLE IF NOT EXISTS constraints (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('HARD','SOFT')),
    category TEXT NOT NULL,
    rule_code TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    weight REAL NOT NULL DEFAULT 1.0 CHECK (weight >= 0.0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_versions (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    planning_mode TEXT NOT NULL CHECK (planning_mode IN ('balanced','budget','explore','strict_schedule')),
    status TEXT NOT NULL CHECK (status IN ('CANDIDATE','SELECTED','ACTIVE','SUPERSEDED','REJECTED')),
    lifecycle TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (lifecycle IN ('ACTIVE','STANDBY','RETIRED')),
    trigger_contract_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL CHECK (source IN ('INITIAL','REPLAN','MANUAL')),
    parent_plan_version_id TEXT REFERENCES plan_versions(id) ON DELETE SET NULL,
    total_cost_minor INTEGER NOT NULL DEFAULT 0 CHECK (total_cost_minor >= 0),
    currency TEXT NOT NULL,
    estimated_duration_min INTEGER NOT NULL DEFAULT 0 CHECK (estimated_duration_min >= 0),
    utility_score REAL,
    score_breakdown_json TEXT,
    explanation_json TEXT,
    mobility_snapshot_id TEXT,
    mobility_evidence_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, version_no)
);

CREATE TABLE IF NOT EXISTS places (
    id TEXT PRIMARY KEY,
    provider_key TEXT NOT NULL,
    external_id TEXT NOT NULL,
    city_code TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    opening_hours_json TEXT NOT NULL DEFAULT '{}',
    tags_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    -- ORD-0095-1 / arbitration R4: every geometry stored here is WGS-84, and the row says so
    -- instead of leaving that to memory.  `source_coordinate_system` records the CRS a provider
    -- handed us (a future GCJ-02 source), so an inbound conversion can never be mistaken for
    -- the system the *stored* geometry is in.  Existing rows are backfilled by the default.
    coordinate_system TEXT NOT NULL DEFAULT 'WGS84',
    source_coordinate_system TEXT,
    UNIQUE(provider_key, external_id)
);

CREATE TABLE IF NOT EXISTS city_services (
    id TEXT PRIMARY KEY,
    provider_key TEXT NOT NULL,
    external_id TEXT NOT NULL,
    place_id TEXT REFERENCES places(id) ON DELETE SET NULL,
    city_code TEXT NOT NULL,
    service_type TEXT NOT NULL,
    name TEXT NOT NULL,
    availability_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    UNIQUE(provider_key, external_id)
);

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL CHECK (sequence_no >= 1),
    activity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    place_id TEXT REFERENCES places(id) ON DELETE SET NULL,
    city_service_id TEXT REFERENCES city_services(id) ON DELETE SET NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    travel_from_prev_min INTEGER NOT NULL DEFAULT 0 CHECK (travel_from_prev_min >= 0),
    estimated_cost_minor INTEGER NOT NULL DEFAULT 0 CHECK (estimated_cost_minor >= 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PLANNED','READY','NOT_STARTED','EN_ROUTE','ARRIVED','IN_PROGRESS','ACTIVE','COMPLETED','SKIPPED','CANCELLED')),
    locked INTEGER NOT NULL DEFAULT 0 CHECK (locked IN (0,1)),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(plan_version_id, sequence_no),
    CHECK (end_at > start_at)
);

CREATE TABLE IF NOT EXISTS commitments (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    kind TEXT NOT NULL CHECK (kind IN ('BOOKING','ORDER','PAYMENT','APPOINTMENT','OTHER')),
    level TEXT NOT NULL CHECK (level IN ('C0_Flexible','C1_Preferred','C2_Reserved','C3_Guaranteed','C4_Anchored')),
    status TEXT NOT NULL CHECK (status IN ('PROPOSED','ACTIVE','FULFILLED','CANCELLED','BREACHED')),
    monetary_value_minor INTEGER NOT NULL DEFAULT 0 CHECK (monetary_value_minor >= 0),
    monetary_value_status TEXT NOT NULL DEFAULT 'KNOWN',
    currency TEXT NOT NULL,
    external_ref TEXT,
    policy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    commitment_id TEXT REFERENCES commitments(id) ON DELETE SET NULL,
    provider_key TEXT NOT NULL,
    external_ref TEXT,
    status TEXT NOT NULL CHECK (status IN ('DRAFT','PENDING','CONFIRMED','COMPLETED','CANCELLED','FAILED')),
    amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (amount_minor >= 0),
    amount_status TEXT NOT NULL DEFAULT 'KNOWN',
    currency TEXT NOT NULL,
    cancellation_policy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    commitment_id TEXT REFERENCES commitments(id) ON DELETE SET NULL,
    provider_key TEXT NOT NULL,
    external_ref TEXT,
    status TEXT NOT NULL CHECK (status IN ('DRAFT','PENDING','CONFIRMED','FULFILLED','CANCELLED','FAILED')),
    amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    items_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    booking_id TEXT REFERENCES bookings(id) ON DELETE SET NULL,
    order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    provider_key TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('AUTHORIZE','CAPTURE','REFUND','VOID')),
    status TEXT NOT NULL CHECK (status IN ('INITIATED','AUTHORIZED','SUCCEEDED','FAILED','REFUNDED','VOIDED')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    external_ref TEXT,
    provider_payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(provider_key, idempotency_key)
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT 'SIMULATED' CHECK (provenance IN ('SIMULATED','PROVIDER_VERIFIED','USER_REPORTED','SYSTEM_DERIVED')),
    event_type TEXT NOT NULL CHECK (event_type IN ('TRAFFIC_DELAY','CLOSURE','WEATHER','SCHEDULE_DELAY','SERVICE_UNAVAILABLE','USER_CHANGE','OPPORTUNITY_WINDOW','OTHER')),
    severity TEXT NOT NULL CHECK (severity IN ('INFO','MINOR','MAJOR','CRITICAL')),
    status TEXT NOT NULL CHECK (status IN ('DETECTED','ACKNOWLEDGED','RESOLVED','IGNORED')),
    affected_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    occurred_at TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    resolved_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS impact_assessments (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    status TEXT NOT NULL,
    maturity_stage TEXT NOT NULL DEFAULT 'AI_ONLY',
    selected_corroboration_refs_json TEXT NOT NULL DEFAULT '[]',
    independent_evidence_count INTEGER NOT NULL DEFAULT 0,
    uncertain INTEGER NOT NULL DEFAULT 0 CHECK (uncertain IN (0,1)),
    selected_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    primary_recovery_target_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    secondary_risk_activity_ids_json TEXT NOT NULL DEFAULT '[]',
    candidates_json TEXT NOT NULL DEFAULT '[]',
    validated_activity_ids_json TEXT NOT NULL DEFAULT '[]',
    rejected_activity_ids_json TEXT NOT NULL DEFAULT '[]',
    reason_codes_json TEXT NOT NULL DEFAULT '[]',
    semantic_reason TEXT NOT NULL DEFAULT '',
    failure_code TEXT,
    response_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS replan_proposals (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    trigger_event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    base_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    proposed_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('GENERATED','PRESENTED','ACCEPTED','REJECTED','EXPIRED','INVALIDATED')),
    hard_constraints_passed INTEGER NOT NULL CHECK (hard_constraints_passed IN (0,1)),
    locked_commitments_preserved INTEGER NOT NULL CHECK (locked_commitments_preserved IN (0,1)),
    utility_score REAL NOT NULL,
    score_breakdown_json TEXT NOT NULL,
    diff_json TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    recovery_epoch_id TEXT REFERENCES recovery_epochs(id) ON DELETE SET NULL,
    source_agent_run_id TEXT REFERENCES agent_runs(id) ON DELETE SET NULL,
    semantic_identity TEXT,
    canonical_proposal_id TEXT REFERENCES replan_proposals(id) ON DELETE SET NULL,
    CHECK (base_plan_version_id <> proposed_plan_version_id)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    journey_id TEXT REFERENCES journeys(id) ON DELETE CASCADE,
    plan_version_id TEXT REFERENCES plan_versions(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('PLACE','ACTIVITY','PLAN','REPLAN_EXPLANATION')),
    source TEXT NOT NULL CHECK (source IN ('RULES','AI','HYBRID')),
    score REAL,
    explanation TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journey_twins (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    active_plan_version_id TEXT REFERENCES plan_versions(id) ON DELETE SET NULL,
    current_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    latest_event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    projection_status TEXT NOT NULL CHECK (projection_status IN ('READY','STALE','DEGRADED')),
    snapshot_at TEXT NOT NULL,
    context_json TEXT NOT NULL DEFAULT '{}',
    upcoming_commitments_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_calls (
    id TEXT PRIMARY KEY,
    provider_key TEXT NOT NULL,
    operation TEXT NOT NULL,
    request_json TEXT NOT NULL,
    response_json TEXT,
    status TEXT NOT NULL CHECK (status IN ('SUCCESS','FAILURE','TIMEOUT','DEGRADED')),
    latency_ms INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    journey_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    before_json TEXT,
    after_json TEXT,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_status INTEGER,
    response_json TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    claim_token TEXT,
    claim_deadline TEXT
);

CREATE TABLE IF NOT EXISTS action_approvals (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','CONSUMED','EXPIRED','REVOKED')),
    required_decision TEXT NOT NULL DEFAULT 'REQUIRE_CONFIRMATION',
    approval_method TEXT,
    approved_by TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    approved_at TEXT,
    consumed_at TEXT,
    authority_receipt_id TEXT,
    recovery_epoch_id TEXT REFERENCES recovery_epochs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS recovery_epochs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    generation INTEGER NOT NULL,
    active_plan_version_id_at_open TEXT,
    material_world_epoch_at_open TEXT,
    recovery_reality_fingerprint TEXT NOT NULL,
    triggering_event_ids_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('OPEN','SUPERSEDED','COMMITTED','ABANDONED')),
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    close_reason TEXT,
    superseded_by_recovery_epoch_id TEXT REFERENCES recovery_epochs(id) ON DELETE SET NULL,
    UNIQUE(journey_id, generation)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_recovery_epochs_one_open
    ON recovery_epochs(journey_id) WHERE status = 'OPEN';
CREATE INDEX IF NOT EXISTS idx_recovery_epochs_journey_status
    ON recovery_epochs(journey_id, status, generation);

CREATE TABLE IF NOT EXISTS collective_authority_receipts (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    proposal_id TEXT NOT NULL REFERENCES replan_proposals(id) ON DELETE CASCADE,
    plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE CASCADE,
    authority_mode TEXT NOT NULL CHECK (authority_mode IN ('AUTHENTICATED_MEMBER_CONSENT','UNANIMOUS_DOMINANCE')),
    decision_epoch TEXT NOT NULL,
    material_world_epoch TEXT NOT NULL,
    candidate_surface_fingerprint TEXT NOT NULL,
    source_mission_id TEXT REFERENCES journey_missions(id) ON DELETE SET NULL,
    source_agent_run_id TEXT REFERENCES agent_runs(id) ON DELETE SET NULL,
    required_member_ids_json TEXT NOT NULL DEFAULT '[]',
    response_audit_ids_json TEXT NOT NULL DEFAULT '[]',
    principal_actor_ids_json TEXT NOT NULL DEFAULT '[]',
    classification TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    invalidated_at TEXT,
    invalidation_code TEXT,
    recovery_epoch_id TEXT REFERENCES recovery_epochs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_collective_authority_receipts_target
    ON collective_authority_receipts(journey_id, proposal_id, plan_version_id);

CREATE INDEX IF NOT EXISTS idx_journeys_traveler ON journeys(traveler_id);
CREATE INDEX IF NOT EXISTS idx_plan_versions_journey ON plan_versions(journey_id, version_no);
-- One ACTIVE PlanVersion per Journey is a domain invariant, not a convention.
-- No Python-side lock can guarantee it across processes, and SQLite has no
-- SELECT ... FOR UPDATE to serialise the read/validate/write window that
-- produces it, so the guarantee is stated where it can actually be enforced.
-- A rejected writer sees IntegrityError and must treat it as a conflict, not
-- as a crash.
CREATE UNIQUE INDEX IF NOT EXISTS ux_plan_versions_single_active
    ON plan_versions(journey_id) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_activities_plan ON activities(plan_version_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_commitments_journey ON commitments(journey_id, status, level);
-- ORD-0360: a Journey claims a node with at most one ACTIVE C4 anchor.  Two ACTIVE rows for
-- one node are not two constraints - resolve_plan_anchors() emits one anchor per row, the pair
-- then overlaps with itself, and generation answered the traveller's own duplicate reservation
-- as "no feasible plan candidates".  Python cannot guarantee this across processes (see the
-- note on ux_plan_versions_single_active), so it is stated where it can be enforced.
-- The role split below is the same one resolve_plan_anchors()/anchor_claim_identity() use:
-- ARRIVAL and DEPARTURE collapse onto the Journey's structural node, MID_TRIP carries its own
-- place/service key.  Rows with no $.anchor_role - the commerce booking/order commitments -
-- match none of these on purpose: they share the semantic_key namespace but are protected
-- through activity_id, so two of them for one place stay legal.
CREATE UNIQUE INDEX IF NOT EXISTS uq_commitments_one_active_arrival_anchor
    ON commitments(journey_id)
    WHERE status = 'ACTIVE' AND level = 'C4_Anchored' AND json_valid(policy_json)
      AND upper(json_extract(policy_json, '$.anchor_role')) = 'ARRIVAL';
CREATE UNIQUE INDEX IF NOT EXISTS uq_commitments_one_active_departure_anchor
    ON commitments(journey_id)
    WHERE status = 'ACTIVE' AND level = 'C4_Anchored' AND json_valid(policy_json)
      AND upper(json_extract(policy_json, '$.anchor_role')) = 'DEPARTURE';
CREATE UNIQUE INDEX IF NOT EXISTS uq_commitments_one_active_mid_trip_anchor
    ON commitments(journey_id, json_extract(policy_json, '$.semantic_key'))
    WHERE status = 'ACTIVE' AND level = 'C4_Anchored' AND json_valid(policy_json)
      AND upper(json_extract(policy_json, '$.anchor_role')) = 'MID_TRIP';
CREATE INDEX IF NOT EXISTS idx_events_journey ON events(journey_id, detected_at);
CREATE INDEX IF NOT EXISTS idx_impact_assessments_event ON impact_assessments(event_id, created_at);
CREATE INDEX IF NOT EXISTS idx_replans_journey ON replan_proposals(journey_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_journey ON audit_logs(journey_id, created_at);
CREATE INDEX IF NOT EXISTS idx_action_approvals_scope
    ON action_approvals(journey_id, action, target_id, status, expires_at);

CREATE TABLE IF NOT EXISTS journey_missions (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    trigger_event_id TEXT,
    user_text TEXT NOT NULL,
    objective_codes_json TEXT NOT NULL DEFAULT '[]',
    protected_activity_ids_json TEXT NOT NULL DEFAULT '[]',
    mutable_activity_ids_json TEXT NOT NULL DEFAULT '[]',
    intent_json TEXT NOT NULL DEFAULT '{}',
    resolved_intent_json TEXT NOT NULL DEFAULT '{}',
    allowed_action_classes_json TEXT NOT NULL DEFAULT '[]',
    unresolved_references_json TEXT NOT NULL DEFAULT '[]',
    compiler_provider_key TEXT NOT NULL DEFAULT 'deterministic',
    compiler_model_key TEXT NOT NULL DEFAULT 'mission-compiler-v2-fallback',
    compiler_confidence REAL NOT NULL DEFAULT 1.0,
    reasoning_summary TEXT NOT NULL DEFAULT '',
    is_standing INTEGER NOT NULL DEFAULT 0 CHECK (is_standing IN (0,1)),
    parent_mission_id TEXT,
    max_cost_delta_minor INTEGER NOT NULL DEFAULT 0 CHECK (max_cost_delta_minor >= 0),
    max_loss_minor INTEGER NOT NULL DEFAULT 0 CHECK (max_loss_minor >= 0),
    max_schedule_drift_min INTEGER NOT NULL DEFAULT 0 CHECK (max_schedule_drift_min >= 0),
    preferences_json TEXT NOT NULL DEFAULT '{}',
    requested_autonomy TEXT NOT NULL DEFAULT 'PLAN_ONLY',
    status TEXT NOT NULL DEFAULT 'CREATED',
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    failure_reason TEXT
);

CREATE TABLE IF NOT EXISTS journey_intents (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    created_by_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    created_by_member_id TEXT,
    source_text TEXT NOT NULL,
    intent_kind TEXT NOT NULL,
    scope_kind TEXT,
    scope_start_at TEXT,
    scope_end_at TEXT,
    local_date TEXT,
    target_activity_ids_json TEXT NOT NULL DEFAULT '[]',
    canonical_dimensions_json TEXT NOT NULL DEFAULT '[]',
    constraints_json TEXT NOT NULL DEFAULT '[]',
    capabilities_json TEXT NOT NULL DEFAULT '[]',
    preference_hints_json TEXT NOT NULL DEFAULT '{}',
    semantic_envelope_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'USER_TEMPORARY_INTENT',
    compiler_provider_key TEXT NOT NULL DEFAULT 'deterministic',
    compiler_model_key TEXT NOT NULL DEFAULT 'fallback',
    compiler_confidence REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    evaluation_state TEXT NOT NULL DEFAULT 'QUEUED',
    semantic_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    superseded_at TEXT,
    expired_at TEXT,
    cancelled_at TEXT,
    UNIQUE(journey_id, semantic_fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_journey_intents_active_scope
    ON journey_intents(journey_id, status, scope_start_at, scope_end_at);

CREATE TABLE IF NOT EXISTS member_side_quests (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,
    traveler_id TEXT NOT NULL,
    planned_separation_intent_id TEXT NOT NULL,
    active_plan_version_id TEXT NOT NULL,
    rendezvous_activity_id TEXT NOT NULL,
    rendezvous_place_id TEXT NOT NULL,
    rendezvous_title TEXT NOT NULL,
    rendezvous_place_name TEXT NOT NULL,
    rendezvous_scheduled_at TEXT,
    side_place_id TEXT,
    side_title TEXT NOT NULL,
    destination_authority TEXT NOT NULL
        CHECK (destination_authority IN ('EXACT_KNOWN_PLACE', 'DESCRIPTIVE_ONLY')),
    state TEXT NOT NULL
        CHECK (state IN ('DESTINATION_UNRESOLVED', 'READY', 'EN_ROUTE', 'ARRIVED',
                         'COMPLETED', 'CANCELLED', 'INVALIDATED')),
    created_at TEXT NOT NULL,
    started_at TEXT,
    arrived_at TEXT,
    completed_at TEXT,
    cancelled_at TEXT,
    invalidated_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_member_side_quests_one_open_per_split
    ON member_side_quests(journey_id, member_id, planned_separation_intent_id)
    WHERE state IN ('DESTINATION_UNRESOLVED', 'READY', 'EN_ROUTE', 'ARRIVED');
CREATE INDEX IF NOT EXISTS idx_member_side_quests_journey_member_updated
    ON member_side_quests(journey_id, member_id, updated_at);

CREATE TABLE IF NOT EXISTS member_live_moment_scout_receipts (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,
    traveler_id TEXT NOT NULL,
    location_observation_id TEXT NOT NULL,
    active_plan_version_id TEXT NOT NULL,
    split_intent_id TEXT,
    rendezvous_activity_id TEXT NOT NULL,
    rendezvous_place_id TEXT NOT NULL,
    budget_minutes INTEGER NOT NULL,
    interest TEXT NOT NULL,
    candidates_json TEXT NOT NULL,
    provider_attempts_json TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'SELECTING', 'SELECTED', 'EXPIRED')),
    selected_candidate_id TEXT,
    selected_place_id TEXT,
    side_quest_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_member_live_moment_scout_receipts_owner_expiry
    ON member_live_moment_scout_receipts(journey_id, member_id, expires_at);

CREATE TABLE IF NOT EXISTS member_side_quest_return_reports (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,
    traveler_id TEXT NOT NULL,
    side_quest_id TEXT NOT NULL UNIQUE REFERENCES member_side_quests(id) ON DELETE CASCADE,
    planned_separation_intent_id TEXT NOT NULL,
    active_plan_version_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RETURN_STARTED_REPORTED'
        CHECK (status = 'RETURN_STARTED_REPORTED'),
    reported_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_member_side_quest_return_reports_journey_member
    ON member_side_quest_return_reports(journey_id, member_id, reported_at);

CREATE TABLE IF NOT EXISTS planned_split_meetup_handshakes (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    owner_member_id TEXT NOT NULL,
    owner_traveler_id TEXT NOT NULL,
    planned_separation_intent_id TEXT NOT NULL,
    member_side_quest_id TEXT NOT NULL,
    active_plan_version_id TEXT NOT NULL,
    rendezvous_activity_id TEXT NOT NULL,
    rendezvous_place_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (state IN ('PENDING', 'PEER_ACKNOWLEDGED', 'NOT_CONFIRMED', 'EXPIRED', 'INVALIDATED')),
    reported_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    responder_member_id TEXT,
    responder_traveler_id TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_planned_split_meetup_handshakes_one_pending_per_owner
    ON planned_split_meetup_handshakes(journey_id, owner_member_id)
    WHERE state = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_planned_split_meetup_handshakes_journey_reported
    ON planned_split_meetup_handshakes(journey_id, reported_at);

CREATE TABLE IF NOT EXISTS member_place_invitations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    owner_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    owner_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    owner_split_intent_id TEXT NOT NULL REFERENCES journey_intents(id) ON DELETE CASCADE,
    owner_side_quest_id TEXT NOT NULL REFERENCES member_side_quests(id) ON DELETE CASCADE,
    active_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE CASCADE,
    place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    place_provider_key TEXT NOT NULL,
    place_external_id TEXT NOT NULL,
    rendezvous_activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    rendezvous_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    disclosure_snapshot_json TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (state IN ('OPEN', 'WITHDRAWN', 'EXPIRED', 'STALE')),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    withdrawn_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_member_place_invitations_one_open_per_quest
    ON member_place_invitations(journey_id, owner_side_quest_id)
    WHERE state = 'OPEN';
CREATE INDEX IF NOT EXISTS idx_member_place_invitations_journey_owner_created
    ON member_place_invitations(journey_id, owner_member_id, created_at);

CREATE TABLE IF NOT EXISTS member_place_invitation_recipients (
    id TEXT PRIMARY KEY,
    invitation_id TEXT NOT NULL REFERENCES member_place_invitations(id) ON DELETE CASCADE,
    recipient_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    recipient_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'INVITED'
        CHECK (state IN ('INVITED', 'ACCEPTANCE_NEEDS_COMPLETION', 'ACCEPTED_OWN_STOP_READY', 'DECLINED')),
    invited_at TEXT NOT NULL,
    responded_at TEXT,
    accepted_split_intent_id TEXT REFERENCES journey_intents(id) ON DELETE SET NULL,
    accepted_side_quest_id TEXT REFERENCES member_side_quests(id) ON DELETE SET NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(invitation_id, recipient_member_id)
);
CREATE INDEX IF NOT EXISTS idx_member_place_invitation_recipients_member_state
    ON member_place_invitation_recipients(recipient_member_id, state, invited_at);

CREATE TABLE IF NOT EXISTS member_place_invitation_progress (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    invitation_id TEXT NOT NULL REFERENCES member_place_invitations(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,
    traveler_id TEXT NOT NULL,
    signal_type TEXT NOT NULL
        CHECK (signal_type IN ('AT_INVITED_PLACE_SELF_REPORTED', 'HEADING_BACK_SELF_REPORTED')),
    active_plan_version_id TEXT NOT NULL,
    planned_separation_intent_id TEXT NOT NULL,
    side_quest_id TEXT NOT NULL,
    place_id TEXT NOT NULL,
    consent_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'WITHDRAWN')),
    reported_at TEXT NOT NULL,
    withdrawn_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(invitation_id, member_id, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_member_place_invitation_progress_invitation_status
    ON member_place_invitation_progress(invitation_id, status, signal_type);

CREATE TABLE IF NOT EXISTS member_place_group_share_consents (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    invitation_id TEXT NOT NULL REFERENCES member_place_invitations(id) ON DELETE CASCADE,
    owner_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    owner_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    owner_split_intent_id TEXT NOT NULL REFERENCES journey_intents(id) ON DELETE CASCADE,
    owner_side_quest_id TEXT NOT NULL REFERENCES member_side_quests(id) ON DELETE CASCADE,
    base_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    base_cursor_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    place_snapshot_json TEXT NOT NULL,
    rendezvous_activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    rendezvous_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    audience_snapshot_json TEXT NOT NULL,
    audience_snapshot_hash TEXT NOT NULL,
    plan_snapshot_hash TEXT NOT NULL,
    source_snapshot_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'WITHDRAWN', 'EXPIRED', 'STALE')),
    consented_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    withdrawn_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_member_place_group_share_consents_one_active
    ON member_place_group_share_consents(journey_id, invitation_id)
    WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_member_place_group_share_consents_invitation_created
    ON member_place_group_share_consents(journey_id, invitation_id, created_at);

CREATE TABLE IF NOT EXISTS member_place_promotions (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    invitation_id TEXT NOT NULL REFERENCES member_place_invitations(id) ON DELETE CASCADE,
    actor_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    actor_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    active_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    rendezvous_activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    current_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    trigger_event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    proposal_id TEXT REFERENCES replan_proposals(id) ON DELETE SET NULL,
    mission_id TEXT REFERENCES journey_missions(id) ON DELETE SET NULL,
    request_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    dwell_minutes INTEGER NOT NULL CHECK (dwell_minutes IN (10, 20, 30)),
    state TEXT NOT NULL DEFAULT 'PENDING_ROUTE'
        CHECK (state IN ('PENDING_ROUTE', 'WAITING_FOR_MEMBERS', 'AUTHORIZED', 'APPLIED', 'DECLINED', 'STALE', 'BLOCKED')),
    state_detail_json TEXT NOT NULL DEFAULT '{}',
    decision_epoch TEXT,
    material_world_epoch TEXT,
    candidate_surface_fingerprint TEXT,
    authority_receipt_id TEXT,
    applied_plan_version_id TEXT REFERENCES plan_versions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    decided_at TEXT,
    applied_at TEXT,
    UNIQUE(journey_id, request_key)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_member_place_promotions_one_pending
    ON member_place_promotions(journey_id, active_plan_version_id, invitation_id, place_id)
    WHERE state IN ('PENDING_ROUTE', 'WAITING_FOR_MEMBERS', 'AUTHORIZED');
CREATE INDEX IF NOT EXISTS idx_member_place_promotions_journey_state_updated
    ON member_place_promotions(journey_id, state, updated_at);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES journey_missions(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    outcome TEXT,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    recovery_epoch_id TEXT REFERENCES recovery_epochs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agent_run_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    decision TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_pending_actions (
    id TEXT PRIMARY KEY,
    approval_id TEXT NOT NULL UNIQUE REFERENCES action_approvals(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    mission_id TEXT NOT NULL REFERENCES journey_missions(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    originating_step_id TEXT REFERENCES agent_run_steps(id) ON DELETE SET NULL,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','RESUMING','RESUMED','FAILED','EXPIRED','SUPERSEDED')),
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    claimed_at TEXT,
    resumed_at TEXT,
    updated_at TEXT NOT NULL,
    authority_receipt_id TEXT,
    recovery_epoch_id TEXT REFERENCES recovery_epochs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_pending_actions_run
    ON agent_pending_actions(run_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_pending_actions_journey
    ON agent_pending_actions(journey_id, status, created_at);

CREATE TABLE IF NOT EXISTS guardian_runs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    standing_mission_id TEXT REFERENCES journey_missions(id) ON DELETE SET NULL,
    trigger_event_id TEXT REFERENCES events(id) ON DELETE SET NULL,
    agent_run_id TEXT REFERENCES agent_runs(id) ON DELETE SET NULL,
    proposal_id TEXT REFERENCES replan_proposals(id) ON DELETE SET NULL,
    decision TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    action_status TEXT NOT NULL DEFAULT 'NO_ACTION',
    evidence_fingerprint TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    reasoning_summary TEXT NOT NULL DEFAULT '',
    active_plan_before_id TEXT,
    active_plan_after_id TEXT,
    trigger_kind TEXT NOT NULL DEFAULT 'REACTIVE',
    resilience_snapshot_id TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    cooldown_until TEXT,
    UNIQUE(journey_id, evidence_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_journey_missions_journey ON journey_missions(journey_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_runs_mission ON agent_runs(mission_id, started_at);
CREATE INDEX IF NOT EXISTS idx_agent_run_steps_run ON agent_run_steps(run_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_guardian_runs_journey ON guardian_runs(journey_id, created_at);

CREATE TABLE IF NOT EXISTS provider_observations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    observation_type TEXT NOT NULL,
    state TEXT NOT NULL,
    incident_fingerprint TEXT,
    provenance TEXT NOT NULL DEFAULT 'REPLAY',
    captured_at TEXT NOT NULL,
    expires_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS city_signal_fixtures (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL DEFAULT 'city-signal-fixture',
    state TEXT NOT NULL DEFAULT 'NORMAL',
    revision INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guardian_pulses (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    provider_key TEXT NOT NULL,
    observation_ids_json TEXT NOT NULL DEFAULT '[]',
    guardian_run_id TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_provider_observations_journey
    ON provider_observations(journey_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_guardian_pulses_journey
    ON guardian_pulses(journey_id, started_at);

CREATE TABLE IF NOT EXISTS autopilot_enrollments (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    enabled INTEGER NOT NULL DEFAULT 1,
    interval_seconds REAL NOT NULL DEFAULT 60,
    provider_mesh_json TEXT NOT NULL DEFAULT '{}',
    last_pulse_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journey_resilience_snapshots (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    status TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    expires_at TEXT,
    components_json TEXT NOT NULL DEFAULT '{}',
    activity_risks_json TEXT NOT NULL DEFAULT '[]',
    commitment_buffers_json TEXT NOT NULL DEFAULT '[]',
    failure_modes_json TEXT NOT NULL DEFAULT '[]',
    recommendation_json TEXT NOT NULL DEFAULT '{}',
    provenance_json TEXT NOT NULL DEFAULT '[]',
    fingerprint TEXT NOT NULL,
    UNIQUE(journey_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS counterfactual_simulations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    snapshot_id TEXT REFERENCES journey_resilience_snapshots(id) ON DELETE SET NULL,
    scenario_key TEXT NOT NULL,
    scenario_type TEXT NOT NULL,
    parameters_json TEXT NOT NULL DEFAULT '{}',
    feasible INTEGER NOT NULL,
    c4_preserved INTEGER NOT NULL,
    cost_delta_minor INTEGER NOT NULL DEFAULT 0,
    schedule_drift_min INTEGER NOT NULL DEFAULT 0,
    plan_changes_json TEXT NOT NULL DEFAULT '[]',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, scenario_key)
);

CREATE TABLE IF NOT EXISTS real_place_candidates (
    id TEXT PRIMARY KEY,
    journey_id TEXT REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    external_id TEXT NOT NULL,
    city_code TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    opening_hours_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    captured_at TEXT NOT NULL,
    expires_at TEXT,
    distance_m REAL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    materialized_place_id TEXT,
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    UNIQUE(journey_id, provider_key, external_id)
);

CREATE INDEX IF NOT EXISTS idx_autopilot_enrollments_enabled
    ON autopilot_enrollments(enabled, updated_at);
CREATE INDEX IF NOT EXISTS idx_resilience_snapshots_journey
    ON journey_resilience_snapshots(journey_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_counterfactuals_journey
    ON counterfactual_simulations(journey_id, created_at);
CREATE INDEX IF NOT EXISTS idx_real_place_candidates_journey
    ON real_place_candidates(journey_id, captured_at);

CREATE TABLE IF NOT EXISTS member_draft_shortlist_items (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    external_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    coordinate_system TEXT NOT NULL DEFAULT 'WGS84',
    source_url TEXT NOT NULL,
    source_provenance TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    opening_hours_json TEXT NOT NULL DEFAULT '{}',
    cost_evidence_json TEXT NOT NULL DEFAULT '{}',
    source_tags_json TEXT NOT NULL DEFAULT '{}',
    distance_m REAL,
    distance_basis TEXT,
    status TEXT NOT NULL DEFAULT 'SAVED' CHECK (status = 'SAVED'),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, member_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_member_draft_shortlist_items_owner
    ON member_draft_shortlist_items(journey_id, member_id, traveler_id, updated_at);

CREATE TABLE IF NOT EXISTS member_draft_resume_intents (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    shortlist_id TEXT NOT NULL REFERENCES member_draft_shortlist_items(id) ON DELETE CASCADE,
    selected_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, member_id, traveler_id)
);

CREATE INDEX IF NOT EXISTS idx_member_draft_resume_intents_owner
    ON member_draft_resume_intents(journey_id, member_id, traveler_id, updated_at);

CREATE TABLE IF NOT EXISTS member_draft_pocket_walks (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    first_shortlist_id TEXT NOT NULL REFERENCES member_draft_shortlist_items(id) ON DELETE CASCADE,
    second_shortlist_id TEXT NOT NULL REFERENCES member_draft_shortlist_items(id) ON DELETE CASCADE,
    max_walk_minutes INTEGER CHECK (max_walk_minutes IS NULL OR (max_walk_minutes >= 1 AND max_walk_minutes <= 180)),
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, member_id, traveler_id),
    CHECK(first_shortlist_id <> second_shortlist_id)
);

CREATE INDEX IF NOT EXISTS idx_member_draft_pocket_walk_owner
    ON member_draft_pocket_walks(journey_id, member_id, traveler_id, updated_at);

CREATE TABLE IF NOT EXISTS member_draft_pocket_walk_progress (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    pocket_walk_id TEXT NOT NULL REFERENCES member_draft_pocket_walks(id) ON DELETE CASCADE,
    first_shortlist_id TEXT NOT NULL REFERENCES member_draft_shortlist_items(id) ON DELETE CASCADE,
    second_shortlist_id TEXT NOT NULL REFERENCES member_draft_shortlist_items(id) ON DELETE CASCADE,
    pocket_walk_revision INTEGER NOT NULL DEFAULT 1,
    state TEXT NOT NULL DEFAULT 'NOT_STARTED'
        CHECK (state IN ('NOT_STARTED', 'HEADING_TO_FIRST', 'FIRST_STOP_DONE_SELF_REPORTED',
                         'HEADING_TO_SECOND', 'WALK_DONE_SELF_REPORTED', 'PAUSED')),
    paused_from_state TEXT,
    progress_revision INTEGER NOT NULL DEFAULT 0,
    progress_class TEXT NOT NULL DEFAULT 'USER_REPORTED_PROGRESS'
        CHECK (progress_class = 'USER_REPORTED_PROGRESS'),
    last_operation_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, member_id, traveler_id)
);

CREATE INDEX IF NOT EXISTS idx_member_draft_pocket_walk_progress_owner
    ON member_draft_pocket_walk_progress(journey_id, member_id, traveler_id, updated_at);

CREATE TABLE IF NOT EXISTS journey_trip_contexts (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    arrival_anchor_json TEXT NOT NULL DEFAULT '{}',
    departure_anchor_json TEXT NOT NULL DEFAULT '{}',
    party_size INTEGER NOT NULL DEFAULT 1 CHECK (party_size >= 1),
    occupancy_json TEXT NOT NULL DEFAULT '{}',
    stay_budget_amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (stay_budget_amount_minor >= 0),
    stay_budget_currency TEXT NOT NULL DEFAULT 'CNY',
    -- ORD-0355: additive, and three-valued. NULL is a row written before this build could ask
    -- the question, not an answer of "not declared"; see `stay_budget_declared` in
    -- `app/db/models.py`.  The amount column above keeps its type and nullability unchanged.
    stay_budget_declared INTEGER CHECK (stay_budget_declared IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journey_launch_contexts (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    authority_kind TEXT NOT NULL,
    place_id TEXT REFERENCES places(id) ON DELETE SET NULL,
    target_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    coordinate_crs TEXT,
    source_ref_type TEXT,
    source_ref_id TEXT,
    valid_from TEXT,
    valid_until TEXT,
    confirmed_by TEXT,
    confirmation_method TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accommodation_offer_snapshots (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    external_offer_id TEXT NOT NULL,
    property_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    coordinate_crs TEXT NOT NULL DEFAULT 'WGS84',
    room_type TEXT NOT NULL,
    occupancy_json TEXT NOT NULL DEFAULT '{}',
    check_in_at TEXT NOT NULL,
    check_out_at TEXT NOT NULL,
    nightly_amount_minor INTEGER NOT NULL CHECK (nightly_amount_minor >= 0),
    taxes_amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (taxes_amount_minor >= 0),
    total_amount_minor INTEGER NOT NULL CHECK (total_amount_minor >= 0),
    currency TEXT NOT NULL,
    cancellation_policy_json TEXT NOT NULL DEFAULT '{}',
    luggage_drop_json TEXT NOT NULL DEFAULT '{}',
    refundable INTEGER NOT NULL DEFAULT 0 CHECK (refundable IN (0,1)),
    evidence_json TEXT NOT NULL DEFAULT '{}',
    captured_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'CAPTURED',
    UNIQUE(journey_id, provider_key, external_offer_id)
);

CREATE TABLE IF NOT EXISTS stay_journey_options (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    accommodation_offer_id TEXT NOT NULL REFERENCES accommodation_offer_snapshots(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    stay_total_minor INTEGER NOT NULL,
    daily_travel_minor INTEGER NOT NULL,
    mobility_total_minor INTEGER NOT NULL,
    walking_min INTEGER NOT NULL,
    protected_margin_min INTEGER NOT NULL,
    arrival_fit REAL NOT NULL,
    departure_fit REAL NOT NULL,
    cancellation_score REAL NOT NULL,
    days_json TEXT NOT NULL DEFAULT '[]',
    leg_modes_json TEXT NOT NULL DEFAULT '[]',
    journey_impact_json TEXT NOT NULL DEFAULT '{}',
    hard_constraints_passed INTEGER NOT NULL DEFAULT 1 CHECK (hard_constraints_passed IN (0,1)),
    optimizer_kind TEXT NOT NULL DEFAULT 'BOUNDED_DETERMINISTIC',
    weather_state TEXT NOT NULL DEFAULT 'NORMAL',
    materialized_plan_version_id TEXT REFERENCES plan_versions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, rank)
);

CREATE TABLE IF NOT EXISTS mobility_facts (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    option_id TEXT REFERENCES stay_journey_options(id) ON DELETE CASCADE,
    from_key TEXT NOT NULL,
    to_key TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('WALK','BICYCLE','TRANSIT','AUTO','RIDE_HAIL')),
    duration_min INTEGER NOT NULL CHECK (duration_min >= 0),
    distance_m INTEGER NOT NULL CHECK (distance_m >= 0),
    cost_amount_minor INTEGER,
    currency TEXT,
    cost_status TEXT NOT NULL,
    walking_min INTEGER NOT NULL CHECK (walking_min >= 0),
    transfers INTEGER NOT NULL DEFAULT 0 CHECK (transfers >= 0),
    weather_exposure TEXT NOT NULL,
    reliability_score REAL NOT NULL,
    provider_key TEXT NOT NULL,
    provenance TEXT NOT NULL,
    geometry_json TEXT NOT NULL DEFAULT '{}',
    crs TEXT NOT NULL DEFAULT 'WGS84',
    paid_mode INTEGER NOT NULL DEFAULT 0 CHECK (paid_mode IN (0,1)),
    evidence_json TEXT NOT NULL DEFAULT '{}',
    captured_at TEXT NOT NULL,
    expires_at TEXT,
    UNIQUE(journey_id, from_key, to_key, mode)
);

CREATE TABLE IF NOT EXISTS journey_legs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL,
    from_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    to_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    from_key TEXT NOT NULL,
    to_key TEXT NOT NULL,
    mode TEXT NOT NULL,
    depart_at TEXT NOT NULL,
    arrive_at TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    distance_m INTEGER NOT NULL,
    cost_amount_minor INTEGER,
    currency TEXT,
    cost_status TEXT NOT NULL,
    walking_min INTEGER NOT NULL,
    transfers INTEGER NOT NULL DEFAULT 0,
    reliability_score REAL NOT NULL,
    weather_exposure TEXT NOT NULL,
    geometry_json TEXT NOT NULL DEFAULT '{}',
    crs TEXT NOT NULL DEFAULT 'WGS84',
    provider_key TEXT NOT NULL,
    provenance TEXT NOT NULL,
    provider_snapshot_id TEXT REFERENCES mobility_facts(id) ON DELETE SET NULL,
    captured_at TEXT NOT NULL,
    expires_at TEXT,
    UNIQUE(plan_version_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS journey_operations_contexts (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    baggage_present INTEGER NOT NULL DEFAULT 0 CHECK (baggage_present IN (0,1)),
    baggage_size_class TEXT NOT NULL DEFAULT 'NONE',
    luggage_drop_required INTEGER NOT NULL DEFAULT 0 CHECK (luggage_drop_required IN (0,1)),
    constraints_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_reservation_drafts (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    raw_payload_json TEXT NOT NULL,
    extracted_json TEXT NOT NULL DEFAULT '{}',
    unresolved_fields_json TEXT NOT NULL DEFAULT '[]',
    extraction_mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_at TEXT NOT NULL,
    confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS journey_inbox_items (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    raw_text_hash TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    received_at TEXT NOT NULL,
    semantic_kind TEXT NOT NULL,
    reservation_type TEXT NOT NULL,
    confirmation_ref TEXT,
    change_kind TEXT NOT NULL,
    extracted_json TEXT NOT NULL DEFAULT '{}',
    provenance TEXT NOT NULL,
    status TEXT NOT NULL,
    linked_reservation_id TEXT,
    linked_commitment_id TEXT,
    reality_claim_id TEXT,
    impact_status TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, raw_text_hash)
);

CREATE TABLE IF NOT EXISTS reality_claims (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    fact_domain TEXT NOT NULL CHECK (fact_domain IN ('RESERVATION_TIME')),
    fact_key TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    value_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    effective_at TEXT,
    expires_at TEXT,
    authority_class TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('CURRENT','SUPERSEDED','CONFLICTING','REJECTED','EXPIRED')),
    generation INTEGER NOT NULL DEFAULT 1,
    fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_reality_claims_fact_status
    ON reality_claims(journey_id, fact_key, status, observed_at);

CREATE TABLE IF NOT EXISTS reality_conflicts (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    fact_domain TEXT NOT NULL CHECK (fact_domain IN ('RESERVATION_TIME')),
    fact_key TEXT NOT NULL,
    generation INTEGER NOT NULL,
    claim_ids_json TEXT NOT NULL DEFAULT '[]',
    claim_set_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    selected_claim_id TEXT,
    resolution_claim_id TEXT,
    resolution_provenance TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    UNIQUE(journey_id, fact_key, generation),
    UNIQUE(journey_id, fact_key, claim_set_fingerprint)
);

CREATE TABLE IF NOT EXISTS transport_reservations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    draft_id TEXT REFERENCES external_reservation_drafts(id) ON DELETE SET NULL,
    reservation_type TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    confirmation_ref TEXT,
    origin_json TEXT NOT NULL,
    destination_json TEXT NOT NULL,
    scheduled_departure_at TEXT NOT NULL,
    scheduled_arrival_at TEXT NOT NULL,
    estimated_arrival_at TEXT,
    actual_arrival_at TEXT,
    status TEXT NOT NULL,
    realtime_status TEXT NOT NULL DEFAULT 'UNKNOWN_REALTIME',
    passenger_scope_json TEXT NOT NULL DEFAULT '{}',
    change_policy_json TEXT NOT NULL DEFAULT '{}',
    price_amount_minor INTEGER,
    currency TEXT,
    price_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_provenance TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    booking_id TEXT REFERENCES bookings(id) ON DELETE SET NULL,
    commitment_id TEXT REFERENCES commitments(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notification_events (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    dedupe_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    payload_json TEXT NOT NULL DEFAULT '{}',
    delivery_channels_json TEXT NOT NULL DEFAULT '[]',
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS offline_journey_snapshots (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL DEFAULT 1,
    valid_until TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    provider_freshness_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS location_observations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    traveler_id TEXT REFERENCES travelers(id) ON DELETE SET NULL,
    journey_member_id TEXT REFERENCES journey_members(id) ON DELETE SET NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    accuracy_m REAL NOT NULL,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'FOREGROUND_WEB'
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    endpoint_hash TEXT NOT NULL UNIQUE,
    subscription_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edge_devices (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    journey_id TEXT REFERENCES journeys(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_sequence INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edge_actions (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES edge_devices(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edge_observations (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES edge_devices(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    observation_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS web_observations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    source_class TEXT NOT NULL DEFAULT 'OPEN_WEB',
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    evidence_fingerprint TEXT NOT NULL,
    content_excerpt TEXT NOT NULL DEFAULT '',
    authority_status TEXT NOT NULL DEFAULT 'NON_AUTHORITATIVE',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_web_observations_journey
    ON web_observations(journey_id, captured_at);

CREATE INDEX IF NOT EXISTS idx_journey_legs_plan ON journey_legs(plan_version_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_external_reservation_drafts_journey ON external_reservation_drafts(journey_id, created_at);
CREATE INDEX IF NOT EXISTS idx_transport_reservations_journey ON transport_reservations(journey_id, scheduled_arrival_at);
-- Authoritative reservation identity is created by the startup migration
-- (app/db/session.py::_migrate_reservation_identity) rather than here.
--
-- Reason: a plain unique index over (journey_id, confirmation_ref) cannot be
-- created while historical duplicate rows exist, and silently swallowing that
-- failure is exactly the defect this replaces.  The migration first quarantines
-- duplicate losers (preserving their evidence) and then creates a partial
-- unique index, so uniqueness is genuinely enforced on every database.
CREATE INDEX IF NOT EXISTS idx_notification_events_journey ON notification_events(journey_id, created_at);
CREATE INDEX IF NOT EXISTS idx_location_observations_journey ON location_observations(journey_id, captured_at);

CREATE INDEX IF NOT EXISTS idx_stay_offers_journey ON accommodation_offer_snapshots(journey_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_stay_options_journey ON stay_journey_options(journey_id, rank);
CREATE INDEX IF NOT EXISTS idx_mobility_facts_journey ON mobility_facts(journey_id, from_key, to_key);

-- ORD-0057: an asynchronous generation job and its state machine.
CREATE TABLE IF NOT EXISTS stay_generation_operations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN
        ('QUEUED','RUNNING','ABANDON_REQUESTED','COMPLETED','FAILED','ABANDONED')),
    phase TEXT CHECK (phase IS NULL OR phase IN
        ('DISCOVERY','NORMALIZATION','MOBILITY_CHECK','RANKING')),
    request_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    outcome TEXT CHECK (outcome IS NULL OR outcome IN
        ('OPTIONS_FOUND','NO_OFFERS_FROM_PROVIDER','ALL_CANDIDATES_REJECTED','NOT_APPLICABLE_ZERO_NIGHTS')),
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    abandon_requested_at TEXT,
    updated_at TEXT NOT NULL
);

-- At most one *unfinished* job per journey and per identical request.  This is a database
-- rule, not a polite convention: two taps racing through the same code path cannot both
-- start a second ~115s provider chain, and a rejected insert is read back as the winner's
-- id.  Terminal rows are deliberately excluded so a traveller can regenerate later.
CREATE UNIQUE INDEX IF NOT EXISTS ux_stay_generation_one_open_job
    ON stay_generation_operations(journey_id, fingerprint)
    WHERE status IN ('QUEUED','RUNNING','ABANDON_REQUESTED');

CREATE INDEX IF NOT EXISTS idx_stay_generation_journey_recent
    ON stay_generation_operations(journey_id, queued_at);

-- ORD-0095-1 (CITYNEXUS-ANYWHERE §6/§7): one catalog-hydration job per destination.
-- The lifecycle is *not* invented here: `status` and `phase` are the two axes the stay-generation
-- job already proved out (`stay_generation_operations`), with the arbitration's structural
-- terminal state `UNAVAILABLE` added, and `phase` names are the arbiter's, one per stage this
-- code can actually be inside.  A stage that never happens is never reported.
CREATE TABLE IF NOT EXISTS catalog_hydration_operations (
    id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    -- Nullable on purpose (ORD-0167): a request whose destination nobody can name has *no*
    -- canonical identity.  The NOT NULL below used to force this build to invent one out of the
    -- traveller's own words, and a fingerprint was then computed from that invention.
    canonical_destination_id TEXT,
    -- The three non-identity columns: verbatim input, folded input, correlation token.  None of
    -- them is a destination identifier and none may be joined against `places`.
    pending_destination_label TEXT,
    resolver_query_normalized TEXT,
    destination_pending_key TEXT,
    pending_label_fidelity TEXT CHECK (pending_label_fidelity IS NULL OR pending_label_fidelity IN
        ('EXACT_RAW','LEGACY_NORMALIZED')),
    legacy_fingerprint TEXT,
    catalog_schema_version TEXT NOT NULL,
    readiness_policy_version TEXT NOT NULL,
    provider_policy_version TEXT NOT NULL,
    journey_id TEXT REFERENCES journeys(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN
        ('QUEUED','RUNNING','ABANDON_REQUESTED','COMPLETED','FAILED','UNAVAILABLE','ABANDONED')),
    phase TEXT CHECK (phase IS NULL OR phase IN
        ('QUEUED','RESOLVING_DESTINATION','DISCOVERING_POIS','NORMALIZING','BUILDING_MOBILITY','PERSISTING','FINALIZING')),
    request_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    outcome TEXT CHECK (outcome IS NULL OR outcome IN
        ('CATALOG_PREPARED','ALREADY_CURRENT','NO_REGISTERED_SOURCE','PENDING_CANDIDATES_UNAPPLIED','ABANDONED_BY_TRAVELLER','WORKER_LOST','DESTINATION_AMBIGUOUS','RESOLVER_RUNTIME_FAILURE')),
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    abandon_requested_at TEXT,
    updated_at TEXT NOT NULL
);

-- Durable idempotency, not a polite convention: at most one *unfinished* job per identical
-- fingerprint.  A process-local lock cannot satisfy this, because two uvicorn workers do not
-- share one; a rejected insert is read back as the winner's id, so five concurrent taps of one
-- county get one job and one provider chain, and every caller is told `reused`.
CREATE UNIQUE INDEX IF NOT EXISTS ux_catalog_hydration_one_open_job
    ON catalog_hydration_operations(fingerprint)
    WHERE status IN ('QUEUED','RUNNING','ABANDON_REQUESTED');

CREATE INDEX IF NOT EXISTS idx_catalog_hydration_destination_recent
    ON catalog_hydration_operations(canonical_destination_id, queued_at);

CREATE INDEX IF NOT EXISTS idx_catalog_hydration_journey_recent
    ON catalog_hydration_operations(journey_id, queued_at);

-- R41: one durable operation for one exact grounded-origin -> target route request.
CREATE TABLE IF NOT EXISTS route_acquisition_operations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    origin_key TEXT NOT NULL,
    target_key TEXT NOT NULL,
    target_activity_id TEXT,
    requested_mode TEXT NOT NULL,
    provider_policy_version TEXT NOT NULL,
    route_truth_policy_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','RUNNING','COMPLETED','UNAVAILABLE','FAILED')),
    phase TEXT,
    outcome TEXT,
    request_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_route_acquisition_one_open
    ON route_acquisition_operations(journey_id, fingerprint)
    WHERE status IN ('QUEUED','RUNNING');

CREATE INDEX IF NOT EXISTS idx_route_acquisition_journey_recent
    ON route_acquisition_operations(journey_id, queued_at);

-- ORD-0434 step 1: a share grant is a server fact, not a URL the client assembles.
-- One journey can hold many grants.  `expires_at` and `revoked_at` carry no DEFAULT and no
-- sentinel: a NULL means that moment was never set, which is the only honest way to say
-- "this grant has no deadline" and "this grant was never revoked" without inventing either.
-- `created_by` is what the creating device asserted; this step does not authenticate it,
-- because the anonymous read path is still the product's default (tightening it is step 2).
CREATE TABLE IF NOT EXISTS journey_share_grants (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('PRIVATE','LINK_READ','INVITEES_ONLY','PUBLIC')),
    created_by TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_journey_share_grants_token
    ON journey_share_grants(token);

CREATE INDEX IF NOT EXISTS idx_journey_share_grants_journey
    ON journey_share_grants(journey_id, created_at);

-- ORD-0434 step 2: one member set per journey, and a role-to-capability table the server holds.
-- Borrowed shape: RELATION/relation_and_copy_findings.md:94 (each role carries one sentence of
-- scope) and :133 (an invitation has a lifetime, and a withdrawal has a moment).
--
-- `journey_members` is the single set the product speaks of: the unique index below is what makes
-- "one row per traveller per journey" a store fact rather than a convention a caller must respect.
-- `expires_at` is NULL for a membership that was given no end - not a far-future date.
CREATE TABLE IF NOT EXISTS journey_members (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('OWNER','ADMIN','COLLABORATOR')),
    invited_by TEXT NOT NULL,
    expires_at TEXT,
    joined_at TEXT,
    removed_at TEXT,
    preferences_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_journey_members_journey_traveler
    ON journey_members(journey_id, traveler_id);

CREATE INDEX IF NOT EXISTS idx_journey_members_journey
    ON journey_members(journey_id, created_at);

-- A pending invitation is not a membership. The recipient's signed acceptance is
-- the only path that inserts an in-force JourneyMember.
CREATE TABLE IF NOT EXISTS journey_membership_invitations (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    target_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    inviter_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    inviter_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    base_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    base_cursor_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    proposed_role TEXT NOT NULL DEFAULT 'COLLABORATOR' CHECK (proposed_role = 'COLLABORATOR'),
    title_snapshot TEXT NOT NULL,
    city_code_snapshot TEXT NOT NULL,
    approximate_start_date TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'OFFERED'
        CHECK (state IN ('OFFERED','ACCEPTED','DECLINED','REVOKED','EXPIRED')),
    request_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    declined_at TEXT,
    revoked_at TEXT,
    joined_member_id TEXT REFERENCES journey_members(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, inviter_member_id, request_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_journey_membership_invitations_one_offered
    ON journey_membership_invitations(journey_id, target_traveler_id)
    WHERE state = 'OFFERED';

CREATE INDEX IF NOT EXISTS idx_journey_membership_invitations_recipient
    ON journey_membership_invitations(target_traveler_id, state, expires_at);

-- R78: an explicit, short-lived, audience-bound self-report for the current shared rendezvous.
-- It never stores a location observation, coordinates, route, or physical-arrival claim.
CREATE TABLE IF NOT EXISTS journey_rendezvous_member_signals (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    journey_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    active_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    current_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    rendezvous_activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    public_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    signal_kind TEXT NOT NULL CHECK (signal_kind IN ('HEADING_TO_RENDEZVOUS','NEEDS_COORDINATION')),
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','REVOKED','REPLACED','STALE','EXPIRED')),
    audience_member_ids_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    reported_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    stale_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, journey_member_id, idempotency_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_journey_rendezvous_member_signals_one_active
    ON journey_rendezvous_member_signals(journey_id, journey_member_id)
    WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_journey_rendezvous_member_signals_expiry
    ON journey_rendezvous_member_signals(journey_id, status, expires_at);

CREATE TABLE IF NOT EXISTS journey_rendezvous_signal_acknowledgements (
    id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL UNIQUE
        REFERENCES journey_rendezvous_member_signals(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    requester_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    responder_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    responder_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    acknowledged_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_journey_rendezvous_signal_ack_journey
    ON journey_rendezvous_signal_acknowledgements(journey_id, acknowledged_at);

-- R79: a pair-private, mutually accepted intention to meet at one exact public Place.
-- It is not an Activity, route, location observation, booking, commitment, or arrival.
CREATE TABLE IF NOT EXISTS journey_rendezvous_buddy_handoffs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    signal_id TEXT NOT NULL REFERENCES journey_rendezvous_member_signals(id) ON DELETE CASCADE,
    acknowledgement_id TEXT NOT NULL REFERENCES journey_rendezvous_signal_acknowledgements(id) ON DELETE CASCADE,
    requester_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    requester_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    helper_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    helper_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    active_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    current_activity_id TEXT REFERENCES activities(id) ON DELETE SET NULL,
    original_rendezvous_activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    original_public_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    handoff_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    handoff_place_snapshot_json TEXT NOT NULL,
    audience_member_ids_json TEXT NOT NULL,
    audience_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OFFERED'
        CHECK (status IN ('OFFERED','ACCEPTED','DECLINED','REVOKED','CANCELLED','EXPIRED','STALE')),
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    offered_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    responded_at TEXT,
    closed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, helper_member_id, idempotency_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_journey_rendezvous_buddy_handoffs_one_current
    ON journey_rendezvous_buddy_handoffs(signal_id)
    WHERE status IN ('OFFERED','ACCEPTED');

CREATE INDEX IF NOT EXISTS idx_journey_rendezvous_buddy_handoffs_pair_status_expiry
    ON journey_rendezvous_buddy_handoffs(
        journey_id, requester_member_id, helper_member_id, status, expires_at
    );

-- R82: finite pair-consented execution window; this does not extend the R79 offer.
CREATE TABLE IF NOT EXISTS journey_rendezvous_buddy_executions (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    handoff_id TEXT NOT NULL UNIQUE REFERENCES journey_rendezvous_buddy_handoffs(id) ON DELETE CASCADE,
    signal_id TEXT NOT NULL REFERENCES journey_rendezvous_member_signals(id) ON DELETE CASCADE,
    acknowledgement_id TEXT NOT NULL REFERENCES journey_rendezvous_signal_acknowledgements(id) ON DELETE CASCADE,
    requester_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    requester_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    helper_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    helper_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    active_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    current_activity_id TEXT,
    original_rendezvous_activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE RESTRICT,
    original_public_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    original_place_snapshot_json TEXT NOT NULL,
    handoff_place_id TEXT NOT NULL REFERENCES places(id) ON DELETE RESTRICT,
    handoff_place_snapshot_json TEXT NOT NULL,
    audience_member_ids_json TEXT NOT NULL,
    audience_sha256 TEXT NOT NULL CHECK (length(audience_sha256) = 64),
    execution_window_minutes INTEGER NOT NULL CHECK (execution_window_minutes IN (30,60,90)),
    status TEXT NOT NULL DEFAULT 'WINDOW_OFFERED'
        CHECK (status IN ('WINDOW_OFFERED','ACTIVE','MUTUALLY_ACKNOWLEDGED','REPLAN_REQUIRED','CANCELLED','EXPIRED','STALE')),
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    helper_consent_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    requester_consent_traveler_id TEXT REFERENCES travelers(id) ON DELETE CASCADE,
    helper_consented_at TEXT NOT NULL,
    requester_consented_at TEXT,
    proposed_at TEXT NOT NULL,
    proposal_expires_at TEXT NOT NULL,
    started_at TEXT,
    expires_at TEXT,
    closed_at TEXT,
    outcome_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, helper_member_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_journey_rendezvous_buddy_executions_pair_status_expiry
    ON journey_rendezvous_buddy_executions(
        journey_id, requester_member_id, helper_member_id, status, expires_at
    );

-- A member can make one durable signed self-report for one execution generation.
CREATE TABLE IF NOT EXISTS journey_rendezvous_buddy_execution_receipts (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    execution_id TEXT NOT NULL REFERENCES journey_rendezvous_buddy_executions(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    receipt_kind TEXT NOT NULL
        CHECK (receipt_kind IN ('BUDDY_MET_ACK','CANNOT_MEET','CANCEL_PARTICIPATION')),
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    self_reported_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(execution_id, member_id),
    UNIQUE(execution_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_journey_rendezvous_buddy_execution_receipts_journey
    ON journey_rendezvous_buddy_execution_receipts(journey_id, execution_id, self_reported_at);

-- R81: an exact, write-once authorization receipt for an R80 private location
-- sample. Legacy location observations are intentionally not backfilled; without
-- this receipt they cannot enter a private handoff route.
CREATE TABLE IF NOT EXISTS private_buddy_route_location_bindings (
    observation_id TEXT PRIMARY KEY
        REFERENCES location_observations(id) ON DELETE CASCADE,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    handoff_id TEXT NOT NULL REFERENCES journey_rendezvous_buddy_handoffs(id) ON DELETE CASCADE,
    journey_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    active_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE CASCADE,
    current_activity_id TEXT,
    destination_place_id TEXT NOT NULL,
    destination_place_snapshot_sha256 TEXT NOT NULL
        CHECK (length(destination_place_snapshot_sha256) = 64),
    audience_sha256 TEXT NOT NULL CHECK (length(audience_sha256) = 64),
    handoff_accepted_at TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    bound_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_private_buddy_route_bindings_context_expiry
    ON private_buddy_route_location_bindings(
        journey_id, handoff_id, journey_member_id, traveler_id, expires_at
    );

-- Appends are the only supported write. Parent retention cascades can still purge
-- the entire parent scope, while an existing binding cannot be rewritten in place.
CREATE TRIGGER IF NOT EXISTS trg_private_buddy_route_binding_no_update
    BEFORE UPDATE ON private_buddy_route_location_bindings
    BEGIN
        SELECT RAISE(ABORT, 'private buddy route location binding is immutable');
    END;

-- The ACL table.  A row says which capability a role has and which message key states its scope in
-- one sentence - the words themselves stay in the client's dictionary, because a server sentence
-- reaching a screen is the defect this project keeps having to fix (RELATION:94's shape is a table,
-- not a string).  Seeded once by `db/session.py`, so it is readable without being editable per trip.
CREATE TABLE IF NOT EXISTS journey_role_capabilities (
    role TEXT NOT NULL CHECK (role IN ('OWNER','ADMIN','COLLABORATOR')),
    capability TEXT NOT NULL CHECK (capability IN ('JOURNEY_READ','JOURNEY_UPDATE','JOURNEY_EXECUTION_UPDATE','PLACE_EDIT','MEMBER_MANAGE','SHARE_GRANT_MANAGE')),
    scope_message_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (role, capability)
);

-- R74: a collaborator may answer only one explicitly accepted shared-stop round.
-- The grant is Journey-, invitation-, base-plan-, member- and grantor-bound; the
-- proposal id and decision epoch are attached when R73 opens that exact round.
CREATE TABLE IF NOT EXISTS shared_stop_coplanning_grants (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id) ON DELETE CASCADE,
    invitation_id TEXT NOT NULL REFERENCES member_place_invitations(id) ON DELETE CASCADE,
    base_plan_version_id TEXT NOT NULL REFERENCES plan_versions(id) ON DELETE RESTRICT,
    grantee_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    grantee_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    grantor_member_id TEXT NOT NULL REFERENCES journey_members(id) ON DELETE CASCADE,
    grantor_traveler_id TEXT NOT NULL REFERENCES travelers(id) ON DELETE CASCADE,
    promotion_id TEXT REFERENCES member_place_promotions(id) ON DELETE CASCADE,
    active_slot INTEGER NOT NULL DEFAULT 1,
    purpose TEXT NOT NULL DEFAULT 'R73_SHARED_STOP_ONLY'
        CHECK (purpose = 'R73_SHARED_STOP_ONLY'),
    status TEXT NOT NULL DEFAULT 'OFFERED'
        CHECK (status IN ('OFFERED','ACCEPTED','DECLINED','REVOKED')),
    request_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    declined_at TEXT,
    revoked_at TEXT,
    decision_epoch TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(journey_id, request_key)
);

CREATE INDEX IF NOT EXISTS idx_shared_stop_coplanning_grantee_scope
    ON shared_stop_coplanning_grants(
        journey_id, invitation_id, base_plan_version_id, grantee_member_id, status
    );
CREATE UNIQUE INDEX IF NOT EXISTS ux_shared_stop_coplanning_one_unbound_active_grant
    ON shared_stop_coplanning_grants(
        journey_id, invitation_id, base_plan_version_id, grantee_member_id
    )
    WHERE active_slot = 1;
CREATE INDEX IF NOT EXISTS idx_shared_stop_coplanning_promotion
    ON shared_stop_coplanning_grants(promotion_id, decision_epoch);


CREATE TABLE IF NOT EXISTS simulation_runs (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL UNIQUE REFERENCES journeys(id),
    actor_id TEXT NOT NULL REFERENCES travelers(id),
    city_code TEXT NOT NULL,
    seed INTEGER NOT NULL,
    timezone TEXT NOT NULL,
    virtual_now TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0 CHECK(sequence >= 0),
    status TEXT NOT NULL,
    state_json TEXT NOT NULL DEFAULT '{}',
    history_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simulation_commands (
    id TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id),
    run_id TEXT NOT NULL REFERENCES simulation_runs(id),
    actor_id TEXT NOT NULL REFERENCES travelers(id),
    idempotency_key TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(journey_id, actor_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS demo_pairing_tickets (
    ticket_sha256 TEXT PRIMARY KEY,
    journey_id TEXT NOT NULL REFERENCES journeys(id),
    traveler_id TEXT NOT NULL REFERENCES travelers(id),
    expires_at INTEGER NOT NULL,
    consumed_at INTEGER
);
CREATE TABLE IF NOT EXISTS demo_pairing_attempts (
    bucket TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_city_identities (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id),
    provider TEXT NOT NULL,
    provider_adcode TEXT NOT NULL,
    public_name TEXT NOT NULL,
    source_call_id TEXT NOT NULL REFERENCES provider_calls(id),
    source_sha256 TEXT NOT NULL,
    bound_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simulation_public_city_snapshots (
    provider_adcode TEXT PRIMARY KEY,
    snapshot_json TEXT NOT NULL,
    snapshot_sha256 TEXT NOT NULL,
    published_at TEXT NOT NULL,
    published_by TEXT NOT NULL REFERENCES travelers(id)
);
