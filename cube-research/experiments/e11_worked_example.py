"""E11: worked, verified example of the 6-algorithm last layer (E10 proposal).
Scramble = inverse of an optimal solution of a seeded random LL state, so the
F2L stays solved.  Each stage: top-view sticker diagram before acting, the
optimal action sequence with the 6 algorithms, and an independent check."""
import heapq, random, json
from common import save, provenance
from e10_beginner_ll import VARIANTS
PROPOSAL = VARIANTS['proposal-7(+Ub)']
from e03_ll_library import STAGES
from cuberesearch import ll, core
from cuberesearch.cubie import SOLVED
from cuberesearch.notation import parse, invert, fmt, count, apply as py_apply, state_of

GRID = [[None, 47, 46, 45, None], [36, 0, 1, 2, 11], [37, 3, 4, 5, 10], [38, 6, 7, 8, 9], [None, 18, 19, 20, None]]


def diagram(c, mode):
    f = c.to_facelets()
    rows = []
    for r in GRID:
        cells = []
        for i in r:
            if i is None:
                cells.append(" ")
            elif mode == "ori":
                cells.append("X" if f[i] == "U" else ".")
            else:
                cells.append(f[i] if i >= 9 else ("X" if f[i] == "U" else "."))
        rows.append(" ".join(cells))
    return "\n".join(rows)


def solve_stage(k, stage, named):
    dom, proj, goal = STAGES[stage]
    acts = [("U", ll.U_POW[1], 1), ("U2", ll.U_POW[2], 1), ("U'", ll.U_POW[3], 1)] + \
           [(n, ll.alg_effect(a), count(a, "STM")) for n, a in named.items()]
    pq, seen, tie = [(0, 0, k, [])], {}, 0
    while pq:
        d, _, kk, path = heapq.heappop(pq)
        if goal(proj(kk)):
            return d, path
        if seen.get(kk, 1 << 30) <= d:
            continue
        seen[kk] = d
        c = ll.from_key(kk)
        for n, e, w in acts:
            tie += 1
            heapq.heappush(pq, (d + w, tie, ll.key(c * e), path + [n]))


if __name__ == "__main__":
    S = ll.enumerate_ll()
    rng = random.Random(2026)
    names = {n: a for st in PROPOSAL.values() for n, a in st.items()}
    while True:
        k = rng.choice(S)
        if any(k[3]) and any(k[1]) and k[0] != (0, 1, 2, 3):
            break
    c = ll.from_key(k)
    core.korf_init()
    L, sols, _ = core.optimal_solve(c, max_len=20)
    scramble = fmt(invert(parse(" ".join(sols[0]))))
    assert py_apply(SOLVED, parse(scramble)) == c
    out = {"provenance": provenance(), "scramble": scramble, "stages": []}
    print("SCRAMBLE:", scramble)
    cur = c
    full = []
    for stage, named in PROPOSAL.items():
        mode = "ori" if stage in ("EO", "CO|EO") else "perm"
        d, path = solve_stage(ll.key(cur), stage, named)
        moves = " ".join(names.get(x, x) for x in path)
        before = diagram(cur, mode)
        nxt = cur * state_of(moves) if moves else cur
        print(f"\n== {stage}: cost {d} STM | {' '.join(path)}\n{before}\n-> moves: {moves}")
        out["stages"].append({"stage": stage, "diagram_before": before, "actions": path, "moves": moves, "stm": d})
        full.append(moves)
        cur = nxt
    sol = " ".join(m for m in full if m)
    ok = py_apply(c, parse(sol)) == SOLVED
    print("\nFULL:", sol, "| STM", count(sol, "STM"), "| solved (independent check):", ok,
          "| optimal for this state:", L, "HTM")
    out.update(full_solution=sol, stm=count(sol, "STM"), verified=ok, optimal_htm=L)
    save("e11_worked_example", out)
