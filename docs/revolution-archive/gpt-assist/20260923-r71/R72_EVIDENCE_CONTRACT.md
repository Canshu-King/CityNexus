# R7.2 evidence contract

Bind product implementation and diagnostic tooling separately:

- product_base_commit: 74005fa8b191511b48df395abda6033fdb93aec3 unless a new product candidate is intentionally created;
- diagnostic_head: current HEAD containing receipts/tools only when applicable.

Each live arm records PRE/POST HEAD, branch, empty porcelain status, product diff from base, disposable DB, destination identity, exact provider objects, provider count, template-eligible count, mobility evidence, planner result, Mission A OPEN, and P7=false.

Keep stdout machine JSON separate from stderr warnings and write JSON as UTF-8.

Preserve three cost states: verified paid, verified free, unknown. Unknown is never known zero. Missing opening facts are never always-open.
