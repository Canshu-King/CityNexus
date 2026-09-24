import io

p = 'frontend/src/app/V8Experience.tsx'
t = io.open(p, encoding='utf-8', newline='').read()

# 1. import
imp_anchor = 'import { useCandidateRejections } from "../api/candidateRejections";'
imp_add = 'import { useContinuationState } from "../api/useContinuationState";'
assert t.count(imp_anchor) == 1
t = t.replace(imp_anchor, imp_anchor + '\n' + imp_add)

# 2. hook call beside the dropped hook
hook_anchor = 'const dropped = useCandidateRejections(data.journey.id, data.journey.city_code).data ?? [];'
hook_add = (
    '  /* ORD-0269 cell 1: the continuation reveal is derived from a device-local marker joined\n'
    '     against the real agent-feed events.  Its coverage boundary is named, not hidden. */\n'
    '  const { state: continuation, feedReadFailed: continuationFeedFailed } = useContinuationState(\n'
    '    data.journey.id,\n'
    '  );'
)
assert t.count(hook_anchor) == 1
t = t.replace(hook_anchor, hook_anchor + '\n' + hook_add)

io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('hook wired')
