import io

p = 'frontend/src/i18n/LocaleContext.tsx'
t = io.open(p, encoding='utf-8', newline='').read()
en_anchor = '"hub.droppedCandidateUnknownRule": "an unnamed hard condition",'
zh_anchor = '"hub.droppedCandidateUnknownRule": "一条未识别的硬性条件",'
comment = '  // ORD-0269 cells 1 and 3: continuation reveal. On-this-device is the named coverage boundary.'
keys = (
    '  "hub.continuationPending": "上次有一次规划在这台设备上没跑完：前半段已完成，但还没有产出方案。",\n'
    '  "hub.continuationResume": "继续这次规划",\n'
    '  "hub.continuationUnconfirmable": "上次规划有记录，但现在读不到它的进度，无法确认进行到哪一步。",\n'
)
assert t.count(en_anchor) == 1
t = t.replace(en_anchor, en_anchor + '\n' + comment + '\n' + keys)
assert t.count(zh_anchor) == 1
t = t.replace(zh_anchor, zh_anchor + '\n' + comment + '\n' + keys)
io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('i18n keys added to both dictionaries')
