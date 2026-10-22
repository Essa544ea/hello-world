"""E01: exhaustive facts about the half-turn group G3 = <U2,D2,R2,L2,F2,B2>
(= the set of "HTR solved" states), to check claims such as "every HTR state
finishes in 3-5 moves".
 1. BFS over G3 with the 6 half-turn generators (exhaustive, exact).
 2. Optimal HTM with all 18 face moves (Korf IDA*) for every one of the
    depth-15 states and for a seeded uniform sample of G3.
"""
import random, time
from collections import Counter
from multiprocessing import Pool
from common import provenance, save
from cuberesearch.cubie import SOLVED, FACE_MOVES, MOVE_INDEX, CubieCube
from cuberesearch import core

SEED, NSAMPLE = 20261022, 400


def opt(t):
    c = CubieCube(*t)
    best, sols, nodes = core.optimal_solve(c, max_len=20)
    return best, " ".join(sols[0]), nodes


if __name__ == "__main__":
    prov = provenance(seed=SEED)
    H = [MOVE_INDEX[f + "2"] for f in "URFDLB"]
    t0 = time.time()
    dist, frontier, d = {SOLVED: 0}, [SOLVED], 0
    while frontier:
        nxt = []
        for s in frontier:
            for m in H:
                t = s * FACE_MOVES[m]
                if t not in dist:
                    dist[t] = d + 1; nxt.append(t)
        frontier, d = nxt, d + 1
    hist = Counter(dist.values())
    print("G3", len(dist), sorted(hist.items()), f"{time.time()-t0:.0f}s", flush=True)
    deep = [s for s, v in dist.items() if v == max(hist)]
    sample = random.Random(SEED).sample(list(dist), NSAMPLE)
    core.korf_init()
    t1 = time.time()
    with Pool(4) as pool:
        deep_r = pool.map(opt, [(s.cp, s.co, s.ep, s.eo) for s in deep])
        samp_r = pool.map(opt, [(s.cp, s.co, s.ep, s.eo) for s in sample])
    deep_h = Counter(b for b, _, _ in deep_r)
    samp_h = Counter(b for b, _, _ in samp_r)
    print("depth-15 optimal", sorted(deep_h.items()), "sample", sorted(samp_h.items()), f"{time.time()-t1:.0f}s", flush=True)
    le5 = sum(v for k, v in hist.items() if k <= 5)
    p = save("e01_htr_group", {
        "experiment": "e01_htr_group", "provenance": prov,
        "group_size": len(dist), "halfturn_only_distance_hist": dict(sorted(hist.items())),
        "states_within_5_halfturns": le5, "fraction_within_5_halfturns": le5 / len(dist),
        "depth15_count": len(deep), "depth15_optimal_htm_hist": dict(sorted(deep_h.items())),
        "depth15_example": {"solution": deep_r[0][1]},
        "sample_n": NSAMPLE, "sample_optimal_htm_hist": dict(sorted(samp_h.items())),
        "sample_mean_optimal_htm": sum(b for b, _, _ in samp_r) / NSAMPLE,
        "sample_mean_halfturn_only": sum(dist[s] for s in sample) / NSAMPLE,
        "sample_fraction_optimal_le5": sum(1 for b, _, _ in samp_r if b <= 5) / NSAMPLE,
        "seconds": time.time() - t0})
    print("saved", p)
