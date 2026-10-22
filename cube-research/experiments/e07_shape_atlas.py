"""E07: atlas of intermediate shapes ("if I reach a recognisable shape...").

For every shape that is a single pattern abstraction, the reach cost from a
uniformly random cube is EXACT: a uniform random state maps to a uniform
random abstract state (abstract states are cosets of equal size), so the BFS
histogram of the pattern table is the exact distribution.  Fraction of all
states in the shape = (#goal abstract states) / (#reachable abstract states).

Recognition load proxy = number of stickers on the pieces the predicate
mentions (an upper bound on what must be looked at; not a measured time).
"""
import hashlib, json, time
from common import provenance, save
from cuberesearch import methods as M

F = M.FACE
C_ALL, E_ALL = list(M.C_), list(M.E_)
X4 = M.ROT_X4

SHAPES = [
    # name, pattern kwargs, move set label, moves, stickers, preserved-by note
    ("cross (D)", dict(edges=M.CROSS_E), "HTM", F, 8, "U, D, R2/L2/F2/B2 do not preserve; only U and D-layer-free moves: <U, D>"),
    ("xcross (cross + FR pair)", dict(corners=["DFR"], edges=M.CROSS_E + ["FR"]), "HTM", F, 8 + 3 + 2, "<U, L, B, D... only U and moves not touching FR column>"),
    ("F2L pair FR alone (corner+edge solved)", dict(corners=["DFR"], edges=["FR"]), "HTM", F, 5, "U, L, B, D-moves that avoid it"),
    ("2x2x2 at DBL", dict(corners=["DBL"], edges=["DL", "DB", "BL"]), "HTM", F, 3 + 6, "<U, R, F>"),
    ("EO (all 12 edges, F/B axis)", dict(edges_ori=E_ALL), "HTM", F, 24, "<U, D, R, L, F2, B2>"),
    ("EOLine (EO + DF, DB)", dict(edges=["DF", "DB"], edges_ori=[e for e in E_ALL if e not in ("DF", "DB")]), "HTM", F, 24, "<U, R, L>"),
    ("EOCross (EO + 4 D edges)", dict(edges=M.CROSS_E, edges_ori=[e for e in E_ALL if e not in M.CROSS_E]), "HTM", F, 24, "<U> (and D-layer turns break it)"),
    ("CO (all corners oriented, U/D axis)", dict(corners_ori=C_ALL), "HTM", F, 24, "<U, D, R2, L2, F2, B2> (+ conjugates)"),
    ("DR part: CO + E-slice edges in E", dict(corners_ori=C_ALL, edge_groups=[(M.E_SLICE, False)]), "HTM", F, 24 + 8, "<U, D, R2, L2, F2, B2>"),
    ("Roux FB (any of 4 x-rotations)", dict(corners=["DLF", "DBL"], edges=["DL", "FL", "BL"], targets=X4), "STM(Roux moves)", M.ROUX_MOVES, 6 + 6 + 1, "<U, R, M, r>"),
    ("LL corners oriented only (OCLL done, ignoring F2L)", dict(corners_ori=M.U_C), "HTM", F, 4, "many"),
]

if __name__ == "__main__":
    prov = provenance()
    rows = []
    for name, kw, metric, moves, stickers, pres in SHAPES:
        t = time.time()
        p = M.pattern("atlas_" + hashlib.sha1(name.encode()).hexdigest()[:8], moves, **kw)
        h = p.histogram(40)
        tot = sum(h)
        mean = sum(i * v for i, v in enumerate(h)) / tot
        targets = kw.get("targets", [[]])
        preserved = [m for m in moves if all(p.distance(M.to_bytes(M.cseq(list(t) + [m]))) == 0 for t in targets)]
        row = {"shape": name, "preserving_moves": preserved, "metric": metric, "abstract_states": tot, "goal_states": h[0],
               "fraction_of_cube": h[0] / tot, "reach_mean": mean, "reach_max": len(h) - 1,
               "reach_hist": h, "stickers": stickers, "seconds": time.time() - t}
        rows.append(row)
        print(f"{name:52s} frac={h[0]/tot:.3g} reach mean={mean:.3f} max={len(h)-1} stickers={stickers} preserved={' '.join(preserved)}", flush=True)
    save("e07_shape_atlas", {"experiment": "e07", "provenance": prov, "rows": rows})
