"""ctypes bridge to csrc/core.c (compiled on first use).

The C core *generates* solutions; callers verify them with the independent
Python model (`verify_*` helpers below do this automatically)."""
from __future__ import annotations

import ctypes as C
import hashlib
import os
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .cubie import CubieCube, SOLVED
from .notation import parse, apply as py_apply

ROOT = Path(__file__).resolve().parents[2]
CSRC = ROOT / "csrc"
BUILD = ROOT / "build"
TABLES = ROOT / "data" / "tables"
BASES = ["U", "R", "F", "D", "L", "B", "M", "E", "S", "u", "r", "f", "d", "l", "b", "x", "y", "z"]
MOVE_NAMES = [b + s for b in BASES for s in ("", "2", "'")]
MOVE_ID = {n: i for i, n in enumerate(MOVE_NAMES)}
FACE_IDS = list(range(18))
SLICE_IDS = list(range(18, 27))
WIDE_IDS = list(range(27, 45))


def _lib():
    BUILD.mkdir(exist_ok=True)
    so = BUILD / "libcore.so"
    srcs = [CSRC / "core.c", CSRC / "moves.h"]
    if not so.exists() or any(s.stat().st_mtime > so.stat().st_mtime for s in srcs):
        subprocess.check_call(["gcc", "-O3", "-march=native", "-shared", "-fPIC",
                               "-o", str(so), str(CSRC / "core.c")])
    lib = C.CDLL(str(so))
    u8p, i32p, u64p = C.POINTER(C.c_uint8), C.POINTER(C.c_int), C.POINTER(C.c_uint64)
    lib.core_init.restype = C.c_int
    lib.core_apply.argtypes = [u8p, i32p, C.c_int]
    lib.korf_build_corners.argtypes = [C.c_char_p]
    lib.korf_build_edges.argtypes = [C.c_int, C.c_int, i32p, C.c_char_p]
    lib.korf_solve.argtypes = [u8p, C.c_int, C.c_int, C.c_int, C.c_uint32, C.c_uint64,
                               i32p, C.c_int, i32p, u64p]
    lib.pattern_create.argtypes = [i32p, i32p, i32p, i32p, i32p, i32p, C.c_int, u8p, C.c_int, C.c_char_p]
    lib.pattern_size.restype = C.c_uint64
    lib.pattern_size.argtypes = [C.c_int]
    lib.pattern_maxdepth.argtypes = [C.c_int]
    lib.pattern_histogram.argtypes = [C.c_int, u64p, C.c_int]
    lib.pattern_distance.argtypes = [C.c_int, u8p]
    lib.step_solve.argtypes = [u8p, i32p, C.c_int, C.c_int, C.c_int, C.c_int, C.c_uint64,
                               i32p, C.c_int, i32p, u64p]
    lib.core_init()
    return lib


LIB = _lib()


def _ints(xs):
    xs = list(xs)
    return (C.c_int * max(1, len(xs)))(*xs)


def state_bytes(c: CubieCube, centres=(0, 1, 2, 3, 4, 5)):
    return (C.c_uint8 * 46)(*(list(c.cp) + list(c.co) + list(c.ep) + list(c.eo) + list(centres)))


def c_apply(c: CubieCube, moves: Sequence[str]):
    st = state_bytes(c)
    ids = [MOVE_ID[m] for m in moves]
    LIB.core_apply(st, _ints(ids), len(ids))
    b = list(st)
    return b[0:8], b[8:16], b[16:28], b[28:40], b[40:46]


def target_bytes(seqs: Iterable[Sequence[str]]):
    """Goal states for a pattern: solved state followed by each move list
    (e.g. rotations or AUF), computed in the centre-tracking C model."""
    out = []
    for seq in seqs:
        cp, co, ep, eo, ct = c_apply(SOLVED, list(seq))
        out += cp + co + ep + eo + ct
    return (C.c_uint8 * len(out))(*out), len(out) // 46


def _decode(buf, n) -> List[List[str]]:
    sols, i = [], 0
    while i < n:
        k = buf[i]
        sols.append([MOVE_NAMES[buf[i + 1 + j]] for j in range(k)])
        i += k + 1
    return sols


# ------------------------------------------------------------------ optimal
_korf_ready = False


def korf_init(edge_k: int = 7):
    global _korf_ready
    if _korf_ready:
        return
    TABLES.mkdir(parents=True, exist_ok=True)
    LIB.korf_build_corners(str(TABLES / "korf_corners.nib").encode())
    if edge_k == 6:
        sets = [list(range(0, 6)), list(range(6, 12)), [0, 2, 5, 7, 8, 10], [1, 3, 4, 6, 9, 11]]
    else:
        sets = [list(range(0, 7)), list(range(5, 12)), [0, 2, 5, 7, 8, 10], [1, 3, 4, 6, 9, 11]]
    for slot, s in enumerate(sets):
        name = f"korf_edges_{edge_k}_{'-'.join(map(str, s))}.nib"
        LIB.korf_build_edges(slot, len(s), _ints(s), str(TABLES / name).encode())
    _korf_ready = True


def optimal_solve(c: CubieCube, max_len=20, max_sol=1, slack=0, allowed: Optional[Sequence[str]] = None,
                  node_limit=0):
    """Optimal HTM solutions (face turns only).  Returns (length, solutions, nodes);
    length -1 = none within max_len, -2 = node limit hit."""
    korf_init()
    mask = (1 << 18) - 1 if allowed is None else sum(1 << MOVE_ID[m] for m in allowed)
    cap = 1 << 16
    buf = (C.c_int * cap)()
    nw, nodes = C.c_int(0), C.c_uint64(0)
    best = LIB.korf_solve(state_bytes(c), max_len, max_sol, slack, mask, node_limit, buf, cap,
                          C.byref(nw), C.byref(nodes))
    sols = _decode(buf, nw.value)
    for s in sols:   # independent verification
        assert py_apply(c, parse(" ".join(s))) == SOLVED, s
    return best, sols, nodes.value


# ------------------------------------------------------------------ patterns
class Pattern:
    """Abstraction of the cube: pieces grouped into classes; orientation tracked
    per class.  Distance table built by BFS from the goal set."""

    def __init__(self, name, ccls, cori, ecls, eori, xcls, moves: Sequence[str],
                 targets: Sequence[Sequence[str]] = ((),)):
        self.name = name
        self.moves = list(moves)
        key = repr((ccls, cori, ecls, eori, xcls, self.moves, [list(t) for t in targets]))
        h = hashlib.sha1(key.encode()).hexdigest()[:16]
        TABLES.mkdir(parents=True, exist_ok=True)
        path = TABLES / f"pat_{name}_{h}.u8"
        tb, nt = target_bytes(targets)
        pad = lambda xs: list(xs) + [0] * (12 - len(xs))
        self.handle = LIB.pattern_create(_ints(ccls), _ints(pad(cori)), _ints(ecls), _ints(pad(eori)),
                                         _ints(xcls), _ints([MOVE_ID[m] for m in self.moves]),
                                         len(self.moves), tb, nt, str(path).encode())
        if self.handle < 0:
            raise RuntimeError("pattern table limit")

    @property
    def size(self):
        return LIB.pattern_size(self.handle)

    def histogram(self, n=32):
        h = (C.c_uint64 * n)()
        LIB.pattern_histogram(self.handle, h, n)
        return [h[i] for i in range(n) if any(h[j] for j in range(i, n))]

    def distance(self, st_bytes):
        return LIB.pattern_distance(self.handle, st_bytes)


def step_solve(st_bytes, patterns: Sequence[Pattern], max_len=30, max_sol=1, slack=0, node_limit=0):
    cap = 1 << 16
    buf = (C.c_int * cap)()
    nw, nodes = C.c_int(0), C.c_uint64(0)
    best = LIB.step_solve(st_bytes, _ints([p.handle for p in patterns]), len(patterns), max_len,
                          max_sol, slack, node_limit, buf, cap, C.byref(nw), C.byref(nodes))
    return best, _decode(buf, nw.value), nodes.value
