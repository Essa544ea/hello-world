"""Known last-layer case counts (community facts) reproduced exactly."""
from cuberesearch import ll

S = ll.enumerate_ll()
EO = [k for k in S if not any(k[3])]


def test_ll_group_size():
    assert len(S) == 62208


def test_known_case_counts():
    assert len(ll.cases(S, ll.orientation_only)) == 57 + 1          # OLL
    pll = [k for k in S if not any(k[1]) and not any(k[3])]
    assert len(ll.cases(pll)) == 21 + 1                             # PLL
    assert len(ll.cases(EO, lambda k: k[1])) == 7 + 1               # OCLL
    assert len(ll.cases(EO, lambda k: (k[0], k[1]))) == 42 + 1      # COLL
    assert len(ll.cases(EO)) == 493 + 1                             # ZBLL incl. PLL


def test_macro_distance_sune_only_corners():
    # with only Sune + U turns, every pure corner-orientation case is solvable
    eo_perm_solved = [k for k in S if k[0] == (0, 1, 2, 3) and k[2] == (0, 1, 2, 3) and not any(k[3])]
    d = ll.macro_distances(S, {"sune": "R U R' U R U2 R'"},
                           goal=lambda k: not any(k[1]))
    assert all(k in d for k in eo_perm_solved)
