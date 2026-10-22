"""E12: generate the learning guide for the 7-algorithm last layer from the
verified model: every situation of every stage, a top-view diagram, and the
optimal sequence.  Every sequence is re-checked by applying it."""
from collections import OrderedDict
from common import ROOT
from e10_beginner_ll import VARIANTS
from e03_ll_library import STAGES, stage_weights, u_moves
from e11_worked_example import diagram, solve_stage
from cuberesearch import ll
from cuberesearch.notation import count, state_of

ALG = VARIANTS["proposal-7(+Ub)"]
NAMES = {n: a for st in ALG.values() for n, a in st.items()}
TITLE = OrderedDict([("EO", "1) توجيه حواف الطبقة العليا (EO)"), ("CO|EO", "2) توجيه الأركان (CO)"),
                     ("CP|ori", "3) ترتيب الأركان (CP)"), ("EP|ori,CP", "4) ترتيب الحواف وإنهاء الحل (EP)")])
lines = ["# دليل الطبقة الأخيرة بسبع خوارزميات (مولَّد آلياً ومتحقَّق منه)", "",
         "امسك المكعب واللون العلوي (لون مركز U) فوق. الرسم منظر من الأعلى والوجه الأمامي في الأسفل:",
         "المربع 3×3 في الوسط هو الوجه العلوي؛ الصف الأعلى = الحافة العليا للوجه الخلفي، العمود الأيسر = الوجه الأيسر، الأيمن = الأيمن، الصف الأسفل = الوجه الأمامي.",
         "في المرحلتين 1–2: `X` = ملصق بلون الوجه العلوي، `.` = غير ذلك. في 3–4: الحرف = لون الملصق باسم وجهه الأصلي (R,F,L,B).", "",
         "## الخوارزميات السبع", ""]
for st, named in ALG.items():
    for n, a in named.items():
        lines.append(f"- **{n}**: `{a}` ({count(a, 'STM')} STM) — {TITLE[st]}")
lines.append("")
for st in TITLE:
    dom, proj, goal = STAGES[st]
    weights, reps = stage_weights(st)
    sits = {}
    for p, k in reps.items():
        if goal(p):
            continue
        c0 = ll.from_key(k)
        canon = min(proj(ll.key(c0 * u)) for u in u_moves())
        sits.setdefault(canon, [0, k])
        sits[canon][0] += weights[p]
    tot = sum(weights.values())
    lines += [f"## {TITLE[st]}", ""]
    mode = "ori" if st in ("EO", "CO|EO") else "perm"
    rows = []
    for canon, (w, k) in sits.items():
        # show the situation in the orientation where the sequence needs no initial AUF if possible
        best = None
        for u in u_moves():
            kk = ll.key(ll.from_key(k) * u)
            d, path = solve_stage(kk, st, ALG[st])
            if best is None or (path[:1] not in (["U"], ["U2"], ["U'"]), -d) > (best[2][:1] not in (["U"], ["U2"], ["U'"]), -best[1]):
                best = (kk, d, path)
        kk, d, path = best
        moves = " ".join(NAMES.get(x, x) for x in path)
        after = ll.key(ll.from_key(kk) * state_of(moves))
        assert goal(proj(after)), (st, path)
        rows.append((-w, d, kk, path, moves))
    for negw, d, kk, path, moves in sorted(rows):
        lines += [f"### احتمال {-negw / tot:.1%} — {d} STM — `{' '.join(path)}`", "", "```", diagram(ll.from_key(kk), mode), "```",
                  f"الحركات: `{moves}`", ""]
out = ROOT / "LL7_GUIDE.md"
out.write_text("\n".join(lines))
print("wrote", out, len(lines), "lines")
