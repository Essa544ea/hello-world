"""E01b: is there an STM solution of U2 R2 F2 D2 L2 B2 shorter than 6, when
slice (M E S) and wide (u r f d l b) turns are allowed (each = 1 STM)?
Meet-in-the-middle: depth <=3 from the scramble state, depth <=3 from the 24
rotations of the solved cube (centre-tracking C model).  Exhaustive for <=6."""
from common import provenance, save
from cuberesearch import core, methods as M
from cuberesearch.notation import parse, apply as py_apply
from cuberesearch.cubie import SOLVED

MOVES = core.MOVE_NAMES[:45]
mv = {m: M.cseq([m]) for m in MOVES}


def layers(starts, depth):
    seen = {s: [] for s in starts}
    frontier = list(starts)
    by_depth = [dict((s, []) for s in starts)]
    for d in range(depth):
        nxt = {}
        for s in frontier:
            for m, c in mv.items():
                t = M.cmul(s, c)
                if t not in seen:
                    seen[t] = seen[s] + [m]
                    nxt[t] = seen[t]
        frontier = list(nxt)
        by_depth.append(nxt)
    return seen, by_depth


if __name__ == "__main__":
    start = M.cseq(parse("U2 R2 F2 D2 L2 B2") and ["U2", "R2", "F2", "D2", "L2", "B2"])
    goals = [M.cseq(r) for r in M.ORIENT24]
    A, Ad = layers([start], 3)
    B, Bd = layers(goals, 3)
    best = None
    for a in range(4):
        for b in range(4):
            for s, path in Ad[a].items():
                if s in Bd[b]:
                    # path from start, then inverse of path from goal
                    back = [x for x in reversed(Bd[b][s])]
                    inv = [m[0] + {"": "'", "'": "", "2": "2"}[m[1:]] for m in back]
                    sol = path + inv
                    if best is None or len(sol) < len(best):
                        best = sol
    ok = best is not None and py_apply(M.CubieCube(*M.cseq([])[:4]) if False else SOLVED, parse("U2 R2 F2 D2 L2 B2 " + " ".join(best))) == SOLVED
    print("shortest STM found:", len(best) if best else None, best, "verified", ok)
    save("e01b_stm_check", {"provenance": provenance(), "state": "U2 R2 F2 D2 L2 B2", "moves_allowed": MOVES,
                             "shortest_stm": len(best) if best else None, "solution": best, "verified": ok,
                             "exhaustive_up_to": 6})
