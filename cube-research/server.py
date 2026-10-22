"""Local-only lab server: serves web/ and a small JSON API backed by the
verified engine.  Binds to 127.0.0.1 by default; nothing is sent anywhere.

  python3 server.py [--port 8765]
"""
import argparse
import json
import random
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from cuberesearch.cubie import CubieCube, random_state, SOLVED  # noqa: E402
from cuberesearch.notation import parse, apply as py_apply, all_metrics, invert, fmt  # noqa: E402

LOCK = threading.Lock()
TRIALS = ROOT / "data" / "human_trials.jsonl"

PIECES = {
    "cross": ["DR", "DF", "DL", "DB"],
    "FR": ["DFR", "FR"], "FL": ["DLF", "FL"], "BL": ["DBL", "BL"], "BR": ["DRB", "BR"],
    "LL": ["URF", "UFL", "ULB", "UBR", "UR", "UF", "UL", "UB"],
    "FB": ["DLF", "DBL", "DL", "FL", "BL"], "SB": ["DFR", "DRB", "DR", "FR", "BR"],
    "CMLL": ["URF", "UFL", "ULB", "UBR"], "LSE": ["UR", "UF", "UL", "UB", "DF", "DB"],
    "EOLine": ["DF", "DB"], "2x2x2": ["DBL", "DL", "DB", "BL"], "2x2x3": ["DLF", "DF", "FL"],
    "LB": ["DLF", "DBL", "DL", "FL", "BL"], "RB": ["DFR", "DRB", "DR", "FR", "BR"],
}

EXPLAIN = {
    "cross": "صليب الوجه السفلي: أربع حواف D في أماكنها واتجاهها. اختير الوجه/الاتجاه الأقصر من بين البدائل المعروضة.",
    "pair": "زوج F2L: ركن + حافة طبقة وسطى. اختير الزوج الأقصر حلاً من بين الأزواج المتبقية (مثل قاعدة «ابدأ بالزوج الأسهل»).",
    "OLL": "توجيه كل قطع الطبقة العليا (اللون العلوي فوق). الطول هنا أمثل حاسوبياً؛ الخوارزمية البشرية غالباً أطول قليلاً.",
    "OCLL": "توجيه أركان الطبقة العليا (الحواف موجّهة مسبقاً).",
    "COLL": "حل أركان الطبقة العليا بالكامل مع إبقاء الحواف موجّهة.",
    "PLL": "ترتيب قطع الطبقة العليا (يشمل لفّ U الأخير AUF).",
    "EPLL": "ترتيب حواف الطبقة العليا فقط.",
    "ZBLL": "حل الطبقة العليا كلها دفعة واحدة (الحواف موجّهة).",
    "EOLine": "توجيه كل الحواف (لا تحتاج F/B لاحقاً) مع وضع حافتي DF وDB.",
    "block1": "كتلة 1×2×3 على أحد الجانبين بحركات R,U,L فقط.",
    "block2": "الكتلة الثانية بحركات R,U,L.",
    "2x2x2": "كتلة 2×2×2 حول ركن واحد.",
    "2x2x3": "توسيع الكتلة إلى 2×2×3.",
    "EO": "توجيه كل الحواف المتبقية.",
    "F2L-RU": "إكمال أول طبقتين بحركات R وU فقط.",
    "FB": "الكتلة الأولى في Roux: 1×2×3 على اليسار.",
    "SB": "الكتلة الثانية في Roux: 1×2×3 على اليمين دون كسر الأولى.",
    "CMLL": "حل أركان الطبقة العليا دون الاهتمام بالحواف والشريحة الوسطى.",
    "LSE": "آخر ست حواف بحركات M وU فقط.",
}


def methods_registry():
    from cuberesearch import methods as M
    return {
        "CFOP/fixed": ("CFOP (صليب أسفل ثابت)", lambda c: M.run_cfop(c, "fixed")),
        "CFOP/fullCN": ("CFOP (حياد ألوان كامل)", lambda c: M.run_cfop(c, "full")),
        "ZZ/OCLL+PLL": ("ZZ + OCLL/PLL", lambda c: M.run_zz(c, "ocll_pll")),
        "ZZ/ZBLL": ("ZZ + ZBLL", lambda c: M.run_zz(c, "zbll")),
        "Petrus/OCLL+PLL": ("Petrus + OCLL/PLL", lambda c: M.run_petrus(c, "ocll_pll")),
        "Roux/x-neutral": ("Roux", lambda c: M.run_roux(c, "x")),
    }


def step_focus(step):
    n = step["name"]
    if n.startswith("pair"):
        return PIECES.get(step.get("choice") or "", [])
    if n == "block1":
        return PIECES.get(step.get("choice") or "", [])
    return PIECES.get(n, PIECES["LL"] if n in ("OLL", "PLL", "OCLL", "COLL", "EPLL", "ZBLL") else [])


def explain(step):
    n = step["name"]
    key = "pair" if n.startswith("pair") else n
    txt = EXPLAIN.get(key, "")
    if step.get("alternatives"):
        alts = "، ".join(f"{k}: {v}" for k, v in sorted(step["alternatives"].items(), key=lambda kv: kv[1]))
        txt += f" (البدائل وأطوالها المثلى: {alts})"
    return txt


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "web"), **kw)

    def log_message(self, fmt_, *args):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path.startswith("/api/methods"):
            return self._json({k: v[0] for k, v in methods_registry().items()})
        if self.path.startswith("/api/random"):
            c = random_state(random.Random())
            import kociemba
            sol = kociemba.solve(c.to_facelets())
            scr = fmt(invert(parse(sol)))
            assert py_apply(SOLVED, parse(scr)) == c
            return self._json({"facelets": c.to_facelets(), "scramble": scr,
                               "note": "حالة عشوائية موحّدة التوزيع؛ الخلط المعروض هو معكوس حل Kociemba (لتطبيقه على مكعب حقيقي)."})
        if self.path.startswith("/api/results"):
            out = {}
            for p in sorted((ROOT / "results").glob("*.json")):
                try:
                    d = json.loads(p.read_text())
                    d.pop("runs", None)
                    out[p.stem] = d
                except Exception as e:  # noqa: BLE001
                    out[p.stem] = {"error": str(e)}
            docs = {n: (ROOT / n).read_text() for n in ("CLAIMS.md", "EXPERIMENT_LOG.md") if (ROOT / n).exists()}
            return self._json({"results": out, "docs": docs})
        return super().do_GET()

    def do_POST(self):
        try:
            body = self._body()
        except Exception:
            return self._json({"error": "bad json"}, 400)
        if self.path.startswith("/api/solve"):
            try:
                c = CubieCube.from_facelets(body["facelets"])
            except ValueError as e:
                return self._json({"error": f"حالة غير ممكنة: {e}"}, 400)
            reg = methods_registry()
            m = body.get("method", "CFOP/fixed")
            if m not in reg:
                return self._json({"error": "unknown method"}, 400)
            t = time.time()
            with LOCK:
                r = reg[m][1](c)
            for st in r["steps"]:
                st["focus"] = step_focus(st)
                st["explain"] = explain(st)
                st["metrics"] = all_metrics(" ".join(st["moves"])) if st["moves"] else {}
            r["metrics"] = all_metrics(r["solution"])
            r["compute_seconds"] = time.time() - t
            r["note"] = ("كل خطوة محلولة بأقل عدد حركات حاسوبياً (حد أدنى هيكلي)؛ "
                         "ليست حلاً بشرياً نموذجياً ولا زمناً مقاساً.")
            return self._json(r)
        if self.path.startswith("/api/trial"):
            body["server_received"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            TRIALS.parent.mkdir(exist_ok=True)
            with LOCK, open(TRIALS, "a") as f:
                f.write(json.dumps(body, ensure_ascii=False) + "\n")
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    print(f"open http://{a.host}:{a.port}/  (first solve per method builds tables; may take minutes)")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
