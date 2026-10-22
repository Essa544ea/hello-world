// Geometric sticker model (mirror of src/cuberesearch/sticker.py) + facelet I/O + validation.
// x = R, y = U, z = F.  A quarter turn rotates the layer clockwise seen from its own side.
"use strict";

const ORDER = "URFDLB";
const FACE_FRAME = {
  U: [[0, 1, 0], [0, 0, -1], [1, 0, 0]],
  R: [[1, 0, 0], [0, 1, 0], [0, 0, -1]],
  F: [[0, 0, 1], [0, 1, 0], [1, 0, 0]],
  D: [[0, -1, 0], [0, 0, 1], [1, 0, 0]],
  L: [[-1, 0, 0], [0, 1, 0], [0, 0, 1]],
  B: [[0, 0, -1], [0, 1, 0], [-1, 0, 0]],
};
const LAYER = {
  R: [0, [1], 1], L: [0, [-1], -1], M: [0, [0], -1],
  U: [1, [1], 1], D: [1, [-1], -1], E: [1, [0], -1],
  F: [2, [1], 1], B: [2, [-1], -1], S: [2, [0], 1],
  r: [0, [1, 0], 1], l: [0, [-1, 0], -1], u: [1, [1, 0], 1], d: [1, [-1, 0], -1],
  f: [2, [1, 0], 1], b: [2, [-1, 0], -1],
  x: [0, [-1, 0, 1], 1], y: [1, [-1, 0, 1], 1], z: [2, [-1, 0, 1], 1],
};
const add = (a, b) => a.map((v, i) => v + b[i]);
const scale = (a, k) => a.map(v => v * k);
function rotCW(v, axis) {
  const [x, y, z] = v;
  if (axis === 0) return [x, z, -y];
  if (axis === 1) return [-z, y, x];
  return [y, -x, z];
}

function parseMoves(str) {
  const re = /([UDRLFB]w|[UDRLFBudrlfbMESxyz])(2'|2|')?/g;
  const clean = str.replace(/[’`]/g, "'");
  const out = [];
  let m, last = 0;
  while ((m = re.exec(clean))) {
    const gap = clean.slice(last, m.index).replace(/[\s()\[\],]/g, "");
    if (gap) throw new Error("رمز غير مفهوم: " + gap);
    last = re.lastIndex;
    let base = m[1];
    if (base.endsWith("w")) base = base[0].toLowerCase();
    const p = { "": 1, "2": 2, "2'": 2, "'": 3 }[m[2] || ""];
    out.push({ base, power: p });
  }
  if (clean.slice(last).replace(/[\s()\[\],]/g, "")) throw new Error("رمز غير مفهوم: " + clean.slice(last));
  return out;
}
const moveStr = m => m.base + ({ 1: "", 2: "2", 3: "'" }[m.power]);
const invMove = m => ({ base: m.base, power: { 1: 3, 2: 2, 3: 1 }[m.power] });

class StickerCube {
  constructor() {
    this.st = [];
    for (const face of ORDER) {
      const [n, up, right] = FACE_FRAME[face];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
        const p = add(add(n, scale(right, j - 1)), scale(up, 1 - i));
        this.st.push({ p, n, c: face, home: p.slice() });   // home = cubie identity
      }
    }
  }
  clone() { const c = new StickerCube(); c.st = this.st.map(s => ({ p: s.p.slice(), n: s.n.slice(), c: s.c, home: s.home })); return c; }
  move(m) {
    const [axis, layers, sign] = LAYER[m.base];
    const q = (m.power * (sign > 0 ? 1 : 3)) % 4;
    for (const s of this.st) if (layers.includes(s.p[axis])) for (let k = 0; k < q; k++) { s.p = rotCW(s.p, axis); s.n = rotCW(s.n, axis); }
    return this;
  }
  apply(moves) { for (const m of moves) this.move(m); return this; }
  at(p, n) { return this.st.find(s => s.p[0] === p[0] && s.p[1] === p[1] && s.p[2] === p[2] && s.n[0] === n[0] && s.n[1] === n[1] && s.n[2] === n[2]); }
  centresHome() { return ORDER.split("").every(f => this.at(FACE_FRAME[f][0], FACE_FRAME[f][0]).c === f); }
  recentred() {
    if (this.centresHome()) return this.clone();
    const rots = [];
    for (const a of "xyz") for (const p of [1, 2, 3]) rots.push({ base: a, power: p });
    for (const r1 of [null, ...rots]) for (const r2 of [null, ...rots]) {
      const c = this.clone();
      if (r1) c.move(r1);
      if (r2) c.move(r2);
      if (c.centresHome()) return c;
    }
    throw new Error("centres");
  }
  facelets(recentre = true) {
    const cube = recentre ? this.recentred() : this;
    let out = "";
    for (const face of ORDER) {
      const [n, up, right] = FACE_FRAME[face];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) out += cube.at(add(add(n, scale(right, j - 1)), scale(up, 1 - i)), n).c;
    }
    return out;
  }
  static fromFacelets(f) {          // geometry from a (centre-home) facelet string
    const c = new StickerCube();
    let k = 0;
    for (const face of ORDER) {
      const [n, up, right] = FACE_FRAME[face];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
        const p = add(add(n, scale(right, j - 1)), scale(up, 1 - i));
        c.at(p, n).c = f[k++];
      }
    }
    // re-derive cubie identities (home) from colours so highlighting works
    const homes = new StickerCube();
    const key = s => s.slice().sort().join("");
    const homeOf = {};
    const groups = g => { const m = {}; for (const s of g.st) { const id = s.p.join(","); (m[id] = m[id] || []).push(s); } return m; };
    for (const ss of Object.values(groups(homes))) homeOf[key(ss.map(s => s.c))] = ss[0].home;
    for (const ss of Object.values(groups(c))) { const h = homeOf[key(ss.map(s => s.c))]; for (const s of ss) s.home = h || s.p.slice(); }
    return c;
  }
  isSolved() {
    const f = this.facelets(false);
    for (let i = 0; i < 6; i++) if (new Set(f.slice(9 * i, 9 * i + 9)).size !== 1) return false;
    return true;
  }
}

// ---- validation (port of CubieCube.from_facelets) ----
const CF = [[8, 9, 20], [6, 18, 38], [0, 36, 47], [2, 45, 11], [29, 26, 15], [27, 44, 24], [33, 53, 42], [35, 17, 51]];
const EF = [[5, 10], [7, 19], [3, 37], [1, 46], [32, 16], [28, 25], [30, 43], [34, 52], [23, 12], [21, 41], [50, 39], [48, 14]];
const CC = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"];
const EC = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"];
function parity(p) { p = p.slice(); let s = 0; for (let i = 0; i < p.length; i++) while (p[i] !== i) { const j = p[i];[p[i], p[j]] = [p[j], p[i]]; s ^= 1; } return s; }
function validateFacelets(f) {
  if (f.length !== 54) return "يجب أن يكون عدد الملصقات 54";
  for (const c of ORDER) { const n = f.split(c).length - 1; if (n !== 9) return `اللون ${c} يظهر ${n} مرات بدل 9`; }
  const cp = [], co = [], ep = [], eo = [];
  for (let pos = 0; pos < 8; pos++) {
    const fl = CF[pos];
    let o = [0, 1, 2].find(k => "UD".includes(f[fl[k]]));
    if (o === undefined) return `الركن في ${CC[pos]} ليس فيه لون علوي/سفلي`;
    const c1 = f[fl[(o + 1) % 3]], c2 = f[fl[(o + 2) % 3]];
    const cub = CC.findIndex(n => n[1] === c1 && n[2] === c2);
    if (cub < 0) return `ألوان ركن مستحيلة في ${CC[pos]}`;
    cp.push(cub); co.push(o);
  }
  for (let pos = 0; pos < 12; pos++) {
    const a = f[EF[pos][0]], b = f[EF[pos][1]];
    let cub = EC.indexOf(a + b), o = 0;
    if (cub < 0) { cub = EC.indexOf(b + a); o = 1; }
    if (cub < 0) return `ألوان حافة مستحيلة في ${EC[pos]}`;
    ep.push(cub); eo.push(o);
  }
  if (new Set(cp).size !== 8) return "ركن مكرر";
  if (new Set(ep).size !== 12) return "حافة مكررة";
  if (co.reduce((a, b) => a + b) % 3) return "ركن ملتوٍ (مجموع اتجاهات الأركان لا يقبل القسمة على 3)";
  if (eo.reduce((a, b) => a + b) % 2) return "حافة مقلوبة منفردة";
  if (parity(cp) !== parity(ep)) return "تبادل قطعتين (تكافؤ غير ممكن)";
  return null;
}

const METRICS = moves => {
  const turns = moves.filter(m => !"xyz".includes(m.base));
  let atm = 0, prev = null;
  const axis = b => ({ U: "y", D: "y", E: "y", u: "y", d: "y", R: "x", L: "x", M: "x", r: "x", l: "x", F: "z", B: "z", S: "z", f: "z", b: "z" }[b]);
  for (const m of turns) { if (axis(m.base) !== prev) atm++; prev = axis(m.base); }
  return {
    HTM: turns.reduce((a, m) => a + ("MES".includes(m.base) ? 2 : 1), 0),
    QTM: turns.reduce((a, m) => a + ("MES".includes(m.base) ? 2 : 1) * (m.power === 2 ? 2 : 1), 0),
    STM: turns.length, ETM: moves.length, ATM: atm,
  };
};

if (typeof module !== "undefined") module.exports = { StickerCube, parseMoves, moveStr, invMove, validateFacelets, METRICS, LAYER, ORDER };
