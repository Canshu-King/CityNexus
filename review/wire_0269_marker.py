import io

p = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
t = io.open(p, encoding='utf-8', newline='').read()

# 1. import the marker writer
imp_anchor = 'import { useLocale } from "../../i18n/LocaleContext";'
imp_add = 'import { markPendingContinuation } from "../../api/journeyContinuation";'
assert t.count(imp_anchor) == 1
t = t.replace(imp_anchor, imp_anchor + '\n' + imp_add)

# 2. write the marker the moment leg 1 returns a mission id -- BEFORE leg 2 can be sent (clause 1),
#    and never before the request itself is sent (clause 5: the write happens on the RESPONSE path).
old = '''      const body = await response.json().catch(() => null);
      const mission = body?.mission ?? null;'''
new = '''      const body = await response.json().catch(() => null);
      const mission = body?.mission ?? null;
      /* ORD-0269 clause 1: the pending marker is written the moment leg 1 returns a mission id --
         after the response is in hand and before leg 2 could ever be sent.  It is NOT cleared when
         a request goes out (clause 5); only a visible outcome supersedes it. */
      if (mission?.id) {
        markPendingContinuation(journeyId, String(mission.id));
      }'''
assert t.count(old) == 1
t = t.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('marker write wired at the mission response')
