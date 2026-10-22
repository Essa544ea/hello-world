"""The C core must agree with the Python sticker model on every move type, and
its solutions must verify in the Python cubie model."""
import random

from cuberesearch import core
from cuberesearch.cubie import SOLVED, random_state
from cuberesearch.gen_moves import raw_cubies
from cuberesearch.notation import parse
from cuberesearch.sticker import StickerCube


def test_c_model_matches_sticker_model_all_moves():
    rng = random.Random(7)
    names = core.MOVE_NAMES
    for _ in range(300):
        seq = [rng.choice(names) for _ in range(rng.randrange(0, 25))]
        c = core.c_apply(SOLVED, seq)
        sc = StickerCube().apply(parse(" ".join(seq)))
        assert [list(x) for x in c] == [list(x) for x in raw_cubies(sc)], seq


def test_pattern_cross_distribution_known():
    # Cross (4 D edges, positions+orientation) optimal HTM distribution over all
    # 190,080 cross states is a known result: max 8, mean ~5.81.
    ecls = [0] * 12
    for i, e in enumerate([4, 5, 6, 7]):
        ecls[e] = i + 1
    p = core.Pattern("cross_test", [0] * 8, [0], ecls, [0, 1, 1, 1, 1], [0] * 6, core.MOVE_NAMES[:18])
    h = p.histogram()
    assert sum(h) == 190080
    assert len(h) - 1 == 8
    assert h == [1, 15, 158, 1394, 9809, 46381, 97254, 34966, 102]
