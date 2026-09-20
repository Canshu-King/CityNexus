import importlib.util, sys

spec = importlib.util.spec_from_file_location(
    "d", "D:/moodle/_qoder_ui_overnight_20260920/review/ord0038_kill_drivers.py"
)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["x", "__none__"]  # seed pristine, then skip every case
spec.loader.exec_module(mod)

# Check against the WORKING file, because the ORD-0038 change is not committed yet.
text = open(mod.SRC, "r", encoding="utf-8", newline="").read()
for name, _port, subs, node in mod.CASES:
    counts = [text.count(old) for old, _new in subs]
    changed = [text.replace(old, new, 1) != text for old, new in subs]
    print(f"{name:44s} node={node:30s} counts={counts} changes={changed}")
