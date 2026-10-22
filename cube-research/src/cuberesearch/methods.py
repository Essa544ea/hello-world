"""Method skeletons as sequences of programmable sub-goals.

Every step goal is an exact predicate implemented as a conjunction of pattern
abstractions (see core.Pattern).  For a given state the evaluator finds an
*optimal* solution for each step in turn (given the previous steps are solved),
so the totals are structural lower bounds for a method executed step by step;
humans are not optimal on intuitive steps, and algorithmic steps use fixed
algorithms that are usually longer than optimal.

All final solutions are re-verified with the independent Python cubie model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import core
from .cubie import CubieCube, SOLVED
from .notation import parse, apply as py_apply, count

C_ = {n: i for i, n in enumerate(["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"])}
E_ = {n: i for i, n in enumerate(["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"])}
X_ = {n: i for i, n in enumerate("URFDLB")}

FACE = core.MOVE_NAMES[:18]


def moveset(bases: str) -> List[str]:
    return [b + s for b in bases for s in ("", "2", "'")]


# ---------------------------------------------------------------- C-format states
CState = Tuple[Tuple[int, ...], ...]   # (cp, co, ep, eo, ct)


def cmul(a: CState, b: CState) -> CState:
    cp = tuple(a[0][b[0][i]] for i in range(8))
    co = tuple((a[1][b[0][i]] + b[1][i]) % 3 for i in range(8))
    ep = tuple(a[2][b[2][i]] for i in range(12))
    eo = tuple(a[3][b[2][i]] ^ b[3][i] for i in range(12))
    ct = tuple(a[4][b[4][i]] for i in range(6))
    return (cp, co, ep, eo, ct)


def cinv(a: CState) -> CState:
    cp = [0] * 8; co = [0] * 8; ep = [0] * 12; eo = [0] * 12; ct = [0] * 6
    for i, c in enumerate(a[0]):
        cp[c] = i
    for i in range(8):
        co[i] = (-a[1][cp[i]]) % 3
    for i, e in enumerate(a[2]):
        ep[e] = i
    for i in range(12):
        eo[i] = a[3][ep[i]]
    for i, x in enumerate(a[4]):
        ct[x] = i
    return (tuple(cp), tuple(co), tuple(ep), tuple(eo), tuple(ct))


def from_cubie(c: CubieCube) -> CState:
    return (c.cp, c.co, c.ep, c.eo, (0, 1, 2, 3, 4, 5))


def cseq(moves: Sequence[str]) -> CState:
    return tuple(tuple(x) for x in core.c_apply(SOLVED, list(moves)))


def capply(s: CState, moves: Sequence[str]) -> CState:
    return cmul(s, cseq(moves)) if moves else s


def to_bytes(s: CState):
    import ctypes
    flat = list(s[0]) + list(s[1]) + list(s[2]) + list(s[3]) + list(s[4])
    return (ctypes.c_uint8 * 46)(*flat)


def conjugate(s: CState, rot: Sequence[str]) -> CState:
    """State as seen after physically performing whole-cube rotation `rot`."""
    r = cseq(rot)
    return cmul(cmul(cinv(r), s), r)


ROT_X4 = [[], ["x"], ["x2"], ["x'"]]
# 24 orientations: bring each face to D then each to F
ORIENT24 = [list(a) + list(b) for a in ([], ["x"], ["x2"], ["x'"], ["z"], ["z'"])
            for b in ([], ["y"], ["y2"], ["y'"])]
D_COLOUR6 = [[], ["x"], ["x2"], ["x'"], ["z"], ["z'"]]


# ---------------------------------------------------------------- pattern specs
_cache: Dict[str, core.Pattern] = {}


def pattern(name: str, moves: Sequence[str], corners=(), edges=(), corners_ori=(), edges_ori=(),
            centres=(), targets: Sequence[Sequence[str]] = ((),), edges_pos=(), corners_pos=(),
            edge_groups=(), corner_groups=()) -> core.Pattern:
    """corners/edges/centres: pieces that must be exactly solved (each its own
    class, orientation tracked).  corners_ori/edges_ori: pieces whose
    orientation must be solved but whose identity/position does not matter
    (one shared oriented class).  edges_pos/corners_pos: exact position but
    orientation not tracked (use only when the move set preserves it).
    edge_groups/corner_groups: extra lists of (pieces, oriented) that form one
    indistinguishable class each (e.g. "the four E-slice edges").
    Everything else: one ignored class."""
    key = repr((name, list(moves), corners, edges, corners_ori, edges_ori, centres,
                [list(t) for t in targets], edges_pos, corners_pos, edge_groups, corner_groups))
    if key in _cache:
        return _cache[key]
    ccls, ecls, xcls = [0] * 8, [0] * 12, [0] * 6
    cori, eori = [0, 1], [0, 1]
    for p in corners_ori:
        ccls[C_[p]] = 1
    for p in edges_ori:
        ecls[E_[p]] = 1
    for i, p in enumerate(corners):
        ccls[C_[p]] = 2 + i; cori.append(1)
    for i, p in enumerate(edges):
        ecls[E_[p]] = 2 + i; eori.append(1)
    for i, p in enumerate(edges_pos):
        ecls[E_[p]] = 2 + len(edges) + i; eori.append(0)
    for i, p in enumerate(corners_pos):
        ccls[C_[p]] = 2 + len(corners) + i; cori.append(0)
    for pieces, oriented in edge_groups:
        k = len(eori); eori.append(int(oriented))
        for p in pieces:
            ecls[E_[p]] = k
    for pieces, oriented in corner_groups:
        k = len(cori); cori.append(int(oriented))
        for p in pieces:
            ccls[C_[p]] = k
    for i, p in enumerate(centres):
        xcls[X_[p]] = 1 + i
    # compact class ids so that every class 0..k-1 is non-empty
    def compact(cls, ori):
        used = sorted(set(cls))
        remap = {c: i for i, c in enumerate(used)}
        return [remap[c] for c in cls], [ori[c] if c < len(ori) else 0 for c in used]
    ccls, cori = compact(ccls, cori)
    ecls, eori = compact(ecls, eori)
    xcls, _ = compact(xcls, [0] * 7)
    p = core.Pattern(name, ccls, cori, ecls, eori, xcls, moves, targets)
    _cache[key] = p
    return p


@dataclass
class StepResult:
    name: str
    moves: List[str]
    length: int
    nodes: int
    choice: Optional[str] = None
    alternatives: Optional[Dict[str, int]] = None


def solve_goal(s: CState, pats: Sequence[core.Pattern], max_len=30, node_limit=0, slack=0, max_sol=1):
    best, sols, nodes = core.step_solve(to_bytes(s), pats, max_len=max_len, max_sol=max_sol,
                                        slack=slack, node_limit=node_limit)
    return best, sols, nodes


# ---------------------------------------------------------------- CFOP
CROSS_E = ["DR", "DF", "DL", "DB"]
PAIRS = {"FR": ("DFR", "FR"), "FL": ("DLF", "FL"), "BL": ("DBL", "BL"), "BR": ("DRB", "BR")}
U_C = ["URF", "UFL", "ULB", "UBR"]
U_E = ["UR", "UF", "UL", "UB"]


def cfop_patterns(moves=FACE):
    cross = pattern("cross", moves, edges=CROSS_E)
    pair = {k: pattern(f"xpair_{k}", moves, corners=[c], edges=CROSS_E + [e]) for k, (c, e) in PAIRS.items()}
    oll = pattern("oll_ori", moves, corners_ori=U_C, edges_ori=U_E)
    llc = pattern("ll_corners", moves, corners=U_C)
    lle = pattern("ll_edges", moves, edges=U_E)
    return cross, pair, oll, llc, lle


def run_cfop(state: CubieCube, colour_neutral: str = "fixed", node_limit=0) -> Dict:
    """CFOP with optimal steps: cross, 4 pairs (each time the cheapest remaining
    pair, i.e. the human 'pick the easiest pair' heuristic), OLL (optimal,
    includes pre-AUF), PLL (optimal, includes AUF).  colour_neutral: 'fixed'
    (white=D... i.e. D cross), 'dual' (D or U), 'full' (any of 6 faces)."""
    cross, pair, oll, llc, lle = cfop_patterns()
    orients = {"fixed": [[]], "dual": [[], ["x2"]], "full": D_COLOUR6}[colour_neutral]
    s0 = from_cubie(state)
    L, rot, s, sol, nodes, alts = _choose_orientation(s0, orients, [cross])
    steps = [StepResult("cross", sol, L, nodes, " ".join(rot) or "-", alts)]
    s = capply(s, sol)
    done: List[str] = []
    for k in range(4):
        cand, alts = None, {}
        for key in PAIRS:
            if key in done:
                continue
            pats = [pair[d] for d in done + [key]]
            Lp, sols, nodes = solve_goal(s, pats, node_limit=node_limit)
            if Lp < 0:
                raise RuntimeError(f"pair search failed ({Lp})")
            alts[key] = Lp
            if cand is None or Lp < cand[0]:
                cand = (Lp, key, sols[0], nodes)
        Lp, key, sol, nodes = cand
        steps.append(StepResult(f"pair{k + 1}", sol, Lp, nodes, key, alts))
        s = capply(s, sol)
        done.append(key)
    f2l = [pair[d] for d in done]
    Lo, sols, nodes = solve_goal(s, f2l + [oll], node_limit=node_limit)
    steps.append(StepResult("OLL", sols[0], Lo, nodes)); s = capply(s, sols[0])
    steps.append(final_solve(s, "PLL"))
    return finish_("CFOP-opt/" + colour_neutral, state, rot, steps)


def final_solve(s: CState, name: str) -> StepResult:
    """Last step: exact optimal solve with face moves (Korf solver).  Requires
    centres at home (true for face-move methods)."""
    assert s[4] == (0, 1, 2, 3, 4, 5)
    c = CubieCube(s[0], s[1], s[2], s[3])
    L, sols, nodes = core.optimal_solve(c, max_len=20)
    return StepResult(name, sols[0], L, nodes)


def finish_(method: str, state: CubieCube, rot: Sequence[str], steps: List[StepResult]) -> Dict:
    full = list(rot) + [m for st in steps for m in st.moves]
    ok = py_apply(state, parse(" ".join(full))) == SOLVED
    if not ok:
        raise AssertionError(f"{method}: solution does not solve the state (independent check)")
    return {"method": method, "rotation": " ".join(rot), "steps": [st.__dict__ for st in steps],
            "solution": " ".join(full), "STM": count(" ".join(full), "STM"),
            "HTM": count(" ".join(full), "HTM"), "verified": ok}


ALL_E = list(E_)


def _choose_orientation(s0: CState, orients, pats):
    best, alts = None, {}
    for rot in orients:
        s = conjugate(s0, rot)
        L, sols, nodes = solve_goal(s, pats)
        alts[" ".join(rot) or "-"] = L
        if best is None or L < best[0]:
            best = (L, rot, s, sols[0], nodes)
    return best + (alts,)


def _ll(s: CState, ll: str, steps: List[StepResult], f2l_pats):
    _, _, oll, llc, lle = cfop_patterns()
    if ll == "zbll":                       # one-look LL (EO already solved)
        steps.append(final_solve(s, "ZBLL"))
        return
    if ll == "ocll_pll":
        L, sols, nodes = solve_goal(s, f2l_pats + [oll])
        steps.append(StepResult("OCLL", sols[0], L, nodes)); s = capply(s, sols[0])
        steps.append(final_solve(s, "PLL"))
        return
    if ll == "coll_epll":
        llc_auf = pattern("ll_corners_auf", FACE, corners=U_C, targets=[[], ["U"], ["U2"], ["U'"]])
        L, sols, nodes = solve_goal(s, f2l_pats + [oll, llc_auf])
        steps.append(StepResult("COLL", sols[0], L, nodes)); s = capply(s, sols[0])
        steps.append(final_solve(s, "EPLL"))
        return
    raise ValueError(ll)


def run_zz(state: CubieCube, ll: str = "ocll_pll", orients=((),)) -> Dict:
    """ZZ with optimal steps: EOLine (face moves), left/right 1x2x3 blocks in
    <R,U,L> (cheaper block first), then last layer."""
    eoline = pattern("eoline", FACE, edges=["DF", "DB"], edges_ori=[e for e in ALL_E if e not in ("DF", "DB")])
    L, rot, s, sol, nodes, alts = _choose_orientation(from_cubie(state), [list(o) for o in orients], [eoline])
    steps = [StepResult("EOLine", sol, L, nodes, " ".join(rot) or "-", alts)]
    s = capply(s, sol)
    RUL = moveset("RUL")
    lb = pattern("zz_lb", RUL, corners=["DLF", "DBL"], edges_pos=["DF", "DB", "DL", "FL", "BL"])
    rb = pattern("zz_rb", RUL, corners=["DFR", "DRB"], edges_pos=["DF", "DB", "DR", "FR", "BR"])
    first, alts = None, {}
    for name, p in (("LB", lb), ("RB", rb)):
        Lb, sols, nodes = solve_goal(s, [p])
        alts[name] = Lb
        if first is None or Lb < first[0]:
            first = (Lb, name, p, sols[0], nodes)
    Lb, name, p, sol, nodes = first
    steps.append(StepResult("block1", sol, Lb, nodes, name, alts)); s = capply(s, sol)
    Lb, sols, nodes = solve_goal(s, [lb, rb])
    steps.append(StepResult("block2", sols[0], Lb, nodes)); s = capply(s, sols[0])
    _, pair, _, _, _ = cfop_patterns()
    _ll(s, ll, steps, list(pair.values()))
    return finish_(f"ZZ-opt/{ll}", state, rot, steps)


# 8 orientations that bring each corner to DBL (2x2x2 location for Petrus)
CORNER8 = [[], ["y"], ["y2"], ["y'"], ["x2"], ["x2", "y"], ["x2", "y2"], ["x2", "y'"]]


def run_petrus(state: CubieCube, ll: str = "ocll_pll", neutral: bool = False) -> Dict:
    """Petrus with optimal steps: 2x2x2 (at DBL; or best of 8 if neutral),
    expand to 2x2x3, EO, finish F2L in <R,U>, last layer."""
    p222 = pattern("p222", FACE, corners=["DBL"], edges=["DL", "DB", "BL"])
    p223 = pattern("p223", FACE, corners=["DLF", "DBL"], edges=["DL", "DF", "FL"])
    eo = pattern("eo_all", FACE, edges_ori=ALL_E)
    orients = CORNER8 if neutral else [[]]
    L, rot, s, sol, nodes, alts = _choose_orientation(from_cubie(state), orients, [p222])
    steps = [StepResult("2x2x2", sol, L, nodes, " ".join(rot) or "-", alts)]
    s = capply(s, sol)
    L, sols, nodes = solve_goal(s, [p222, p223]); steps.append(StepResult("2x2x3", sols[0], L, nodes)); s = capply(s, sols[0])
    L, sols, nodes = solve_goal(s, [p222, p223, eo]); steps.append(StepResult("EO", sols[0], L, nodes)); s = capply(s, sols[0])
    RU = moveset("RU")
    pf = pattern("petrus_f2l", RU, corners=["DFR", "DRB"], edges_pos=["DR", "FR", "BR"])
    L, sols, nodes = solve_goal(s, [pf]); steps.append(StepResult("F2L-RU", sols[0], L, nodes)); s = capply(s, sols[0])
    _, pair, _, _, _ = cfop_patterns()
    _ll(s, ll, steps, list(pair.values()))
    return finish_(f"Petrus-opt/{ll}{'/neutral' if neutral else ''}", state, rot, steps)


# ---------------------------------------------------------------- Roux
ROUX_MOVES = moveset("RLUDFBMr")
L_COLOUR6 = [[], ["y2"], ["y"], ["y'"], ["z"], ["z'"]]


class ReachTable:
    """Exact distance table for a small restricted-move subgroup coset, built by
    BFS from goal states over full C-format states (hash map)."""

    def __init__(self, moves: Sequence[str], targets: Sequence[Sequence[str]] = (), target_states=()):
        self.moves = list(moves)
        self.mv = [cseq([m]) for m in self.moves]
        self.dist: Dict[CState, int] = {}
        frontier = []
        for s in list(target_states) + [cseq(list(t)) for t in targets]:
            if s not in self.dist:
                self.dist[s] = 0
                frontier.append(s)
        d = 0
        while frontier:
            nxt = []
            for s in frontier:
                for m in self.mv:
                    t = cmul(s, m)
                    if t not in self.dist:
                        self.dist[t] = d + 1
                        nxt.append(t)
            frontier, d = nxt, d + 1

    def solve(self, s: CState) -> List[str]:
        d = self.dist[s]
        out = []
        while d:
            for name, m in zip(self.moves, self.mv):
                t = cmul(s, m)
                if self.dist.get(t, 99) == d - 1:
                    out.append(name); s = t; d -= 1
                    break
        return out


_lse = None
_lse_steps = None


def lse_substep_tables():
    """Human LSE decomposition (blocks at the bottom), each goal an exact set:
    EO   = all edges oriented relative to the U/D centres: for some k, applying
           M^k puts the U/D centres on U/D and leaves every edge oriented;
    ULUR = EO done and the rest finishable with <M, U2>;   4c = solved."""
    global _lse_steps
    if _lse_steps is None:
        mu = moveset("MU")
        full = ReachTable(mu, [[]])
        mk = [cseq([]), cseq(["M"]), cseq(["M2"]), cseq(["M'"])]
        home, m2c = cseq([])[4], cseq(["M2"])[4]

        def eo_done(x):
            for m in mk:
                y = cmul(x, m)
                if y[4] in (home, m2c) and not any(y[3]):
                    return True
            return False
        g_eo = {x for x in full.dist if eo_done(x)}
        g_ulur = set(ReachTable(["M", "M2", "M'", "U2"], [[]]).dist)
        _lse_steps = [("EO", ReachTable(mu, target_states=g_eo)),
                      ("ULUR", ReachTable(mu, target_states=g_eo & g_ulur)),
                      ("4c", full)]
    return _lse_steps


def run_roux(state: CubieCube, neutral: str = "x", lse: str = "opt", cmll_slack: int = -1) -> Dict:
    """Roux with optimal steps: FB (1x2x3 on L; the 4 x-rotations allowed, i.e.
    any bottom colour), SB, CMLL (optimal, includes AUF), LSE in <M,U>
    (optimal).  neutral='x' (L colour fixed) or 'full' (any L colour)."""
    global _lse
    X4 = ROT_X4
    fb = pattern("roux_fb", ROUX_MOVES, corners=["DLF", "DBL"], edges=["DL", "FL", "BL"], targets=X4)
    sb = pattern("roux_sb", ROUX_MOVES, corners=["DFR", "DRB"], edges=["DR", "FR", "BR"], targets=X4)
    pc = pattern("roux_couple", ROUX_MOVES, corners=["DLF", "DFR"], edges=["DL", "DR"], targets=X4)
    cm = pattern("roux_cmll", ROUX_MOVES, corners=U_C, targets=X4)
    orients = L_COLOUR6 if neutral == "full" else [[]]
    L, rot, s, sol, nodes, alts = _choose_orientation(from_cubie(state), orients, [fb])
    steps = [StepResult("FB", sol, L, nodes, " ".join(rot) or "-", alts)]
    s = capply(s, sol)
    L, sols, nodes = solve_goal(s, [fb, sb, pc]); steps.append(StepResult("SB", sols[0], L, nodes)); s = capply(s, sols[0])
    if _lse is None:
        _lse = ReachTable(moveset("MU"), [[]])
    if cmll_slack < 0:
        L, sols, nodes = solve_goal(s, [fb, sb, pc, cm]); steps.append(StepResult("CMLL", sols[0], L, nodes)); s = capply(s, sols[0])
    else:
        # joint choice: among CMLL solutions up to optimal+slack, take the one minimising CMLL + optimal LSE
        L, sols, nodes = solve_goal(s, [fb, sb, pc, cm], slack=cmll_slack, max_sol=5000)

        def lse_len(x):
            for r in X4:
                xr = capply(x, r)
                if xr in _lse.dist:
                    return _lse.dist[xr]
            raise AssertionError
        best = min(sols, key=lambda q: len(q) + lse_len(capply(s, q)))
        steps.append(StepResult("CMLL", best, len(best), nodes, None, {"greedy_first": len(sols[0]) + lse_len(capply(s, sols[0])),
                                                                     "joint": len(best) + lse_len(capply(s, best)), "candidates": len(sols)}))
        s = capply(s, best)
    for r in X4:                      # physically rotate the blocks to the bottom (0 STM)
        sr = capply(s, r)
        if sr in _lse.dist:
            break
    else:
        raise AssertionError("LSE state not in <M,U> coset")
    if lse == "opt":
        sol = _lse.solve(sr)
        steps.append(StepResult("LSE", list(r) + sol, len(sol), 0, " ".join(r) or "-"))
    else:
        first = True
        for name, tab in lse_substep_tables():
            sol = tab.solve(sr)
            steps.append(StepResult(name, (list(r) if first else []) + sol, len(sol), 0))
            sr = capply(sr, sol); first = False
    return finish_(f"Roux-opt/{neutral}/lse-{lse}", state, rot, steps)


# ---------------------------------------------------------------- EO -> DR -> HTR -> finish
DR_MOVES = ["U", "U2", "U'", "D", "D2", "D'", "R", "R2", "R'", "L", "L2", "L'", "F2", "B2"]
HTR_MOVES = ["U", "U2", "U'", "D", "D2", "D'", "R2", "L2", "F2", "B2"]
HALF = ["U2", "D2", "R2", "L2", "F2", "B2"]
E_SLICE, M_SLICE, S_SLICE = ["FR", "FL", "BL", "BR"], ["UF", "UB", "DF", "DB"], ["UR", "UL", "DR", "DL"]
_g3_corner_targets = None


def g3_corner_targets() -> List[List[str]]:
    """One half-turn move sequence for each of the 96 corner permutations of G3."""
    global _g3_corner_targets
    if _g3_corner_targets is None:
        mv = {m: cseq([m]) for m in HALF}
        start = cseq([])
        seen = {start[0]: []}
        frontier = [(start, [])]
        while frontier:
            nxt = []
            for st, seq in frontier:
                for m, c in mv.items():
                    t = cmul(st, c)
                    if t[0] not in seen:
                        seen[t[0]] = seq + [m]
                        nxt.append((t, seq + [m]))
            frontier = nxt
        _g3_corner_targets = list(seen.values())
        assert len(_g3_corner_targets) == 96
    return _g3_corner_targets


def run_thistle(state: CubieCube, finish: str = "half", orients=((),)) -> Dict:
    """EO (F/B axis) -> DR (U/D axis, Kociemba G1) -> HTR (G3) -> finish.
    finish='half': finish with half turns only; 'any': optimal with all moves."""
    eo = pattern("eo_all", FACE, edges_ori=ALL_E)
    L, rot, s, sol, nodes, alts = _choose_orientation(from_cubie(state), [list(o) for o in orients], [eo])
    steps = [StepResult("EO", sol, L, nodes, " ".join(rot) or "-", alts)]
    s = capply(s, sol)
    dr = pattern("dr_co_eslice", DR_MOVES, corners_ori=list(C_), edge_groups=[(E_SLICE, False)])
    L, sols, nodes = solve_goal(s, [dr]); steps.append(StepResult("DR", sols[0], L, nodes)); s = capply(s, sols[0])
    hc = pattern("htr_corners", HTR_MOVES, corners_pos=list(C_), targets=g3_corner_targets())
    he = pattern("htr_edges", HTR_MOVES, edge_groups=[(E_SLICE, False), (M_SLICE, False), (S_SLICE, False)])
    L, sols, nodes = solve_goal(s, [hc, he]); steps.append(StepResult("HTR", sols[0], L, nodes)); s = capply(s, sols[0])
    c = CubieCube(s[0], s[1], s[2], s[3])
    if finish == "half":
        Lf, sols, nodes = core.optimal_solve(c, max_len=20, allowed=HALF)
    else:
        Lf, sols, nodes = core.optimal_solve(c, max_len=20)
    steps.append(StepResult("finish", sols[0], Lf, nodes))
    return finish_(f"EO-DR-HTR-opt/{finish}", state, rot, steps)


# ---------------------------------------------------------------- generic chains (H2)
CROSS_SPEC = dict(edges=CROSS_E)
PAIR_SPECS = {k: dict(corners=[c], edges=CROSS_E + [e]) for k, (c, e) in PAIRS.items()}
EO_SPEC = dict(edges_ori=ALL_E)


def _pat(spec: Dict, moves) -> core.Pattern:
    """Pattern for a spec on a move set; the name only depends on the spec so
    tables are shared between chains."""
    import hashlib
    h = hashlib.sha1(repr(sorted((k, tuple(v)) for k, v in spec.items())).encode()).hexdigest()[:8]
    return pattern(f"spec{h}", moves, **spec)


OLL_SPEC = dict(corners_ori=U_C, edges_ori=U_E)
OCLL_SPEC = dict(corners_ori=U_C)


def run_chain(state: CubieCube, chain: List[Dict], label: str, orients=((),)) -> Dict:
    """Evaluate a method given as a list of steps (face moves only, centres fixed).
    step = {"name", "moves": list, "options": {opt_label: [spec, ...]}, "repeat": n}
    Each option is a list of pattern specs whose conjunction is the option's goal.
    The cheapest option is taken (the 'pick the easiest' rule); with repeat=n,
    n options are consumed one by one.  Options already satisfied by earlier goals
    are skipped.  Goals of all earlier steps are kept, so nothing is undone.
    {"name": X, "final": True}: exact optimal finish (Korf, face moves).
    {"name": X, "ll": "oll"|"ocll"|"coll"}: LL sub-step on face moves.
    The first step may be tried in several whole-cube orientations (orients)."""
    s0 = from_cubie(state)
    s = s0
    kept: List[Dict] = []
    kept_keys = set()
    steps: List[StepResult] = []
    best_rot: List[str] = []
    spec_key = lambda sp: repr(sorted((k, tuple(v)) for k, v in sp.items()))
    for si, st in enumerate(chain):
        if st.get("final"):
            for sp in kept + st.get("require", []):      # preconditions must hold exactly
                if _pat(sp, FACE).distance(to_bytes(s)) != 0:
                    raise AssertionError(f"{label}: precondition {sp} not met before {st['name']}")
            steps.append(final_solve(s, st["name"]))
            s = capply(s, steps[-1].moves)
            continue
        if st.get("ll"):
            extra = {"oll": [OLL_SPEC], "ocll": [OCLL_SPEC], "coll": None}[st["ll"]]
            goal = [_pat(sp, FACE) for sp in kept + (extra or [])]
            if st["ll"] == "coll":
                goal.append(pattern("ll_corners_auf", FACE, corners=U_C, targets=[[], ["U"], ["U2"], ["U'"]]))
            L, sols, nodes = solve_goal(s, goal)
            steps.append(StepResult(st["name"], sols[0], L, nodes))
            s = capply(s, sols[0])
            if extra:
                kept += extra
            continue
        moves = st["moves"]
        # an option whose primary goal (first spec) is already achieved is not a real option
        remaining = {k: v for k, v in st["options"].items() if spec_key(v[0]) not in kept_keys}
        for rep in range(st.get("repeat", 1)):
            best, alts = None, {}
            rots = [list(o) for o in orients] if si == 0 else [None]
            for rot in rots:
                base = conjugate(s0, rot) if si == 0 else s
                for olabel, specs in remaining.items():
                    goal = [_pat(sp, moves) for sp in kept + list(specs)]
                    L, sols, nodes = solve_goal(base, goal)
                    if L < 0:
                        raise RuntimeError(f"{label}/{st['name']}/{olabel}: search failed ({L})")
                    key = (" ".join(rot) + ":" if rot else "") + olabel
                    alts[key] = L
                    if best is None or L < best[0]:
                        best = (L, olabel, specs, sols[0], nodes, rot, base)
            L, olabel, specs, sol, nodes, rot, base = best
            if si == 0:
                best_rot = rot or []
                s = base
            steps.append(StepResult(st["name"] + (f"{rep + 1}" if st.get("repeat", 1) > 1 else ""), sol, L, nodes,
                                    olabel, alts if len(alts) > 1 else None))
            s = capply(s, sol)
            for sp in specs:
                if spec_key(sp) not in kept_keys:
                    kept.append(sp); kept_keys.add(spec_key(sp))
            del remaining[olabel]
            remaining = {k: v for k, v in remaining.items() if spec_key(v[0]) not in kept_keys}
            if not remaining:
                break
    return finish_(label, state, best_rot, steps)


def chain_library() -> Dict[str, Tuple[List[Dict], Sequence]]:
    """Named chains (known methods expressed in the chain language + hybrids)."""
    F, RUL, RULD = FACE, moveset("RUL"), moveset("RULD")
    pairs = {"options": {k: [v] for k, v in PAIR_SPECS.items()}, "repeat": 4}
    pairs3 = {"options": {k: [v] for k, v in PAIR_SPECS.items()}, "repeat": 3}
    lib = {
        "CFOP": [dict(name="cross", moves=F, options={"D": [CROSS_SPEC]}), dict(name="pair", moves=F, **pairs),
                 dict(name="OLL", ll="oll"), dict(name="PLL", final=True)],
        "XCross-CFOP": [dict(name="xcross", moves=F, options={k: [v] for k, v in PAIR_SPECS.items()}),
                        dict(name="pair", moves=F, **pairs3), dict(name="OLL", ll="oll"), dict(name="PLL", final=True)],
        "EOCross+pairs(RULD)+ZBLL": [dict(name="EOCross", moves=F, options={"D": [CROSS_SPEC, EO_SPEC]}),
                                     dict(name="pair", moves=RULD, **pairs), dict(name="ZBLL", final=True, require=[EO_SPEC])],
        "EOCross+pairs(RULD)+OCLL+PLL": [dict(name="EOCross", moves=F, options={"D": [CROSS_SPEC, EO_SPEC]}),
                                         dict(name="pair", moves=RULD, **pairs), dict(name="OCLL", ll="ocll"),
                                         dict(name="PLL", final=True)],
        "CFOP+ZBLS-like(EO in last pair)+ZBLL": [dict(name="cross", moves=F, options={"D": [CROSS_SPEC]}),
                                                 dict(name="pair", moves=F, **pairs3),
                                                 dict(name="LS+EO", moves=F, options={k: [v, EO_SPEC] for k, v in PAIR_SPECS.items()}),
                                                 dict(name="ZBLL", final=True, require=[EO_SPEC])],
        "CFOP+1LLL": [dict(name="cross", moves=F, options={"D": [CROSS_SPEC]}), dict(name="pair", moves=F, **pairs),
                      dict(name="1LLL", final=True)],
    }
    return lib
