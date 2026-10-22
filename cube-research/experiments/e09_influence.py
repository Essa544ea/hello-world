"""E09 (H8): upper bound of 'influence' — choosing the CMLL solution to help
LSE.  greedy = first optimal CMLL;  joint0 = best CMLL+LSE among ALL optimal
CMLL solutions;  joint1 = best among solutions up to optimal+1.
Same states for all; LSE cost exact (lookup over the <M,U> coset)."""
import sys, time, statistics as st
from multiprocessing import Pool
from common import provenance, save
from cuberesearch import methods as M, datasets


def work(args):
    idx, split = args
    c = datasets.uniform(split, idx + 1)[idx]
    out = {"index": idx}
    for name, k in (("greedy", -1), ("joint0", 0), ("joint1", 1)):
        t = time.time()
        r = M.run_roux(c, "x", "opt", k)
        st_ = {s["name"]: s["length"] for s in r["steps"]}
        out[name] = {"STM": r["STM"], "CMLL": st_["CMLL"], "LSE": st_["LSE"], "seconds": time.time() - t,
                     "candidates": (r["steps"][2].get("alternatives") or {}).get("candidates")}
    return out


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    split = sys.argv[2] if len(sys.argv) > 2 else "dev"
    prov = provenance(n=N, split=split)
    M.run_roux(datasets.uniform(split, 1)[0], "x", "opt", 0)
    with Pool(4) as pool:
        res = pool.map(work, [(i, split) for i in range(N)], chunksize=1)
    summ = {}
    for name in ("greedy", "joint0", "joint1"):
        summ[name] = {k: st.mean(r[name][k] for r in res) for k in ("STM", "CMLL", "LSE")}
        summ[name]["CMLL+LSE"] = summ[name]["CMLL"] + summ[name]["LSE"]
    d0 = [r["joint0"]["STM"] - r["greedy"]["STM"] for r in res]
    d1 = [r["joint1"]["STM"] - r["greedy"]["STM"] for r in res]
    summ["paired_diff_joint0"] = {"mean": st.mean(d0), "sem": st.pstdev(d0) / len(d0) ** .5}
    summ["paired_diff_joint1"] = {"mean": st.mean(d1), "sem": st.pstdev(d1) / len(d1) ** .5}
    print(summ)
    save(f"e09_influence_{split}_{N}", {"experiment": "e09", "provenance": prov, "summary": summ, "runs": res})
