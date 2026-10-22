"""E06 (H2): method chains under identical rules (optimal per step, STM),
including hybrids, on the same uniform states.  Also Roux with optimal LSE vs
the human 3-step LSE decomposition (EO -> UL/UR -> 4c).

Algorithm counts are the standard published case counts (also reproduced by
tests/test_ll.py for OLL/PLL/OCLL/COLL/1LLL/ZBLL): they are memorisation
proxies, not measured learning costs.
usage: python e06_chains.py [N] [split]
"""
import sys, time, statistics as st
from multiprocessing import Pool
from common import provenance, save
from cuberesearch import methods as M, datasets

LIB = M.chain_library()
ALGS = {"CFOP": 78, "XCross-CFOP": 78, "EOCross+pairs(RULD)+ZBLL": 493, "EOCross+pairs(RULD)+OCLL+PLL": 28,
        "CFOP+ZBLS-like(EO in last pair)+ZBLL": None,  # ZBLS case count not verified by us "CFOP+1LLL": 3915,
        "Roux/lse-opt": 42, "Roux/lse-steps": 42}
VARIANTS = {k: (lambda c, k=k: M.run_chain(c, LIB[k], k)) for k in LIB}
VARIANTS["Roux/lse-opt"] = lambda c: M.run_roux(c, "x", "opt")
VARIANTS["Roux/lse-steps"] = lambda c: M.run_roux(c, "x", "steps")


def work(args):
    name, idx, split = args
    c = datasets.uniform(split, idx + 1)[idx]
    t = time.time()
    r = VARIANTS[name](c)
    r.update(seconds=time.time() - t, index=idx, variant=name)
    return r


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    split = sys.argv[2] if len(sys.argv) > 2 else "dev"
    prov = provenance(n=N, split=split)
    c0 = datasets.uniform(split, 1)[0]
    for f in VARIANTS.values():
        f(c0)
    M.lse_substep_tables()
    jobs = [(n, i, split) for n in VARIANTS for i in range(N)]
    with Pool(4) as pool:
        res = pool.map(work, jobs, chunksize=1)
    by = {}
    for r in res:
        by.setdefault(r["variant"], []).append(r)
    summary = {}
    for k, rs in by.items():
        v = [r["STM"] for r in rs]
        steps = {}
        for r in rs:
            for s_ in r["steps"]:
                steps.setdefault(s_["name"], []).append(s_["length"])
        summary[k] = {"STM_mean": st.mean(v), "STM_sem": st.pstdev(v) / len(v) ** .5, "algs": ALGS.get(k),
                      "steps_mean": {a: st.mean(b) for a, b in steps.items()},
                      "max_intuitive_step_mean": max(st.mean(b) for a, b in steps.items()
                                                     if a not in ("OLL", "PLL", "OCLL", "ZBLL", "1LLL", "CMLL", "LSE", "EO", "ULUR", "4c"))}
        print(f"{k:42s} STM {summary[k]['STM_mean']:.2f}±{summary[k]['STM_sem']:.2f} algs {ALGS.get(k)} "
              + " ".join(f"{a}={b:.2f}" for a, b in summary[k]["steps_mean"].items()), flush=True)
    save(f"e06_chains_{split}_{N}", {"experiment": "e06", "provenance": prov, "summary": summary, "runs": res})
