"""The browser engine (web/cube.js) must agree with the Python model."""
import json, random, shutil, subprocess
from pathlib import Path

import pytest

from cuberesearch.notation import parse, state_of
from cuberesearch.cubie import random_state, CubieCube

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_matches_python():
    rng = random.Random(9)
    toks = [b + s for b in "UDRLFBudrlfbMESxyz" for s in ("", "2", "'")]
    seqs = [" ".join(rng.choice(toks) for _ in range(rng.randrange(0, 30))) for _ in range(200)]
    states = [random_state(rng).to_facelets() for _ in range(50)]
    bad = states[0][:8] + states[0][9] + states[0][8] + states[0][10:]   # swap two stickers
    js = f"""
const C = require({json.dumps(str(ROOT / 'web' / 'cube.js'))});
const seqs = {json.dumps(seqs)}, states = {json.dumps(states)};
const out = {{
  seq: seqs.map(s => new C.StickerCube().apply(C.parseMoves(s)).facelets()),
  val: states.map(f => C.validateFacelets(f)),
  rt: states.map(f => C.StickerCube.fromFacelets(f).facelets()),
  bad: C.validateFacelets({json.dumps(bad)}),
  metrics: C.METRICS(C.parseMoves("R U2 M x")),
}};
console.log(JSON.stringify(out));
"""
    r = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for s, f in zip(seqs, r["seq"]):
        assert state_of(parse(s)).to_facelets() == f, s
    assert all(v is None for v in r["val"])
    assert r["rt"] == states
    assert r["bad"] is not None
    assert r["metrics"] == {"HTM": 4, "QTM": 5, "STM": 3, "ETM": 4, "ATM": 3}
