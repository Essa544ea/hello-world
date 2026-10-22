"""Execution-effort ESTIMATE (uncalibrated).

This is not a model of human time.  It is a transparent heuristic used to ask
"does a conclusion survive a reasonable range of assumptions?".  Every weight
is a guess; `perturbed()` draws random weight sets so every comparison can be
reported with its robustness (fraction of weight sets that agree).

State tracked: right-wrist offset (quarter turns away from home grip, changed
by R/r turns) and the last hand used, to add regrip penalties and reward
hand alternation.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List

from .notation import Move, parse

BASE = {  # cost of a quarter turn; half turn multiplier separate
    "U": 1.0, "R": 1.0, "r": 1.1, "L": 1.15, "l": 1.3, "F": 1.35, "D": 1.35,
    "M": 1.3, "B": 2.0, "f": 1.8, "b": 2.4, "d": 1.8, "u": 1.5, "E": 2.0, "S": 2.0,
}
DEFAULT = {
    **{f"q_{k}": v for k, v in BASE.items()},
    "half_mult": 1.45,        # half turn relative to quarter
    "rotation": 2.2,          # whole-cube rotation (regrip-like)
    "regrip": 2.0,            # wrist leaves comfortable range
    "wrist_range": 1.0,       # allowed |offset| in quarter turns before regrip
    "alt_bonus": 0.15,        # fraction saved when the other hand moves next
}
HAND = {"U": "L", "R": "R", "r": "R", "L": "L", "l": "L", "F": "R", "D": "L", "M": "R",
        "B": "R", "f": "R", "b": "R", "d": "L", "u": "R", "E": "L", "S": "R"}


def cost(moves, p: Dict[str, float] = DEFAULT) -> float:
    moves: List[Move] = parse(moves) if isinstance(moves, str) else moves
    total, wrist, last = 0.0, 0, None
    for m in moves:
        if m.kind == "rotation":
            total += p["rotation"]; wrist = 0; last = None
            continue
        c = p[f"q_{m.base}"] * (p["half_mult"] if m.power == 2 else 1.0)
        if m.base in "Rr":
            wrist += {1: -1, 2: 2 if wrist <= 0 else -2, 3: 1}[m.power]
            if abs(wrist) > p["wrist_range"] + (1 if m.power == 2 else 0):
                c += p["regrip"]; wrist = 0
        h = HAND[m.base]
        if last and h != last:
            c *= 1 - p["alt_bonus"]
        last = h
        total += c
    return total


def perturbed(rng: random.Random, spread: float = 0.5) -> Dict[str, float]:
    """Log-uniform multiplicative perturbation of every weight by up to
    exp(+-spread) (spread=0.5 -> factors 0.61..1.65)."""
    return {k: v * math.exp(rng.uniform(-spread, spread)) for k, v in DEFAULT.items()}
