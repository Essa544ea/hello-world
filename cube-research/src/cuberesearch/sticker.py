"""Independent geometric sticker model used to cross-check `cubie.py`.

Every one of the 54 stickers is a (position, normal, colour) triple in integer
3-D coordinates (x = R, y = U, z = F).  A move rotates all stickers in the
affected layer(s) by 90 degrees with an integer rotation matrix.  Nothing here
is derived from the cubie tables: slices, wide moves and rotations are just
different layer selections, so agreement between the two models is real
evidence that both are right.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Vec = Tuple[int, int, int]

FACE_NORMAL: Dict[str, Vec] = {"U": (0, 1, 0), "D": (0, -1, 0), "R": (1, 0, 0),
                               "L": (-1, 0, 0), "F": (0, 0, 1), "B": (0, 0, -1)}
# reading frame for each face in the Kociemba facelet string: (normal, up, right)
FACE_FRAME = {
    "U": ((0, 1, 0), (0, 0, -1), (1, 0, 0)),
    "R": ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
    "F": ((0, 0, 1), (0, 1, 0), (1, 0, 0)),
    "D": ((0, -1, 0), (0, 0, 1), (1, 0, 0)),
    "L": ((-1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "B": ((0, 0, -1), (0, 1, 0), (-1, 0, 0)),
}
ORDER = "URFDLB"

# (axis index, layers selected, sign): a quarter turn rotates by -90deg about
# +axis when sign=+1 (clockwise seen from the + side).
LAYER_SPEC = {
    "R": (0, {1}, 1), "L": (0, {-1}, -1), "M": (0, {0}, -1),
    "U": (1, {1}, 1), "D": (1, {-1}, -1), "E": (1, {0}, -1),
    "F": (2, {1}, 1), "B": (2, {-1}, -1), "S": (2, {0}, 1),
    "r": (0, {1, 0}, 1), "l": (0, {-1, 0}, -1),
    "u": (1, {1, 0}, 1), "d": (1, {-1, 0}, -1),
    "f": (2, {1, 0}, 1), "b": (2, {-1, 0}, -1),
    "x": (0, {-1, 0, 1}, 1), "y": (1, {-1, 0, 1}, 1), "z": (2, {-1, 0, 1}, 1),
}


def _add(a, b):
    return tuple(i + j for i, j in zip(a, b))


def _scale(a, k):
    return tuple(i * k for i in a)


def _rot_cw(v: Vec, axis: int) -> Vec:
    """Rotate v by -90 degrees around the +axis (clockwise viewed from +axis)."""
    x, y, z = v
    if axis == 0:   # y' = z, z' = -y
        return (x, z, -y)
    if axis == 1:   # z' = x, x' = -z   (U: F -> L)
        return (-z, y, x)
    return (y, -x, z)  # axis 2: x' = y, y' = -x  (F: U -> R)


class StickerCube:
    def __init__(self):
        self.st: List[Tuple[Vec, Vec, str]] = []
        for face in ORDER:
            n, up, right = FACE_FRAME[face]
            for i in range(3):
                for j in range(3):
                    p = _add(_add(n, _scale(right, j - 1)), _scale(up, 1 - i))
                    self.st.append((p, n, face))

    def move(self, base: str, power: int):
        axis, layers, sign = LAYER_SPEC[base]
        q = (power * (1 if sign > 0 else 3)) % 4
        new = []
        for p, n, c in self.st:
            if p[axis] in layers:
                for _ in range(q):
                    p, n = _rot_cw(p, axis), _rot_cw(n, axis)
            new.append((p, n, c))
        self.st = new

    def apply(self, moves):
        for m in moves:
            self.move(m.base, m.power)
        return self

    def colour_at(self, p: Vec, n: Vec) -> str:
        for q, m, c in self.st:
            if q == p and m == n:
                return c
        raise KeyError((p, n))

    def centre_facing(self, n: Vec) -> str:
        return self.colour_at(n, n)

    def _centres_home(self) -> bool:
        return all(self.centre_facing(FACE_NORMAL[f]) == f for f in ORDER)

    def recentred(self) -> "StickerCube":
        """Copy rotated as a whole so every centre is back at its home face
        (the centre-fixed frame used by the cubie model)."""
        rots = [(a, p) for a in "xyz" for p in (1, 2, 3)]
        for first in [None] + rots:
            for second in [None] + rots:
                c = StickerCube()
                c.st = list(self.st)
                for r in (first, second):
                    if r:
                        c.move(*r)
                if c._centres_home():
                    return c
        raise AssertionError("no rotation restores the centres")

    def facelets(self, recentre: bool = True) -> str:
        """Kociemba-format facelet string, read in the centre-fixed frame by default."""
        cube = self.recentred() if recentre else self
        out = []
        for face in ORDER:
            n, up, right = FACE_FRAME[face]
            for i in range(3):
                for j in range(3):
                    p = _add(_add(n, _scale(right, j - 1)), _scale(up, 1 - i))
                    out.append(cube.colour_at(p, n))
        return "".join(out)

    def is_solved(self) -> bool:
        f = self.facelets(recentre=False)
        return all(len(set(f[9 * i:9 * i + 9])) == 1 for i in range(6))
