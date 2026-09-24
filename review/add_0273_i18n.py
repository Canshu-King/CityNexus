import io

# ORD-0273: replace the raw error.message concatenation with an i18n message key, and give the
# failure screen an executable next step.  The technical detail (HTTP 200 / text/html etc.) stays
# available to telemetry via data attribute; it never reaches the user sentence.

p = 'frontend/src/i18n/LocaleContext.tsx'
t = io.open(p, encoding='utf-8', newline='').read()
anchor = '"trial.tianjinDemo": "Use the sealed demo trip",'
assert t.count(anchor) == 1
add = (
    '\n'
    '  /* ORD-0273: the sealed-demo read failure is a named product state, not a raw error passthrough.\n'
    '     The technical facts ride in data-* of the element (see V8Experience), never in this sentence. */\n'
    '  "trial.sealedUnreadable": "没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。",\n'
)
t = t.replace(anchor, anchor + add)
zh_anchor = '"trial.tianjinDemo": "使用封存的演示行程",'
assert t.count(zh_anchor) == 1
zh_add = (
    '\n'
    '  "trial.sealedUnreadable": "没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。",\n'
)
t = t.replace(zh_anchor, zh_anchor + zh_add)
io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('i18n: trial.sealedUnreadable added (both locales)')
