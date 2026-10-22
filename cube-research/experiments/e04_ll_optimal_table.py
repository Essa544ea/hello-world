"""E04: optimal HTM (face turns) solution length, and up to 8 optimal
solutions, for every last-layer state (F2L solved, exact final state — i.e.
the final AUF is included in the count).  States are reduced by conjugation
with y rotations (a length-preserving symmetry): ~15.6k Korf solves.

Output: results/e04_ll_optimal.json.gz  {class_key: [length, [solutions]]}
        plus the length histogram over all 62,208 states.
"""
import gzip, json, sys, time
from collections import Counter
from multiprocessing import Pool
from common import provenance, save, ROOT
from cuberesearch import ll, core, methods as M
from cuberesearch.cubie import CubieCube

ROTS = [[], ["y"], ["y2"], ["y'"]]


def conj_key(k, rot):
    s = M.from_cubie(ll.from_key(k))
    t = M.conjugate(s, rot)
    return (t[0][:4], t[1][:4], t[2][:4], t[3][:4])


def canon(k):
    return min(conj_key(k, r) for r in ROTS)


def solve(k):
    c = ll.from_key(k)
    best, sols, nodes = core.optimal_solve(c, max_len=20, max_sol=8)
    return k, best, [" ".join(s) for s in sols], nodes


if __name__ == "__main__":
    prov = provenance()
    t0 = time.time()
    S = ll.enumerate_ll()
    cls = {}
    for k in S:
        cls.setdefault(canon(k), []).append(k)
    reps = list(cls)
    print("LL states", len(S), "classes under y-conjugation", len(reps), flush=True)
    core.korf_init()
    out = {}
    with Pool(4) as pool:
        for i, (k, best, sols, nodes) in enumerate(pool.imap_unordered(solve, reps, chunksize=8)):
            out[repr(k)] = [best, sols]
            if i % 1000 == 0:
                print(i, f"{time.time()-t0:.0f}s", flush=True)
    hist = Counter()
    for rep, members in cls.items():
        hist[out[repr(rep)][0]] += len(members)
    path = ROOT / "results" / "e04_ll_optimal.json.gz"
    with gzip.open(path, "wt") as f:
        json.dump(out, f)
    n = sum(hist.values())
    save("e04_ll_optimal_summary", {"experiment": "e04", "provenance": prov, "states": n, "classes": len(reps),
                                    "length_hist_all_states": dict(sorted(hist.items())),
                                    "mean_optimal_htm_uniform_LL": sum(k * v for k, v in hist.items()) / n,
                                    "seconds": time.time() - t0})
    print("done", dict(sorted(hist.items())), f"{time.time()-t0:.0f}s")
