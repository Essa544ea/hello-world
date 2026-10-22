"""E10 (H5): a 6-algorithm, 4-look last layer built from E03's findings, using
well-known human-friendly forms of the algorithms.  Exact evaluation over the
uniform LL distribution + the complete decision table (for every situation,
up to the AUF before it, the optimal sequence of AUFs and algorithms).

Compared with the same evaluator: 'beginner-like' (4 algs) and '4LLL' (16).
"""
import json
from collections import defaultdict
from common import provenance, save
from e03_ll_library import STAGES, PRESERVE, REFERENCE, stage_cost, stage_weights, u_moves
from cuberesearch import ll
from cuberesearch.notation import count

PROPOSAL = {
    "EO": {"EO-A": "F R U R' U' F'", "EO-B": "F U R U' R' F'"},
    "CO|EO": {"Sune": "R U R' U R U2 R'", "AntiSune": "R U2 R' U' R U' R'"},
    "CP|ori": {"Aa": "R' F R' B2 R F' R' B2 R2"},
    "EP|ori,CP": {"Ua": "R U' R U R U R U' R' U' R2"},
}
VARIANTS = {
    "proposal-6": PROPOSAL,
    "proposal-7(+Ub)": {**PROPOSAL, "EP|ori,CP": {**PROPOSAL["EP|ori,CP"], "Ub": "R2 U R U R' U' R' U' R' U R'"}},
}
STAGE_AR = {"EO": "توجيه حواف الطبقة العليا", "CO|EO": "توجيه أركانها", "CP|ori": "ترتيب الأركان", "EP|ori,CP": "ترتيب الحواف"}


def policy(stage, named):
    """For each situation (projected start state up to pre-AUF), the optimal
    action sequence (names of algs and U turns).  Dijkstra forward per state."""
    import heapq
    dom, proj, goal = STAGES[stage]
    weights, reps = stage_weights(stage)
    acts = [("U", ll.U_POW[1], 1), ("U2", ll.U_POW[2], 1), ("U'", ll.U_POW[3], 1)] + \
           [(n, ll.alg_effect(a), count(a, "STM")) for n, a in named.items()]
    table = {}
    for p, k in reps.items():
        if goal(p):
            continue
        c0 = ll.from_key(k)
        sit = min(proj(ll.key(c0 * u)) for u in u_moves())
        if sit in table:
            continue
        # search from c0 (any pre-AUF is one of the actions anyway)
        pq, seen = [(0, 0, k, [])], {}
        best = None
        tie = 0
        while pq:
            d, _, kk, path = heapq.heappop(pq)
            if goal(proj(kk)):
                best = (d, path); break
            if seen.get(kk, 1 << 30) <= d:
                continue
            seen[kk] = d
            c = ll.from_key(kk)
            for n, e, w in acts:
                tie += 1
                heapq.heappush(pq, (d + w, tie, ll.key(c * e), path + [n]))
        table[sit] = {"example_state": k, "cost": best[0], "sequence": best[1],
                      "weight": sum(w for q, w in weights.items()
                                    if min(proj(ll.key(ll.from_key(reps[q]) * u)) for u in u_moves()) == sit)}
    return table


if __name__ == "__main__":
    prov = provenance()
    out = {"reference": {}, "variants": {}}
    for name, st in REFERENCE.items():
        rows = {s: stage_cost(s, a)[0] for s, a in st.items()}
        out["reference"][name] = {"algs": sum(len(a) for a in st.values()), "stages": rows, "total": sum(rows.values())}
        print(name, out["reference"][name])
    for vname, st in VARIANTS.items():
        rows, pol = {}, {}
        for stage, named in st.items():
            for a in named.values():
                assert PRESERVE[stage](ll.alg_effect(a)), (stage, a)
            rows[stage] = stage_cost(stage, list(named.values()))[0]
            pol[stage] = policy(stage, named)
        out["variants"][vname] = {"algs": sum(len(v) for v in st.values()), "stages": rows,
                                  "total": sum(rows.values()), "algorithms": st,
                                  "policy": {s: {repr(k): v for k, v in p.items()} for s, p in pol.items()}}
        print(vname, {"algs": out["variants"][vname]["algs"], "stages": rows, "total": sum(rows.values())})
        for s, p in pol.items():
            for sit, v in sorted(p.items(), key=lambda kv: -kv[1]["weight"]):
                print("   ", s, "cost", v["cost"], " ".join(v["sequence"]), "weight", v["weight"])
    save("e10_beginner_ll", {"experiment": "e10", "provenance": prov, **out})
