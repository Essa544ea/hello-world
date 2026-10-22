"""Cubie-level model of the 3x3x3 cube (centre-fixed frame).

Conventions follow Kociemba's published definitions (corner/edge order and
"replaced-by" permutation semantics) so that facelet strings are compatible
with the external `kociemba` reference library:

  corners: URF UFL ULB UBR DFR DLF DBL DRB
  edges:   UR UF UL UB DR DF DL DB FR FL BL BR
  facelet string order: U1..U9 R1..R9 F1..F9 D1..D9 L1..L9 B1..B9

A state stores, for each *position*, which cubie sits there (cp/ep) and its
orientation (co in Z3, eo in Z2).  `a * b` means "apply a, then b".

Slice moves, wide moves and whole-cube rotations are NOT represented by moving
centres.  Instead `Sequence` tracks a frame (which physical face the solver
currently calls U, R, ...).  A slice such as M is executed as R L' plus a frame
change x'.  This keeps the group state at 8 corners + 12 edges while still
supporting every human move type.  The independent sticker model in
`sticker.py` handles these moves geometrically and is used to cross-check.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Sequence as Seq, Tuple

URF, UFL, ULB, UBR, DFR, DLF, DBL, DRB = range(8)
UR, UF, UL, UB, DR, DF, DL, DB, FR, FL, BL, BR = range(12)
CORNER_NAMES = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]
EDGE_NAMES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]
FACES = "URFDLB"

# facelet indices (0..53) of each corner / edge, Kociemba layout
CORNER_FACELETS = [
    (8, 9, 20), (6, 18, 38), (0, 36, 47), (2, 45, 11),
    (29, 26, 15), (27, 44, 24), (33, 53, 42), (35, 17, 51),
]
EDGE_FACELETS = [
    (5, 10), (7, 19), (3, 37), (1, 46), (32, 16), (28, 25), (30, 43), (34, 52),
    (23, 12), (21, 41), (50, 39), (48, 14),
]
CORNER_COLORS = [
    "URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB",
]
EDGE_COLORS = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]


@dataclass(frozen=True)
class CubieCube:
    cp: Tuple[int, ...] = tuple(range(8))
    co: Tuple[int, ...] = (0,) * 8
    ep: Tuple[int, ...] = tuple(range(12))
    eo: Tuple[int, ...] = (0,) * 12

    def __mul__(self, b: "CubieCube") -> "CubieCube":
        a = self
        cp = tuple(a.cp[b.cp[i]] for i in range(8))
        co = tuple((a.co[b.cp[i]] + b.co[i]) % 3 for i in range(8))
        ep = tuple(a.ep[b.ep[i]] for i in range(12))
        eo = tuple((a.eo[b.ep[i]] + b.eo[i]) % 2 for i in range(12))
        return CubieCube(cp, co, ep, eo)

    def inverse(self) -> "CubieCube":
        cp = [0] * 8
        co = [0] * 8
        for i, c in enumerate(self.cp):
            cp[c] = i
        for i in range(8):
            co[i] = (-self.co[cp[i]]) % 3
        ep = [0] * 12
        eo = [0] * 12
        for i, e in enumerate(self.ep):
            ep[e] = i
        for i in range(12):
            eo[i] = self.eo[ep[i]]
        return CubieCube(tuple(cp), tuple(co), tuple(ep), tuple(eo))

    def is_solved(self) -> bool:
        return self == SOLVED

    # ---------------------------------------------------------------- validity
    def validity_errors(self) -> List[str]:
        errs = []
        if sorted(self.cp) != list(range(8)):
            errs.append("corner permutation is not a permutation")
        if sorted(self.ep) != list(range(12)):
            errs.append("edge permutation is not a permutation")
        if sum(self.co) % 3:
            errs.append("corner twist sum != 0 mod 3 (one corner twisted)")
        if sum(self.eo) % 2:
            errs.append("edge flip sum odd (one edge flipped)")
        if not errs and perm_parity(self.cp) != perm_parity(self.ep):
            errs.append("corner and edge permutation parity differ (two pieces swapped)")
        return errs

    def is_valid(self) -> bool:
        return not self.validity_errors()

    # ---------------------------------------------------------------- facelets
    def to_facelets(self) -> str:
        f = [""] * 54
        for i, face in enumerate(FACES):
            f[9 * i + 4] = face
        for pos in range(8):
            cub, ori = self.cp[pos], self.co[pos]
            for k in range(3):
                f[CORNER_FACELETS[pos][(k + ori) % 3]] = CORNER_COLORS[cub][k]
        for pos in range(12):
            cub, ori = self.ep[pos], self.eo[pos]
            for k in range(2):
                f[EDGE_FACELETS[pos][(k + ori) % 2]] = EDGE_COLORS[cub][k]
        return "".join(f)

    @staticmethod
    def from_facelets(s: str) -> "CubieCube":
        """Parse a 54-char facelet string (letters URFDLB, or any 6 symbols whose
        centres define the colour scheme).  Raises ValueError on impossible input."""
        s = s.strip()
        if len(s) != 54:
            raise ValueError(f"need 54 facelets, got {len(s)}")
        centres = [s[9 * i + 4] for i in range(6)]
        if len(set(centres)) != 6:
            raise ValueError("centre colours are not 6 distinct colours")
        tr = {c: FACES[i] for i, c in enumerate(centres)}
        try:
            s = "".join(tr[c] for c in s)
        except KeyError as e:
            raise ValueError(f"unknown colour {e}") from None
        for face in FACES:
            if s.count(face) != 9:
                raise ValueError(f"colour {face} appears {s.count(face)} times, expected 9")
        cp, co, ep, eo = [None] * 8, [0] * 8, [None] * 12, [0] * 12
        for pos in range(8):
            fl = CORNER_FACELETS[pos]
            ori = next((o for o in range(3) if s[fl[o]] in "UD"), None)
            if ori is None:
                raise ValueError(f"corner at {CORNER_NAMES[pos]} has no U/D sticker")
            c1, c2 = s[fl[(ori + 1) % 3]], s[fl[(ori + 2) % 3]]
            for cub in range(8):
                if CORNER_COLORS[cub][1] == c1 and CORNER_COLORS[cub][2] == c2:
                    cp[pos], co[pos] = cub, ori % 3
                    break
            else:
                raise ValueError(f"impossible corner stickers at {CORNER_NAMES[pos]}")
        for pos in range(12):
            a, b = s[EDGE_FACELETS[pos][0]], s[EDGE_FACELETS[pos][1]]
            for cub in range(12):
                if EDGE_COLORS[cub] == a + b:
                    ep[pos], eo[pos] = cub, 0
                    break
                if EDGE_COLORS[cub] == b + a:
                    ep[pos], eo[pos] = cub, 1
                    break
            else:
                raise ValueError(f"impossible edge stickers at {EDGE_NAMES[pos]}")
        cc = CubieCube(tuple(cp), tuple(co), tuple(ep), tuple(eo))
        errs = cc.validity_errors()
        if errs:
            raise ValueError("; ".join(errs))
        return cc


SOLVED = CubieCube()


def perm_parity(p: Seq[int]) -> int:
    p = list(p)
    par = 0
    for i in range(len(p)):
        while p[i] != i:
            j = p[i]
            p[i], p[j] = p[j], p[i]
            par ^= 1
    return par


_BASIC = {
    "U": CubieCube((UBR, URF, UFL, ULB, DFR, DLF, DBL, DRB), (0,) * 8,
                   (UB, UR, UF, UL, DR, DF, DL, DB, FR, FL, BL, BR), (0,) * 12),
    "R": CubieCube((DFR, UFL, ULB, URF, DRB, DLF, DBL, UBR), (2, 0, 0, 1, 1, 0, 0, 2),
                   (FR, UF, UL, UB, BR, DF, DL, DB, DR, FL, BL, UR), (0,) * 12),
    "F": CubieCube((UFL, DLF, ULB, UBR, URF, DFR, DBL, DRB), (1, 2, 0, 0, 2, 1, 0, 0),
                   (UR, FL, UL, UB, DR, FR, DL, DB, UF, DF, BL, BR),
                   (0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0)),
    "D": CubieCube((URF, UFL, ULB, UBR, DLF, DBL, DRB, DFR), (0,) * 8,
                   (UR, UF, UL, UB, DF, DL, DB, DR, FR, FL, BL, BR), (0,) * 12),
    "L": CubieCube((URF, ULB, DBL, UBR, DFR, UFL, DLF, DRB), (0, 1, 2, 0, 0, 2, 1, 0),
                   (UR, UF, BL, UB, DR, DF, FL, DB, FR, UL, DL, BR), (0,) * 12),
    "B": CubieCube((URF, UFL, UBR, DRB, DFR, DLF, ULB, DBL), (0, 0, 1, 2, 0, 0, 2, 1),
                   (UR, UF, UL, BR, DR, DF, DL, BL, FR, FL, UB, DB),
                   (0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1)),
}

# 18 face moves in the order U U2 U' R R2 R' F ... (index = 3*face + power-1)
FACE_MOVES: List[CubieCube] = []
FACE_MOVE_NAMES: List[str] = []
for _f in FACES:
    _m = _BASIC[_f]
    _acc = _m
    for _p, _suf in enumerate(["", "2", "'"]):
        FACE_MOVES.append(_acc)
        FACE_MOVE_NAMES.append(_f + _suf)
        _acc = _acc * _m
MOVE_INDEX = {n: i for i, n in enumerate(FACE_MOVE_NAMES)}


def apply_face_moves(state: CubieCube, moves: Iterable[int]) -> CubieCube:
    for m in moves:
        state = state * FACE_MOVES[m]
    return state


def random_state(rng: random.Random) -> CubieCube:
    """Uniformly random legal state (all 43,252,003,274,489,856,000 equally likely)."""
    while True:
        cp = list(range(8)); rng.shuffle(cp)
        ep = list(range(12)); rng.shuffle(ep)
        if perm_parity(cp) == perm_parity(ep):
            break
    co = [rng.randrange(3) for _ in range(7)]
    co.append((-sum(co)) % 3)
    eo = [rng.randrange(2) for _ in range(11)]
    eo.append(sum(eo) % 2)
    return CubieCube(tuple(cp), tuple(co), tuple(ep), tuple(eo))
