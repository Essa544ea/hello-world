"""Exact last-layer (LL) machinery: the group of states with F2L solved.

LL state = (cp[0:4], co[0:4], ep[0:4], eo[0:4]) in Kociemba numbering (U
corners are 0..3, U edges 0..3).  |LL| = 4!*4!/2 * 3^3 * 2^3 = 62,208.

Cases: a solver may turn U before an algorithm (pre-AUF) and after it
(post-AUF), so two states are the same *case* iff s' = U^a * s * U^b.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Sequence, Tuple

from .cubie import CubieCube, SOLVED
from .notation import parse, state_of, count

LLState = Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]
U_POW = [state_of(s) for s in ("", "U", "U2", "U'")]


def is_f2l_solved(c: CubieCube) -> bool:
    return (c.cp[4:] == (4, 5, 6, 7) and c.co[4:] == (0,) * 4 and
            c.ep[4:] == tuple(range(4, 12)) and c.eo[4:] == (0,) * 8)


def key(c: CubieCube) -> LLState:
    return (c.cp[:4], c.co[:4], c.ep[:4], c.eo[:4])


def from_key(k: LLState) -> CubieCube:
    return CubieCube(k[0] + (4, 5, 6, 7), k[1] + (0,) * 4, k[2] + tuple(range(4, 12)), k[3] + (0,) * 8)


def alg_effect(alg: str) -> CubieCube:
    c = state_of(alg)
    if not is_f2l_solved(c):
        raise ValueError(f"not an LL algorithm (breaks F2L): {alg}")
    return c


def enumerate_ll() -> List[LLState]:
    gens = [alg_effect(a) for a in ("U", "R U R' U R U2 R'", "F R U R' U' F'", "R U R' U' R' F R2 U' R' U' R U R' F'")]
    seen = {key(SOLVED)}
    q = deque([SOLVED])
    while q:
        s = q.popleft()
        for g in gens:
            t = s * g
            k = key(t)
            if k not in seen:
                seen.add(k); q.append(t)
    return sorted(seen)


def case_id(c: CubieCube, pre: bool = True, post: bool = True) -> LLState:
    """Canonical representative (lexicographically smallest key) of the case."""
    best = None
    for a in (U_POW if pre else U_POW[:1]):
        for b in (U_POW if post else U_POW[:1]):
            k = key(a * c * b)
            if best is None or k < best:
                best = k
    return best


def cases(states: Iterable[LLState], project=lambda k: k, pre=True, post=True) -> Dict[LLState, int]:
    """Count cases; `project` maps a state to the information a sub-step cares
    about (e.g. orientation only for OLL) before canonicalising."""
    out: Dict = {}
    for k in states:
        c = from_key(k)
        best = None
        for a in (U_POW if pre else U_POW[:1]):
            for b in (U_POW if post else U_POW[:1]):
                pk = project(key(a * c * b))
                if best is None or pk < best:
                    best = pk
        out[best] = out.get(best, 0) + 1
    return out


def orientation_only(k: LLState):
    return (k[1], k[3])


def permutation_only(k: LLState):
    return (k[0], k[2]) if not any(k[1]) and not any(k[3]) else None


def macro_distances(states: Sequence[LLState], algs: Dict[str, str], goal, metric="STM",
                    auf_cost: int = 1) -> Dict[LLState, int]:
    """Exact cheapest cost to reach a goal set using only the given algorithms
    plus free choice of U turns between them (each non-trivial U turn costs
    auf_cost).  Dijkstra backwards from the goal set over the LL group.
    goal(key)->bool.  Returns cost for every state from which the goal is
    reachable."""
    import heapq
    eff = [(alg_effect(a), count(a, metric)) for a in algs.values()]
    # predecessor relation: s * U^a * A == t  =>  s = t * A^-1 * U^-a
    inv = [(e.inverse(), c) for e, c in eff]
    dist: Dict[LLState, int] = {}
    pq = []
    for k in states:
        if goal(k):
            dist[k] = 0
            heapq.heappush(pq, (0, k))
    while pq:
        d, k = heapq.heappop(pq)
        if dist.get(k, 1 << 30) < d:
            continue
        t = from_key(k)
        # final AUF is free here only if counted by caller; we allow U turns as moves
        for a, ua in enumerate(U_POW):
            s = t * ua.inverse()
            nd = d + (auf_cost if a else 0)
            ks = key(s)
            if nd < dist.get(ks, 1 << 30):
                dist[ks] = nd; heapq.heappush(pq, (nd, ks))
        for ie, c in inv:
            s = t * ie
            ks = key(s)
            nd = d + c
            if nd < dist.get(ks, 1 << 30):
                dist[ks] = nd; heapq.heappush(pq, (nd, ks))
    return dist
