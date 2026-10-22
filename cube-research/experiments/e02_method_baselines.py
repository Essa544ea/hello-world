"""E02: structural baselines.  Each established method skeleton solved with
OPTIMAL moves per step (given earlier steps), on the same uniform random
states (dev split).  Totals are lower bounds for step-by-step execution of
that skeleton, not human times.  Metric: STM (rotations free) and HTM.

usage: python e02_method_baselines.py [N] [split]
"""
import sys, time, statistics as st
from multiprocessing import Pool
from common import provenance, save
from cuberesearch import methods as M, datasets

VARIANTS = {
    "CFOP/fixed": lambda c: M.run_cfop(c, "fixed"),
    "CFOP/fullCN": lambda c: M.run_cfop(c, "full"),
    "ZZ/OCLL+PLL": lambda c: M.run_zz(c, "ocll_pll"),
    "ZZ/COLL+EPLL": lambda c: M.run_zz(c, "coll_epll"),
    "ZZ/ZBLL": lambda c: M.run_zz(c, "zbll"),
    "Petrus/OCLL+PLL": lambda c: M.run_petrus(c, "ocll_pll"),
    "Petrus/ZBLL/neutral": lambda c: M.run_petrus(c, "zbll", neutral=True),
    "Roux/x-neutral": lambda c: M.run_roux(c, "x"),
    "Roux/fullCN": lambda c: M.run_roux(c, "full"),
}


def work(args):
    name, idx, split = args
    c = datasets.uniform(split, idx + 1)[idx]
    t = time.time()
    r = VARIANTS[name](c)
    r["seconds"] = time.time() - t
    r["index"] = idx
    r["variant"] = name
    return r


def summarise(rs):
    out = {}
    for metric in ("STM", "HTM"):
        v = [r[metric] for r in rs]
        out[metric] = {"mean": st.mean(v), "sd": st.pstdev(v), "median": st.median(v), "min": min(v), "max": max(v),
                       "sem": st.pstdev(v) / len(v) ** 0.5}
    steps = {}
    for r in rs:
        for s in r["steps"]:
            steps.setdefault(s["name"], []).append(s["length"])
    out["steps_mean"] = {k: st.mean(v) for k, v in steps.items()}
    out["seconds_mean"] = st.mean(r["seconds"] for r in rs)
    return out


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    split = sys.argv[2] if len(sys.argv) > 2 else "dev"
    prov = provenance(n=N, split=split)
    c0 = datasets.uniform(split, 1)[0]
    for name, f in VARIANTS.items():   # build/load all tables once before forking
        f(c0)
    jobs = [(name, i, split) for name in VARIANTS for i in range(N)]
    with Pool(4) as pool:
        res = pool.map(work, jobs, chunksize=1)
    by = {}
    for r in res:
        by.setdefault(r["variant"], []).append(r)
    summary = {k: summarise(v) for k, v in by.items()}
    for k, v in summary.items():
        print(f"{k:22s} STM {v['STM']['mean']:.2f}±{v['STM']['sem']:.2f}  HTM {v['HTM']['mean']:.2f}  "
              + " ".join(f"{s}={m:.2f}" for s, m in v["steps_mean"].items()), flush=True)
    save(f"e02_method_baselines_{split}_{N}", {"experiment": "e02", "provenance": prov, "summary": summary,
                                               "runs": res})
