# CityNexus mobile site map

```text
/v8
├─ setup wizard
│  ├─ step 1: destination, arrival/departure anchors, dates
│  ├─ step 2: travellers, budget, pace, interests
│  └─ step 3: review and create
└─ product shell (after a real journey exists)
   ├─ /v8/hub       Today — current day, attention, stay/status context
   ├─ /v8/live      Live — execution window and current journey state
   ├─ /v8/bookings  Wallet — reservations, import inbox, protected memory
   ├─ /v8/map       Map — geographic context and map interaction surface
   ├─ /v8/agent     Copilot — planning/agent entry
   └─ /v8/me        Me — profile and settings
```

## Golden path used for evidence

```text
/v8 → trial-tianjin-demo → /v8/hub → /v8/live → /v8/bookings
```

The setup blocked-state path intentionally stays before the demo action so the missing-field explanation and sticky Next behavior are tested without fabricating a journey. The seeded product path uses the local isolated backend only.
