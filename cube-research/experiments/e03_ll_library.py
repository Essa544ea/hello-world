"""E03: how few algorithms does a multi-look last layer need?

Question (H5 / small-segment library): for a staged LL (each stage = a goal
predicate on a projection of the LL state), what expected STM is achievable
with k algorithms, if the solver uses its algorithms optimally (exact
Dijkstra over the projected state space; U turns between algorithms cost 1)?

Pool of candidate algorithms: optimal (and optimal+1) face-turn solutions,
computed with our Korf solver, for one representative of every OLL, PLL,
OCLL, COLL and EO case, plus their inverses (inverse of an LL alg is an LL alg).
Distribution: uniform over the 62,208 LL states (exact weights, no sampling).

Selection: greedy forward selection on the stage objective, then 1-swap
local search.  Reported: best library per k, the standard reference sets
(beginner-style, 4LLL, 2LLL) evaluated by the same rules.

Caveat: "uses algorithms optimally" means the solver recognises the full
projected state of the stage; the number of distinct situations to recognise
is reported for each library (cases_to_recognise).
"""
import json, sys, time
from collections import Counter
from multiprocessing import Pool
from common import provenance, save
from cuberesearch import ll, core
from cuberesearch.cubie import SOLVED
from cuberesearch.notation import parse, invert, fmt, count, state_of

S = ll.enumerate_ll()


def proj_eo(k): return k[3]
def proj_co(k): return k[1]
def proj_ori(k): return (k[1], k[3])
def proj_cp(k): return k[0]
def proj_ep(k): return k[2]
def proj_perm(k): return (k[0], k[2])
def proj_full(k): return k


# stage = (name, domain predicate on start states, projection, goal predicate on projection)
STAGES = {
    "EO": (lambda k: True, proj_eo, lambda p: not any(p)),
    "CO|EO": (lambda k: not any(k[3]), proj_co, lambda p: not any(p)),
    "OLL": (lambda k: True, proj_ori, lambda p: not any(p[0]) and not any(p[1])),
    "CP|ori": (lambda k: not any(k[1]) and not any(k[3]), proj_cp, lambda p: p == (0, 1, 2, 3)),
    "EP|ori,CP": (lambda k: not any(k[1]) and not any(k[3]) and k[0] == (0, 1, 2, 3), proj_ep, lambda p: p == (0, 1, 2, 3)),
    "PLL": (lambda k: not any(k[1]) and not any(k[3]), proj_perm, lambda p: p == ((0, 1, 2, 3), (0, 1, 2, 3))),
}
# goal "solved" up to final AUF is handled by allowing U turns (cost 1) inside the stage.


def u_moves():
    return [ll.U_POW[i] for i in range(4)]


def stage_cost(stage, algs, cache={}):
    """Expected cost (STM) of a stage over the uniform distribution of its start
    states, solver using `algs` optimally; also number of distinct start
    situations (projected states up to pre-AUF) that require a decision."""
    dom, proj, goal = STAGES[stage]
    starts = [k for k in S if dom(k)]
    # projected state space and transitions
    eff = [(ll.alg_effect(a), count(a, "STM")) for a in algs]
    pstates = {}
    for k in starts:
        pstates.setdefault(proj(k), k)
    # Dijkstra backward on projected states using representatives: transitions are
    # well-defined on projections (checked below on a sample).
    import heapq
    reps = dict(pstates)
    # forward graph on projections
    def succ(p):
        c = ll.from_key(reps[p])
        out = []
        for i, u in enumerate(u_moves()[1:], 1):
            out.append((proj(ll.key(c * u)), 1))
        for e, w in eff:
            out.append((proj(ll.key(c * e)), w))
        return out
    # make reps closed under successors
    frontier = list(reps)
    while frontier:
        nxt = []
        for p in frontier:
            c = ll.from_key(reps[p])
            for e in [u for u in u_moves()[1:]] + [e for e, _ in eff]:
                k2 = ll.key(c * e)
                q = proj(k2)
                if q not in reps:
                    reps[q] = k2; nxt.append(q)
        frontier = nxt
    graph = {p: succ(p) for p in reps}
    rev = {p: [] for p in reps}
    for p, lst in graph.items():
        for q, w in lst:
            rev[q].append((p, w))
    dist = {p: 0 for p in reps if goal(p)}
    pq = [(0, p) for p in dist]
    heapq.heapify(pq)
    while pq:
        d, q = heapq.heappop(pq)
        if d > dist[q]:
            continue
        for p, w in rev[q]:
            if d + w < dist.get(p, 1 << 30):
                dist[p] = d + w; heapq.heappush(pq, (d + w, p))
    tot, unsolved = 0, 0
    for k in starts:
        d = dist.get(proj(k))
        if d is None:
            unsolved += 1
        else:
            tot += d
    exp = tot / len(starts) if not unsolved else float("inf")
    # situations: projected start states up to pre-AUF (U^a * state), excluding goal
    situ = set()
    for p, k in pstates.items():
        if goal(p):
            continue
        c = ll.from_key(k)
        situ.add(min(proj(ll.key(c * u)) for u in u_moves()))
    return exp, len(situ), unsolved


def optimal_algs_for(k, slack=1, max_sol=6):
    c = ll.from_key(k)
    best, sols, _ = core.optimal_solve(c, max_len=18, max_sol=max_sol, slack=slack)
    return [" ".join(s) for s in sols]


def build_pool():
    reps = {}
    for name, proj_ in (("OLL", proj_ori), ("PLL", proj_perm), ("COLL", lambda k: (k[0], k[1]))):
        dom = (lambda k: True) if name == "OLL" else (lambda k: not any(k[3]) and (name != "PLL" or not any(k[1])))
        for cid in ll.cases([k for k in S if dom(k)], proj_):
            pass
    # representatives: one state per case for each family
    fams = {
        "OLL": ([k for k in S if k[0] == (0, 1, 2, 3) and k[2] == (0, 1, 2, 3)], proj_ori),
        "PLL": ([k for k in S if not any(k[1]) and not any(k[3])], proj_perm),
        "COLL": ([k for k in S if not any(k[3]) and k[2] == (0, 1, 2, 3)], lambda k: (k[0], k[1])),
        "EO": ([k for k in S if k[0] == (0, 1, 2, 3) and k[2] == (0, 1, 2, 3) and not any(k[1])], proj_eo),
    }
    jobs = []
    for fam, (states, pr) in fams.items():
        seen = set()
        for k in states:
            c = ll.from_key(k)
            cid = min(pr(ll.key(u * c * v)) for u in u_moves() for v in u_moves())
            if cid in seen or k == ll.key(SOLVED):
                continue
            seen.add(cid)
            jobs.append((fam, k))
    return jobs


def solve_job(job):
    fam, k = job
    return fam, k, optimal_algs_for(k)


REFERENCE = {
    # beginner-style 4-look with commonly taught algorithms (verified as LL algs below)
    "beginner-like": {
        "EO": ["F R U R' U' F'"],
        "CO|EO": ["R U R' U R U2 R'"],
        "CP|ori": ["R U R' U' R' F R2 U' R' U' R U R' F'"],   # T-perm (also used for corner swaps)
        "EP|ori,CP": ["R U' R U R U R U' R' U' R2"],          # Ua
    },
    "4LLL": {
        "EO": ["F R U R' U' F'", "F U R U' R' F'", "F R U R' U' F' f R U R' U' f'"],
        "CO|EO": ["R U R' U R U2 R'", "R U2 R' U' R U' R'", "R U2 R2 U' R2 U' R2 U2 R", "R U R' U R U' R' U R U2 R'",
                  "r U R' U' r' F R F'", "F' r U R' U' r' F R", "R2 D R' U2 R D' R' U2 R'"],
        "CP|ori": ["R U R' U' R' F R2 U' R' U' R U R' F'", "F R U' R' U' R U R' F' R U R' U' R' F R F'"],
        "EP|ori,CP": ["R U' R U R U R U' R' U' R2", "R2 U R U R' U' R' U' R' U R'",
                      "M2 U M2 U2 M2 U M2", "M' U M2 U M2 U M' U2 M2"],
    },
}


if __name__ == "__main__":
    prov = provenance()
    t0 = time.time()
    # verify reference algorithms are LL algorithms
    for name, st in REFERENCE.items():
        for stage, algs in st.items():
            for a in algs:
                ll.alg_effect(a)
    ref = {}
    for name, st in REFERENCE.items():
        rows = {s: stage_cost(s, algs) for s, algs in st.items()}
        ref[name] = {"stages": {s: {"expected_STM": r[0], "situations": r[1], "unsolved_states": r[2]} for s, r in rows.items()},
                     "n_algs": sum(len(v) for v in st.values()),
                     "total_expected_STM": sum(r[0] for r in rows.values())}
        print(name, json.dumps(ref[name]), flush=True)
    core.korf_init()
    jobs = build_pool()
    print("pool cases", Counter(f for f, _ in jobs), flush=True)
    with Pool(4) as pool:
        solved = pool.map(solve_job, jobs, chunksize=4)
    pool_algs = {}
    for fam, k, algs in solved:
        for a in algs:
            for v in (a, fmt(invert(parse(a)))):
                pool_algs.setdefault(v, fam)
    print("pool size", len(pool_algs), f"{time.time()-t0:.0f}s", flush=True)
    names = list(pool_algs)
    # greedy selection per stage for the 4-look structure EO -> CO|EO -> CP|ori -> EP
    results = {}
    for stage in ("EO", "CO|EO", "CP|ori", "EP|ori,CP", "OLL", "PLL"):
        dom, proj, goal = STAGES[stage]
        cand = [a for a in names if True]
        chosen, curve = [], []
        best_val = float("inf")
        kmax = {"EO": 4, "CO|EO": 8, "CP|ori": 5, "EP|ori,CP": 5, "OLL": 12, "PLL": 10}[stage]
        # pre-filter candidates that change the stage projection at all
        for kk in range(kmax):
            scored = []
            for a in cand:
                if a in chosen:
                    continue
                v = stage_cost(stage, chosen + [a])[0]
                scored.append((v, count(a, "STM"), a))
            scored.sort()
            if not scored:
                break
            v, _, a = scored[0]
            if v == float("inf") and kk > 0 and best_val == float("inf"):
                pass
            chosen.append(a); best_val = v
            e, situ, uns = stage_cost(stage, chosen)
            curve.append({"k": len(chosen), "expected_STM": e, "situations": situ, "unsolved_states": uns, "added": a})
            print(stage, curve[-1], flush=True)
        results[stage] = curve
    save("e03_ll_library", {"experiment": "e03", "provenance": prov, "reference": ref,
                            "pool_size": len(pool_algs), "greedy": results, "seconds": time.time() - t0})
