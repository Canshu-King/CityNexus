"""ORD-0503 - the generated client must be reproducible from the contract, and the ruler must see it.

Measured on the base `f707e1b3908c9ff4371e4a013242880b7e36045d` before this file existed: the contract
declares 78 component schemas and the checked-in `frontend/src/generated/api.ts` carries 77 -- the missing
one is `V13NamedRejection`, which ORD-0467 put into `contracts/openapi.yaml` without regenerating the
client, and one share-grant description line was stale too.  Nothing caught it, because
`tools/verify_openapi_parity.py` compared only paths and methods (`formal 166; runtime 166; missing 0;
extra 0` -- green, over a client that was wrong).

The arms here are deliberately one positive and two negative, and the negatives are the point: a ruler
that has never been seen to fail on a fabricated case is not measuring anything.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "verify_openapi_parity.py"
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend" / "src" / "generated" / "api.ts"


def _tool():
    """Import the ruler as a module so the arms call the same functions the CLI calls."""

    spec = importlib.util.spec_from_file_location("cnx_parity", TOOL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _contract_schemas() -> dict:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return spec["components"]["schemas"]


def test_the_generated_client_carries_every_component_the_contract_declares() -> None:
    t = _tool()
    formal = t.formal_schemas()
    generated = t.generated_schemas(GENERATED.read_text(encoding="utf-8"))
    missing, extra = t.schema_drift(formal, generated)
    assert missing == [], f"契约声明而生成物里没有的组件（ORD-0467 那一类）：{missing}"
    assert extra == [], f"生成物里有而契约已不声明的组件：{extra}"
    assert len(formal) == len(_contract_schemas()), (
        f"尺读到的组件数与契约自己数的不等：{len(formal)} vs {len(_contract_schemas())}"
    )


def test_a_component_declared_only_in_the_contract_turns_the_ruler_red_and_is_named() -> None:
    """The negative arm: invent a component in the contract, and the ruler must name exactly that one."""

    t = _tool()
    phantom = "Ord0503PhantomSchemaOnlyInContract"
    assert phantom not in _contract_schemas(), "这枚假名已经被用了，反例就不成立"
    formal = t.formal_schemas() | {phantom}
    generated = t.generated_schemas(GENERATED.read_text(encoding="utf-8"))
    missing, extra = t.schema_drift(formal, generated)
    assert missing == [phantom], f"造了一枚只在契约里的组件，尺却没点到它名：missing={missing}"
    assert extra == [], extra


def test_a_component_left_in_the_client_after_contract_removal_is_also_named() -> None:
    """The other direction: a stale client entry is the same class of lie as a missing one."""

    t = _tool()
    formal = t.formal_schemas()
    ghost = "Ord0503GhostInClient"
    generated = t.generated_schemas(GENERATED.read_text(encoding="utf-8")) | {ghost}
    missing, extra = t.schema_drift(formal, generated)
    assert missing == [], missing
    assert extra == [ghost], f"生成物里多出来的一枚没被报出来：extra={extra}"


def test_the_parser_is_scoped_to_components_schemas_and_cannot_be_satisfied_by_other_keys() -> None:
    """`parameters:` and `content:` appear at the same indent inside every operation.

    An unscoped scan finds hundreds of them and would call an empty schemas block healthy, so the arm
    asserts the parsed set equals the contract's set exactly, and that a name which exists only outside
    the region is not in it.
    """

    t = _tool()
    text = GENERATED.read_text(encoding="utf-8")
    parsed = t.generated_schemas(text)
    assert "parameters" not in parsed and "content" not in parsed, sorted(parsed)[:8]
    assert parsed == set(_contract_schemas()), (
        f"区段解析与契约组件集不等：只在解析里={sorted(parsed - set(_contract_schemas()))[:5]} "
        f"只在契约里={sorted(set(_contract_schemas()) - parsed)[:5]}"
    )
    assert text.count("\n        parameters: {") > 100, (
        "这格的前提是 `parameters:` 在别处大量出现；它变了说明生成器形状换了，得重看解析"
    )


def test_the_cli_exits_zero_on_a_reproduced_client_and_one_on_the_base_one() -> None:
    """The gate's own exit code, both ways, against the real file -- not a fixture."""

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    ok = subprocess.run([os.sys.executable, str(TOOL)], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", cwd=ROOT, env=env)
    assert ok.returncode == 0, f"修平之后尺仍报红：{ok.stdout}{ok.stderr}"
    assert "schemas formal 78; generated 78; missing 0; extra 0" in ok.stdout, ok.stdout

    backup = GENERATED.read_bytes()
    try:
        stale = ROOT / "review" / "ord0503" / "api_base_committed.ts"
        if not stale.exists():
            raise AssertionError(f"缺少基线生成物原件 {stale}，反向那半格无法验，先把它交进来")
        GENERATED.write_bytes(stale.read_bytes())
        bad = subprocess.run([os.sys.executable, str(TOOL)], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", cwd=ROOT, env=env)
    finally:
        GENERATED.write_bytes(backup)
    assert bad.returncode == 1, f"把生成物换回基线那份，尺竟然还绿：rc={bad.returncode} {bad.stdout}"
    assert "V13NamedRejection" in bad.stdout, bad.stdout
    assert GENERATED.read_bytes() == backup, "反例跑完没把文件还原，这会污染后面的臂"


def test_the_client_is_byte_for_byte_what_the_declared_toolchain_makes_from_the_contract() -> None:
    """Reproducibility, not "looks right": regenerate and compare bytes.

    Skips with the reason named when the pinned toolchain is not on this machine -- the worktree carries
    no node_modules by design, so this arm runs in a lane export or wherever `CNX_OPENAPI_TS` points.
    """
    import shutil
    import tempfile

    cli = os.environ.get("CNX_OPENAPI_TS")
    node = shutil.which("node")
    if not cli or not node or not os.path.exists(cli):
        raise __import__("pytest").skip(
            f"openapi-typescript 不在这台可达（CNX_OPENAPI_TS={cli!r}, node={bool(node)}）；"
            "本臂需要车道导出目录里的 7.13.0"
        )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "api.ts"
        r = subprocess.run([node, cli, str(CONTRACT), "-o", str(out)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, r.stderr
        regen = io.open(out, encoding="utf-8", errors="replace").read()
    committed = GENERATED.read_text(encoding="utf-8")
    a = regen.replace("\r\n", "\n").rstrip() + "\n"
    b = committed.replace("\r\n", "\n").rstrip() + "\n"
    assert a == b, (
        f"生成物不可由契约复现：重生成 {len(a)} 字符 vs 已入库 {len(b)} 字符，"
        f"首个不同处在 {next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), '长度')} 偏移"
    )
