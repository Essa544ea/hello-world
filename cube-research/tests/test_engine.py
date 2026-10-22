import random

import pytest

from cuberesearch.cubie import (CubieCube, FACE_MOVES, SOLVED, random_state,
                                apply_face_moves)
from cuberesearch.notation import (parse, fmt, invert, apply, state_of, count,
                                   to_face_turns, cancel, Move)
from cuberesearch.sticker import StickerCube

ALL_TOKENS = [b + s for b in "UDRLFBudrlfbMESxyz" for s in ("", "2", "'")]


def rand_seq(rng, n, tokens=ALL_TOKENS):
    return parse(" ".join(rng.choice(tokens) for _ in range(n)))


def test_identity_and_orders():
    for b in "UDRLFB":
        m = parse(b)
        assert state_of(m * 4) == SOLVED
        assert state_of(parse(b + "2") * 2) == SOLVED
        assert state_of(m + m[0:1] and parse(b + " " + b + "'")) == SOLVED
    for b in "udrlfbMESxyz":
        assert state_of(parse(b) * 4) == SOLVED
        assert state_of(parse(f"{b}2 {b}2")) == SOLVED


def test_sequence_then_inverse():
    rng = random.Random(1)
    for _ in range(300):
        s = rand_seq(rng, rng.randrange(1, 40))
        assert state_of(s + invert(s)) == SOLVED
        st = StickerCube().apply(s + invert(s))
        assert st.is_solved()


def test_known_orders():
    # well-known facts: (R U) has order 105, sexy move (R U R' U') order 6
    def order(seq):
        g = state_of(seq); s = g; k = 1
        while s != SOLVED:
            s = s * g; k += 1
        return k
    assert order("R U") == 105
    assert order("R U R' U'") == 6
    assert order("R U2 D' B D'") == 1260
    assert order("U2 R2 F2 D2 L2 B2") > 1


def test_cubie_matches_sticker_model_all_move_types():
    rng = random.Random(2)
    for _ in range(500):
        s = rand_seq(rng, rng.randrange(0, 30))
        assert state_of(s).to_facelets() == StickerCube().apply(s).facelets(), fmt(s)


def test_facelet_roundtrip_and_validity():
    rng = random.Random(3)
    for _ in range(500):
        c = random_state(rng)
        assert c.is_valid()
        assert CubieCube.from_facelets(c.to_facelets()) == c
        assert c * c.inverse() == SOLVED


def test_reject_impossible_states():
    c = state_of("R U F")
    f = list(c.to_facelets())
    # twist a single corner (URF facelets 8, 9, 20)
    g = f[:]; g[8], g[9], g[20] = f[9], f[20], f[8]
    with pytest.raises(ValueError, match="twist"):
        CubieCube.from_facelets("".join(g))
    # flip a single edge (UR facelets 5, 10)
    g = f[:]; g[5], g[10] = f[10], f[5]
    with pytest.raises(ValueError, match="flip"):
        CubieCube.from_facelets("".join(g))
    # swap two edges -> parity
    s = SOLVED.to_facelets()
    g = list(s)
    for a, b in [(5, 7), (10, 19)]:   # swap UR and UF stickers
        g[a], g[b] = g[b], g[a]
    with pytest.raises(ValueError, match="parity"):
        CubieCube.from_facelets("".join(g))
    with pytest.raises(ValueError):
        CubieCube.from_facelets("U" * 54)
    with pytest.raises(ValueError):
        CubieCube.from_facelets(s[:53])


def test_colour_scheme_independent_input():
    c = state_of("R U R' F2 D")
    f = c.to_facelets()
    tr = {"U": "W", "R": "R", "F": "G", "D": "Y", "L": "O", "B": "B"}
    assert CubieCube.from_facelets("".join(tr[x] for x in f)) == c


def test_slice_and_rotation_identities():
    # M = R L' x' ; r = R M' ; x = R M' L'
    assert state_of("M") == state_of("R L'")
    _, fr = to_face_turns(parse("M"))
    _, fr2 = to_face_turns(parse("x'"))
    assert fr == fr2
    assert state_of("r U r'") == state_of("L F L'")   # r = L x, so U after r is F
    sc = StickerCube().apply(parse("x y x'"))
    sc2 = StickerCube().apply(parse("z"))  # conjugating y by x gives z
    assert sc.facelets(recentre=False) == sc2.facelets(recentre=False)


def test_metrics():
    assert count("R U2 M", "HTM") == 4
    assert count("R U2 M", "QTM") == 5
    assert count("R U2 M", "STM") == 3
    assert count("R U2 M x", "ETM") == 4
    assert count("R L' U D2 M F", "ATM") == 4
    assert count("x y z", "STM") == 0


def test_cancel():
    assert fmt(cancel(parse("R R"))) == "R2"
    assert fmt(cancel(parse("R R'"))) == ""
    assert fmt(cancel(parse("U D U"))) == "U2 D"
    assert fmt(cancel(parse("R U U' R'"))) == ""
    rng = random.Random(5)
    for _ in range(300):
        s = rand_seq(rng, 20, [b + x for b in "UDRLFB" for x in ("", "2", "'")])
        assert state_of(cancel(s)) == state_of(s)
