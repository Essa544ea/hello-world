"""Cross-check against an external, independently written solver (the C
`kociemba` package, Kociemba two-phase).  The reference solver only sees the
facelet string of the current state."""
import random

import pytest

from cuberesearch.cubie import random_state, SOLVED
from cuberesearch.notation import parse, state_of, apply
from cuberesearch.sticker import StickerCube

kociemba = pytest.importorskip("kociemba")


def test_external_solver_solutions_solve_our_states():
    rng = random.Random(11)
    for _ in range(60):
        c = random_state(rng)
        sol = kociemba.solve(c.to_facelets())
        assert apply(c, sol) == SOLVED
        # and the sticker model agrees: scramble = inverse(solution)
        sc = StickerCube().apply(parse(sol))
        assert sc.facelets() == c.inverse().to_facelets()


def test_scramble_then_external_solution():
    rng = random.Random(12)
    toks = [f + s for f in "UDRLFB" for s in ("", "2", "'")]
    for _ in range(40):
        scr = " ".join(rng.choice(toks) for _ in range(25))
        c = state_of(scr)
        sol = kociemba.solve(c.to_facelets())
        assert apply(c, sol) == SOLVED
