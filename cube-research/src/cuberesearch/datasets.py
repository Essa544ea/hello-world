"""Fixed, seeded datasets.  Splits never overlap in seed space.

  dev   : free use while developing
  tune  : for choosing parameters / candidates
  test  : final, independent evaluation only (log every use in EXPERIMENT_LOG.md)

`uniform` = uniformly random legal states (NOT random-move scrambles).
`movescramble` = random face-move sequences of a given length (a different,
non-uniform distribution; only for specific experiments, labelled as such).
"""
from __future__ import annotations

import random
from typing import List

from .cubie import CubieCube, random_state
from .notation import state_of

SEEDS = {"dev": 1000, "tune": 2000, "test": 3000}


def uniform(split: str, n: int) -> List[CubieCube]:
    rng = random.Random(SEEDS[split] * 1_000_003 + 17)
    return [random_state(rng) for _ in range(n)]


def movescramble(split: str, n: int, length: int) -> List[str]:
    rng = random.Random(SEEDS[split] * 7_919 + length)
    faces = "URFDLB"
    out = []
    for _ in range(n):
        seq, last = [], None
        while len(seq) < length:
            f = rng.choice(faces)
            if f == last or (last and "URFDLB".index(f) % 3 == "URFDLB".index(last) % 3 and f < last):
                continue
            seq.append(f + rng.choice(["", "2", "'"]))
            last = f
        out.append(" ".join(seq))
    return out
