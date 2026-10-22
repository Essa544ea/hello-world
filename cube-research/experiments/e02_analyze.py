"""Paired analysis of E02: differences on the same states, bootstrap 95% CI."""
import json, random, statistics as st, sys
from common import ROOT

name = sys.argv[1] if len(sys.argv) > 1 else "e02_method_baselines_dev_50"
d = json.loads((ROOT / "results" / f"{name}.json").read_text())
by = {}
for r in d["runs"]:
    by.setdefault(r["variant"], {})[r["index"]] = r
names = list(by)
rng = random.Random(0)


def ci(diffs, B=4000):
    n = len(diffs)
    bs = sorted(st.mean(rng.choice(diffs) for _ in range(n)) for _ in range(B))
    return bs[int(.025 * B)], bs[int(.975 * B)]


ref = "CFOP/fixed"
lines = [f"# {name}: paired differences vs {ref} (STM; negative = fewer moves)", "",
         "| variant | mean STM | median | p10–p90 | diff vs ref | 95% CI | better/tie/worse |", "|---|---|---|---|---|---|---|"]
for v in names:
    idx = sorted(by[v])
    x = [by[v][i]["STM"] for i in idx]
    q = sorted(x)
    diffs = [by[v][i]["STM"] - by[ref][i]["STM"] for i in idx]
    lo, hi = ci(diffs)
    b = sum(1 for z in diffs if z < 0); t = sum(1 for z in diffs if z == 0); w = sum(1 for z in diffs if z > 0)
    lines.append(f"| {v} | {st.mean(x):.2f} | {st.median(x)} | {q[len(q)//10]}–{q[9*len(q)//10]} | {st.mean(diffs):+.2f} | [{lo:+.2f}, {hi:+.2f}] | {b}/{t}/{w} |")
out = "\n".join(lines)
(ROOT / "results" / f"{name}_paired.md").write_text(out + "\n")
print(out)
