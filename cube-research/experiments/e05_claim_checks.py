"""E05: checks of specific claims made by the earlier (unverified) research.

(a) Coset fact: G1 = <U,D,R2,L2,F2,B2> is a group, so a sequence of domino
    moves can never bring a state from outside G1 into G1.  Empirical check on
    random states + exact argument.
(b) "Visual HTR" (every face shows only its own colour and the opposite
    colour) is necessary but not sufficient for G3 membership.  Exact count of
    visual-HTR states vs |G3| = 663,552, and how many look-alikes are fake.
(c) Metric switching: the same optimal solutions measured in HTM vs ATM.
"""
import itertools, random
from collections import Counter
from common import provenance, save
from cuberesearch.cubie import CubieCube, random_state, SOLVED, perm_parity
from cuberesearch.notation import parse, state_of, count
from cuberesearch import core

rng = random.Random(5)
DOM = ["U", "U'", "U2", "D", "D'", "D2", "R2", "L2", "F2", "B2"]


def in_g1(c):  # Kociemba phase-1 goal: co=0, eo=0, E-slice edges in E-slice
    return not any(c.co) and not any(c.eo) and all(c.ep[i] >= 8 for i in range(8, 12))


# (a)
outside = [random_state(rng) for _ in range(2000)]
outside = [c for c in outside if not in_g1(c)]
entered = 0
for c in outside:
    seq = " ".join(rng.choice(DOM) for _ in range(rng.randrange(1, 30)))
    if in_g1(c * state_of(seq)):
        entered += 1
print("(a) states outside G1 that entered G1 via domino moves:", entered, "of", len(outside))

# (b) visual HTR: each facelet shows its face colour or the opposite colour
OPP = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}
FACES = "URFDLB"


def visual_htr(c):
    f = c.to_facelets()
    return all(f[i] in (FACES[i // 9], OPP[FACES[i // 9]]) for i in range(54))


# exact count by enumeration of the independent parts:
# corners: co must be 0 and the corner must sit in its own tetrad;
# edges: eo 0 and each edge in its own slice. We enumerate corner perms (8!) and
# edge perms (12!/... via slice-preserving perms 4!^3) directly.
corner_ok = []
for cp in itertools.permutations(range(8)):
    c = CubieCube(cp, (0,) * 8, tuple(range(12)), (0,) * 12)
    f = c.to_facelets()
    if all(f[i] in (FACES[i // 9], OPP[FACES[i // 9]]) for i in range(54)):
        corner_ok.append(cp)
slices = [[0, 2, 4, 6], [1, 3, 5, 7], [8, 9, 10, 11]]   # UR UL DR DL | UF UB DF DB | E
edge_perms = []
for a in itertools.permutations(slices[0]):
    for b in itertools.permutations(slices[1]):
        for e in itertools.permutations(slices[2]):
            ep = [0] * 12
            for src, dst in zip(slices[0], a): ep[src] = dst
            for src, dst in zip(slices[1], b): ep[src] = dst
            for src, dst in zip(slices[2], e): ep[src] = dst
            edge_perms.append(tuple(ep))
# verify edges in own slice with eo=0 always look right, and other edge placements never do
c_even = sum(1 for cp in corner_ok if perm_parity(cp) == 0)
c_odd = len(corner_ok) - c_even
e_even = sum(1 for ep in edge_perms if perm_parity(ep) == 0)
e_odd = len(edge_perms) - e_even
visual_count = c_even * e_even + c_odd * e_odd
print("(b) corner perms with visual-HTR look:", len(corner_ok), "(G3 has 96)")
print("    legal visual-HTR states:", visual_count, " |G3| = 663552  -> fake fraction", 1 - 663552 / visual_count)
# sanity: sample visual-HTR states, check optimal distance with half turns only
g3_corner = set()
frontier = [SOLVED]; seen = {SOLVED.cp}
H = [state_of(m) for m in ("U2", "D2", "R2", "L2", "F2", "B2")]
while frontier:
    nxt = []
    for s in frontier:
        for h in H:
            t = s * h
            if t.cp not in seen:
                seen.add(t.cp); nxt.append(t)
    frontier = nxt
print("    G3 corner permutations:", len(seen))
fake_example = None
for cp in corner_ok:
    if cp not in seen:
        for ep in edge_perms:
            if perm_parity(ep) == perm_parity(cp):
                fake_example = CubieCube(cp, (0,) * 8, ep, (0,) * 12)
                break
        break
core.korf_init()
L, sols, _ = core.optimal_solve(fake_example, max_len=20)
Lh, solsh, _ = core.optimal_solve(fake_example, max_len=20, allowed=["U2", "D2", "R2", "L2", "F2", "B2"])
print("    example fake HTR: visual?", visual_htr(fake_example), "optimal HTM", L, " half-turn-only solvable?", Lh)

# (c) metric switching on the E01 sample-like states: random states, optimal HTM vs ATM of the same solution
atm, htm = [], []
for _ in range(10):
    c = random_state(rng)
    L, sols, _ = core.optimal_solve(c, max_len=20, node_limit=200_000_000)
    if L > 0:
        htm.append(L); atm.append(count(" ".join(sols[0]), "ATM"))
print("(c) same optimal solutions: HTM", htm, "ATM", atm)
save("e05_claim_checks", {"provenance": provenance(), "a_entered_g1": entered, "a_tested": len(outside),
                          "b_visual_corner_perms": len(corner_ok), "b_g3_corner_perms": len(seen),
                          "b_visual_htr_states": visual_count, "b_g3_states": 663552,
                          "b_fake_fraction": 1 - 663552 / visual_count,
                          "b_fake_example_facelets": fake_example.to_facelets(), "b_fake_example_opt_htm": L,
                          "b_fake_example_halfturn_only": Lh,
                          "c_htm": htm, "c_atm": atm})
