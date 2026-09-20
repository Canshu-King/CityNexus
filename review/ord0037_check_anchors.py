import importlib.util, sys

spec = importlib.util.spec_from_file_location(
    "d", "D:/moodle/_qoder_ui_overnight_20260920/review/ord0037_kill_drivers.py"
)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["x", "__none__"]
spec.loader.exec_module(mod)

text = open(mod.PRISTINE, "r", encoding="utf-8", newline="").read()
for name, _port, subs, node in mod.CASES:
    counts = [text.count(old) for old, _new in subs]
    produces_change = [text.replace(old, new, 1) != text for old, new in subs]
    print(f"{name:32s} node={node:32s} counts={counts} changes={produces_change}")
