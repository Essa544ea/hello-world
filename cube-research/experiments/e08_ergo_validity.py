"""E08 (H4): does the uncalibrated ergonomic estimate carry information?

Proxy ground truth: widely used community PLL algorithms (chosen by humans for
execution speed over many years).  For each such PLL case we generate
alternative algorithms for the SAME case (optimal and restricted-generator
solutions from our solver, plus each alg's AUF-conjugate variants are not
needed since we fix the case exactly).  Then we ask where the community alg
ranks among the candidates under (a) STM alone, (b) the ergo estimate with
default weights, (c) 200 randomly perturbed weight sets.

If (b)/(c) do not rank community algs better than (a), the model adds nothing
and must not be used to claim execution-speed advantages.

The community algorithms below are well-known face-turn algorithms; every one
is verified to be a pure LL permutation before use.
"""
import random, statistics as st, time
from multiprocessing import Pool
from common import provenance, save
from cuberesearch import core, ergo, ll
from cuberesearch.notation import parse, invert, fmt, count, state_of

COMMUNITY = {
    "T": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Jb": "R U R' F' R U R' U' R' F R2 U' R'",
    "Y": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    "Ua": "R U' R U R U R U' R' U' R2",
    "Ub": "R2 U R U R' U' R' U' R' U R'",
    "F": "R' U' F' R U R' U' R' F R2 U' R' U' R U R' U R",
    "Ra": "R U' R' U' R U R D R' U' R D' R' U2 R'",
    "Rb": "R2 F R U R U' R' F' R U2 R' U2 R",
}
GENS = {"all": None, "RU": ["R", "R2", "R'", "U", "U2", "U'"],
        "RUF": ["R", "R2", "R'", "U", "U2", "U'", "F", "F2", "F'"],
        "RUD": ["R", "R2", "R'", "U", "U2", "U'", "D", "D2", "D'"],
        "RUL": ["R", "R2", "R'", "U", "U2", "U'", "L", "L2", "L'"]}


def candidates(args):
    name, alg = args
    case = state_of(fmt(invert(parse(alg))))          # the state this alg solves
    out = {}
    for g, allowed in GENS.items():
        best, sols, nodes = core.optimal_solve(case, max_len=19, max_sol=60, slack=0,
                                               allowed=allowed, node_limit=300_000_000)
        for s in sols:
            out.setdefault(" ".join(s), g)
    return name, alg, out


if __name__ == "__main__":
    prov = provenance()
    for n, a in COMMUNITY.items():
        e = ll.alg_effect(a)
        assert not any(e.co[:4]) and not any(e.eo[:4]), n
    core.korf_init()
    t0 = time.time()
    with Pool(4) as pool:
        res = pool.map(candidates, list(COMMUNITY.items()))
    rng = random.Random(8)
    weights = [ergo.DEFAULT] + [ergo.perturbed(rng) for _ in range(200)]
    rows = {}
    for name, alg, cands in res:
        cands = dict(cands)
        cands.setdefault(alg, "community")
        algs = list(cands)
        def pct_rank(score):
            sc = {a: score(a) for a in algs}
            return sum(1 for a in algs if sc[a] < sc[alg]) / (len(algs) - 1)
        stm_rank = pct_rank(lambda a: count(a, "STM"))
        ergo_ranks = [pct_rank(lambda a, w=w: ergo.cost(a, w)) for w in weights]
        best_default = min(algs, key=lambda a: ergo.cost(a))
        rows[name] = {"n_candidates": len(algs), "community_alg": alg, "community_STM": count(alg, "STM"),
                      "min_STM_among_candidates": min(count(a, "STM") for a in algs),
                      "rank_frac_by_STM": stm_rank, "rank_frac_by_ergo_default": ergo_ranks[0],
                      "rank_frac_by_ergo_perturbed_median": st.median(ergo_ranks[1:]),
                      "rank_frac_by_ergo_perturbed_p90": sorted(ergo_ranks[1:])[180],
                      "ergo_default_best": best_default, "generators": dict((g, sum(1 for v in cands.values() if v == g)) for g in set(cands.values()))}
        print(name, {k: v for k, v in rows[name].items() if k not in ("generators",)}, flush=True)
    summ = {k: st.mean(r[k] for r in rows.values()) for k in ("rank_frac_by_STM", "rank_frac_by_ergo_default", "rank_frac_by_ergo_perturbed_median")}
    print("mean rank fraction (0 = community alg is the best candidate):", summ)
    save("e08_ergo_validity", {"experiment": "e08", "provenance": prov, "rows": rows, "summary": summ,
                               "seconds": time.time() - t0})
