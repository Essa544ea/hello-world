"""Move notation, frame tracking and move-count metrics.

Supported tokens (WCA / common speedcubing notation):
  face turns   U D R L F B         (+ suffix '', 2, ', 2')
  wide turns   u d r l f b  or Uw Dw Rw Lw Fw Bw
  slices       M (follows L)  E (follows D)  S (follows F)
  rotations    x (follows R)  y (follows U)  z (follows F)

Metrics (all declared explicitly; nothing is free unless stated):
  HTM  face/wide turn = 1 (any angle); slice = 2; rotation = 0
  QTM  quarter = 1, half = 2; slice counts as two outer quarter turns; rotation = 0
  STM  any face/wide/slice turn = 1 (any angle); rotation = 0
  ETM  every token including rotations = 1 (closest to "number of hand actions")
  ATM  maximal runs of consecutive same-axis turns (outer or slice) count 1; rotation = 0
The *research* comparisons use HTM for computer solutions and STM/ETM for
human methods; a result in one metric is never reported as a result in another.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .cubie import CubieCube, FACE_MOVES, MOVE_INDEX, SOLVED

TOKEN_RE = re.compile(r"([UDRLFB]w|[UDRLFBudrlfbMESxyz])(2'|2|')?")

AXIS = {"U": "y", "D": "y", "E": "y", "u": "y", "d": "y",
        "R": "x", "L": "x", "M": "x", "r": "x", "l": "x",
        "F": "z", "B": "z", "S": "z", "f": "z", "b": "z",
        "x": "x", "y": "y", "z": "z"}

ROT = {
    "x": {"U": "F", "F": "D", "D": "B", "B": "U", "R": "R", "L": "L"},
    "y": {"F": "R", "R": "B", "B": "L", "L": "F", "U": "U", "D": "D"},
    "z": {"U": "L", "L": "D", "D": "R", "R": "U", "F": "F", "B": "B"},
}

# expansion of slices / wide turns into (outer turns, rotation) per quarter turn
EXPAND = {
    "M": ([("R", 1), ("L", -1)], ("x", -1)),
    "E": ([("U", 1), ("D", -1)], ("y", -1)),
    "S": ([("F", -1), ("B", 1)], ("z", 1)),
    "r": ([("L", 1)], ("x", 1)),
    "l": ([("R", 1)], ("x", -1)),
    "u": ([("D", 1)], ("y", 1)),
    "d": ([("U", 1)], ("y", -1)),
    "f": ([("B", 1)], ("z", 1)),
    "b": ([("F", 1)], ("z", -1)),
}


@dataclass(frozen=True)
class Move:
    base: str   # one of UDRLFB udrlfb MES xyz (wide normalised to lowercase)
    power: int  # 1, 2, 3  (3 == prime)

    def __str__(self) -> str:
        return self.base + {1: "", 2: "2", 3: "'"}[self.power]

    @property
    def kind(self) -> str:
        if self.base in "UDRLFB":
            return "face"
        if self.base in "udrlfb":
            return "wide"
        if self.base in "MES":
            return "slice"
        return "rotation"

    def inverse(self) -> "Move":
        return Move(self.base, {1: 3, 2: 2, 3: 1}[self.power])


def parse(seq: str) -> List[Move]:
    seq = seq.replace("’", "'").replace("`", "'")
    out: List[Move] = []
    pos = 0
    for m in TOKEN_RE.finditer(seq):
        gap = seq[pos:m.start()]
        if gap.strip(" \t\n()[],"):
            raise ValueError(f"cannot parse {gap.strip()!r} in {seq!r}")
        pos = m.end()
        base, suf = m.group(1), m.group(2) or ""
        if base.endswith("w"):
            base = base[0].lower()
        power = {"": 1, "2": 2, "2'": 2, "'": 3}[suf]
        out.append(Move(base, power))
    if seq[pos:].strip(" \t\n()[],"):
        raise ValueError(f"cannot parse {seq[pos:].strip()!r}")
    return out


def fmt(moves: List[Move]) -> str:
    return " ".join(str(m) for m in moves)


def invert(moves: List[Move]) -> List[Move]:
    return [Move(m.base, {1: 3, 2: 2, 3: 1}[m.power]) for m in reversed(moves)]


IDENTITY_FRAME = {f: f for f in "URFDLB"}


def rotate_frame(frame: Dict[str, str], axis: str, power: int) -> Dict[str, str]:
    for _ in range(power % 4):
        frame = {k: frame[ROT[axis][k]] for k in frame}
    return frame


def to_face_turns(moves: List[Move], frame: Dict[str, str] | None = None
                  ) -> Tuple[List[int], Dict[str, str]]:
    """Translate any human sequence to centre-fixed face-turn indices (0..17)
    plus the final frame (which physical face the solver now calls U, R, ...)."""
    frame = dict(frame or IDENTITY_FRAME)
    out: List[int] = []

    def face(f: str, p: int):
        p %= 4
        if p:
            out.append(MOVE_INDEX[frame[f] + {1: "", 2: "2", 3: "'"}[p]])

    for m in moves:
        if m.kind == "face":
            face(m.base, m.power)
        elif m.kind == "rotation":
            frame = rotate_frame(frame, m.base, m.power)
        else:
            faces, (rax, rp) = EXPAND[m.base]
            for f, p in faces:
                face(f, p * m.power)
            frame = rotate_frame(frame, rax, rp * m.power)
    return out, frame


def apply(state: CubieCube, seq) -> CubieCube:
    moves = parse(seq) if isinstance(seq, str) else seq
    idx, _ = to_face_turns(moves)
    for i in idx:
        state = state * FACE_MOVES[i]
    return state


def state_of(seq) -> CubieCube:
    return apply(SOLVED, seq)


def count(moves, metric: str) -> int:
    moves = parse(moves) if isinstance(moves, str) else moves
    metric = metric.upper()
    if metric == "ETM":
        return len(moves)
    turns = [m for m in moves if m.kind != "rotation"]
    if metric == "STM":
        return len(turns)
    if metric == "HTM":
        return sum(2 if m.kind == "slice" else 1 for m in turns)
    if metric == "QTM":
        return sum((2 if m.kind == "slice" else 1) * (2 if m.power == 2 else 1) for m in turns)
    if metric == "ATM":
        n, prev = 0, None
        for m in turns:
            if AXIS[m.base] != prev:
                n += 1
            prev = AXIS[m.base]
        return n
    raise ValueError(metric)


def all_metrics(moves) -> Dict[str, int]:
    return {k: count(moves, k) for k in ("HTM", "QTM", "STM", "ETM", "ATM")}


def cancel(moves: List[Move]) -> List[Move]:
    """Merge adjacent same-base turns (U U -> U2, U U' -> nothing).  Also merges
    across a commuting opposite face (U D U -> U2 D).  Rotations untouched."""
    out: List[Move] = []
    for m in moves:
        out.append(m)
        changed = True
        while changed and out:
            changed = False
            last = out[-1]
            # look back past one commuting move on the same axis
            for back in (2, 3):
                if len(out) >= back:
                    cand = out[-back]
                    between = out[-back + 1:-1]
                    if cand.base == last.base and all(
                            AXIS[b.base] == AXIS[last.base] and b.base != last.base
                            and b.kind == "face" == last.kind for b in between):
                        p = (cand.power + last.power) % 4
                        del out[-1]
                        if p:
                            out[-back + 1] = Move(cand.base, p)
                        else:
                            del out[-back + 1]
                        changed = True
                        break
    return out
