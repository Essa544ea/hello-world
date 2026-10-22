"use strict";
// UI for the local lab.  Engine: cube.js (verified against the Python model by tests/test_web_engine.py).

const $ = s => document.querySelector(s);
const COLORS = { U: "var(--cU)", D: "var(--cD)", F: "var(--cF)", B: "var(--cB)", R: "var(--cR)", L: "var(--cL)" };
let API = false;
const api = async (path, body) => {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const j = await r.json();
  if (!r.ok || j.error) throw new Error(j.error || r.statusText);
  return j;
};

// ------------------------------------------------------------------ renderer
const FACE_DIRS = [
  { n: [0, 0, 1], t: "" }, { n: [0, 0, -1], t: "rotateY(180deg)" },
  { n: [1, 0, 0], t: "rotateY(90deg)" }, { n: [-1, 0, 0], t: "rotateY(-90deg)" },
  { n: [0, 1, 0], t: "rotateX(90deg)" }, { n: [0, -1, 0], t: "rotateX(-90deg)" },
];
class View {
  constructor(sceneEl, cubeEl) {
    this.scene = sceneEl; this.el = cubeEl; this.vx = -28; this.vy = -38;
    this.focus = null; this.busy = false;
    let drag = null;
    sceneEl.addEventListener("pointerdown", e => { drag = [e.clientX, e.clientY, this.vx, this.vy]; sceneEl.setPointerCapture(e.pointerId); });
    sceneEl.addEventListener("pointermove", e => {
      if (!drag) return;
      this.vy = drag[3] + (e.clientX - drag[0]) * 0.5;
      this.vx = Math.max(-89, Math.min(89, drag[2] - (e.clientY - drag[1]) * 0.5));
      this.orient();
    });
    sceneEl.addEventListener("pointerup", () => drag = null);
  }
  size() { return this.scene.clientWidth / 5; }
  orient() { this.el.style.transform = `rotateX(${this.vx}deg) rotateY(${this.vy}deg)`; }
  pos(p) { const s = this.size(); return `translate3d(${p[0] * s}px, ${-p[1] * s}px, ${p[2] * s}px)`; }
  render(cube) {
    const s = this.size();
    this.el.style.setProperty("--s", s + "px");
    const map = new Map(cube.st.map(st => [st.p.join() + "|" + st.n.join(), st]));
    const focusKeys = this.focus ? new Set(this.focus) : null;
    let html = "";
    for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
      if (!x && !y && !z) continue;
      const p = [x, y, z];
      let faces = "";
      for (const f of FACE_DIRS) {
        const st = map.get(p.join() + "|" + f.n.join());
        const col = st ? COLORS[st.c] : "transparent";
        const dim = st && focusKeys && !focusKeys.has(st.home.join()) && !isCentre(st.home) ? " class=dim" : "";
        faces += `<div class="face" style="transform:${f.t} translateZ(${s / 2}px)"><i${dim} style="background:${col}"></i></div>`;
      }
      html += `<div class="cubie" data-p="${p.join()}" style="transform:rotate3d(1,0,0,0deg) ${this.pos(p)}">${faces}</div>`;
    }
    this.el.innerHTML = html;
    this.orient();
  }
  animate(cube, m, ms) {
    return new Promise(res => {
      const [axis, layers, sign] = LAYER[m.base];
      let q = (m.power * (sign > 0 ? 1 : 3)) % 4;
      if (q === 3) q = -1;
      const th = -90 * q;
      const css = axis === 0 ? [1, 0, 0, -th] : axis === 1 ? [0, 1, 0, th] : [0, 0, 1, -th];
      const els = [...this.el.querySelectorAll(".cubie")].filter(e => layers.includes(+e.dataset.p.split(",")[axis]));
      const ax = css.slice(0, 3).join(",");
      els.forEach(e => { e.style.transition = "none"; e.style.transform = `rotate3d(${ax},0deg) ${this.pos(e.dataset.p.split(",").map(Number))}`; });
      void this.el.offsetWidth;
      els.forEach(e => { e.style.transition = `transform ${ms}ms ease-in-out`; e.style.transform = `rotate3d(${ax},${css[3]}deg) ${this.pos(e.dataset.p.split(",").map(Number))}`; });
      setTimeout(() => { cube.move(m); this.render(cube); res(); }, ms + 20);
    });
  }
}
const isCentre = h => h.filter(v => v !== 0).length === 1;
const PIECE_HOME = (() => {        // piece name -> home position key
  const v = { U: [0, 1, 0], D: [0, -1, 0], R: [1, 0, 0], L: [-1, 0, 0], F: [0, 0, 1], B: [0, 0, -1] };
  return name => name.split("").reduce((a, c) => a.map((x, i) => x + v[c][i]), [0, 0, 0]).join();
})();

// ------------------------------------------------------------------ simulator state
let cube = new StickerCube();
const view = new View($("#scene"), $("#cube"));
let speed = 300;
const queue = [];
async function run(moves) {
  queue.push(...moves);
  if (view.busy) return;
  view.busy = true;
  while (queue.length) await view.animate(cube, queue.shift(), speed);
  view.busy = false;
}

// move buttons
(() => {
  const bases = ["U", "D", "R", "L", "F", "B", "M", "E", "S", "u", "d", "r", "l", "f", "b", "x", "y", "z"];
  let h = "";
  for (const b of bases) for (const s of ["", "'", "2"]) h += `<button data-m="${b}${s}">${b}${s}</button>`;
  $("#movebtns").innerHTML = h;
  $("#movebtns").addEventListener("click", e => { if (e.target.dataset.m) { clearPlayer(); run(parseMoves(e.target.dataset.m)); } });
})();

$("#applyScr").onclick = () => { try { clearPlayer(); run(parseMoves($("#scr").value)); } catch (e) { alert(e.message); } };
$("#reset").onclick = () => { clearPlayer(); cube = new StickerCube(); view.focus = null; view.render(cube); };
$("#speed").oninput = e => speed = 980 - +e.target.value;
$("#rand").onclick = async () => {
  clearPlayer();
  if (API) {
    const r = await api("/api/random");
    cube = StickerCube.fromFacelets(r.facelets);
    $("#scr").value = r.scramble;
    $("#randnote").textContent = r.note;
  } else {
    const s = localScramble(25);
    cube = new StickerCube().apply(parseMoves(s));
    $("#scr").value = s;
    $("#randnote").textContent = "الخادم غير متاح: خلط بسلسلة 25 حركة عشوائية (ليس توزيعاً موحّداً على كل الحالات).";
  }
  view.render(cube);
};
function localScramble(n) {
  const f = "URFDLB", out = []; let last = -1;
  while (out.length < n) { const i = Math.floor(Math.random() * 6); if (i === last || (i % 3 === last % 3 && i < last)) continue; out.push(f[i] + ["", "'", "2"][Math.floor(Math.random() * 3)]); last = i; }
  return out.join(" ");
}

// ------------------------------------------------------------------ colour editor
let paint = "U", editF = null;
$("#editToggle").onclick = () => { const e = $("#editor"); e.hidden = !e.hidden; if (!e.hidden) { editF = cube.facelets().split(""); drawNet(); } };
$("#palette").innerHTML = "URFDLB".split("").map(c => `<b data-c="${c}" style="background:${COLORS[c]}" class="${c === paint ? "on" : ""}"></b>`).join("");
$("#palette").onclick = e => { if (!e.target.dataset.c) return; paint = e.target.dataset.c; document.querySelectorAll("#palette b").forEach(b => b.classList.toggle("on", b.dataset.c === paint)); };
const NET_POS = { U: [0, 3], L: [3, 0], F: [3, 3], R: [3, 6], B: [3, 9], D: [6, 3] };
function drawNet() {
  let h = "";
  "URFDLB".split("").forEach((f, fi) => {
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
      const k = fi * 9 + i * 3 + j, [r0, c0] = NET_POS[f];
      h += `<b data-k="${k}" style="grid-row:${r0 + i + 1};grid-column:${c0 + j + 1};background:${COLORS[editF[k]]}${k % 9 === 4 ? ";cursor:not-allowed" : ""}"></b>`;
    }
  });
  $("#net").innerHTML = h;
}
$("#net").onclick = e => { const k = e.target.dataset.k; if (k === undefined || k % 9 === 4) return; editF[k] = paint; drawNet(); };
$("#editApply").onclick = () => {
  const f = editF.join(""), err = validateFacelets(f);
  $("#editMsg").textContent = err ? "✗ " + err : "✓ حالة ممكنة";
  if (!err) { clearPlayer(); cube = StickerCube.fromFacelets(f); view.render(cube); }
};

// ------------------------------------------------------------------ solution player
let player = null;   // {start: StickerCube, moves:[{m, step}], i, steps}
function clearPlayer() { player = null; $("#steps").innerHTML = ""; view.focus = null; }
$("#solve").onclick = async () => {
  if (!API) return alert("شغّل الخادم المحلي: python3 server.py");
  $("#solveMsg").textContent = "جارٍ الحساب... (أول تشغيل لكل طريقة يبني جداول وقد يستغرق دقائق)";
  try {
    const r = await api("/api/solve", { facelets: cube.facelets(), method: $("#method").value });
    cube = cube.recentred();
    setPlayer(r);
    $("#solveMsg").innerHTML = `${r.method}: STM ${r.metrics.STM} · HTM ${r.metrics.HTM} · ETM ${r.metrics.ETM} — زمن الحساب ${r.compute_seconds.toFixed(1)} ث. <br>${r.note}`;
  } catch (e) { $("#solveMsg").textContent = "خطأ: " + e.message; }
};
function setPlayer(r) {
  const moves = [];
  const rot = r.rotation ? parseMoves(r.rotation) : [];
  rot.forEach(m => moves.push({ m, step: -1 }));
  r.steps.forEach((st, si) => parseMoves(st.moves.join(" ")).forEach(m => moves.push({ m, step: si })));
  player = { start: cube.clone(), moves, i: 0, steps: r.steps, rot: r.rotation };
  drawSteps();
}
function drawSteps() {
  if (!player) return;
  const cur = player.i < player.moves.length ? player.moves[player.i].step : player.steps.length - 1;
  let k = player.moves.filter(x => x.step === -1).length;
  let h = player.rot ? `<div class="small muted">تدوير ابتدائي: <span dir="ltr">${player.rot}</span></div>` : "";
  player.steps.forEach((st, si) => {
    const mv = parseMoves(st.moves.join(" ")).map(m => `<span class="${k++ < player.i ? "done" : ""}">${moveStr(m)}</span>`).join(" ");
    const met = st.metrics && st.metrics.STM !== undefined ? `STM ${st.metrics.STM} · HTM ${st.metrics.HTM}` : "0";
    h += `<div class="step ${si === cur ? "cur" : ""}"><b>${st.name}</b>${st.choice && st.choice !== "-" ? `<span class="badge">${st.choice}</span>` : ""}<span class="badge">${met}</span>
      <div class="mv">${mv || "—"}</div><div class="small muted">${st.explain || ""}</div></div>`;
  });
  $("#steps").innerHTML = h;
  const st = player.steps[cur];
  view.focus = $("#hl").checked && st && st.focus && st.focus.length ? focusFor(cur) : null;
  view.render(cube);
}
function focusFor(cur) {           // pieces solved so far + this step
  const keys = [];
  for (let s = 0; s <= cur; s++) (player.steps[s].focus || []).forEach(p => keys.push(PIECE_HOME(p)));
  return keys;
}
$("#hl").onchange = drawSteps;
async function pStep(dir) {
  if (!player || view.busy) return;
  if (dir > 0 && player.i < player.moves.length) { const m = player.moves[player.i++].m; drawSteps(); await run([m]); }
  else if (dir < 0 && player.i > 0) { const m = player.moves[--player.i].m; drawSteps(); await run([invMove(m)]); }
  drawSteps();
}
let playing = false;
$("#pNext").onclick = () => pStep(1);
$("#pPrev").onclick = () => pStep(-1);
$("#pFirst").onclick = () => { if (!player) return; cube = player.start.clone(); player.i = 0; drawSteps(); };
$("#pLast").onclick = () => { if (!player) return; cube = player.start.clone().apply(player.moves.map(x => x.m)); player.i = player.moves.length; drawSteps(); };
$("#pPlay").onclick = async () => {
  if (!player) return;
  playing = !playing;
  while (playing && player.i < player.moves.length) await pStep(1);
  playing = false;
};

// ------------------------------------------------------------------ compare
$("#runCmp").onclick = async () => {
  if (!API) return alert("شغّل الخادم المحلي");
  const f = cube.facelets();
  $("#cmpOut").innerHTML = "جارٍ الحساب...";
  try {
    const rs = await Promise.all([$("#mA").value, $("#mB").value].map(m => api("/api/solve", { facelets: f, method: m })));
    $("#cmpOut").innerHTML = rs.map(r => `<div class="panel"><h3>${r.method}</h3>
      <table class="tbl"><tr><th>الخطوة</th><th>STM</th><th>HTM</th><th>الحركات</th></tr>
      ${r.steps.map(s => `<tr><td>${s.name}</td><td class="num">${s.metrics.STM ?? 0}</td><td class="num">${s.metrics.HTM ?? 0}</td><td class="num">${s.moves.join(" ")}</td></tr>`).join("")}
      <tr><th>المجموع</th><th class="num">${r.metrics.STM}</th><th class="num">${r.metrics.HTM}</th><th class="num">ETM ${r.metrics.ETM} · QTM ${r.metrics.QTM} · ATM ${r.metrics.ATM}</th></tr></table>
      <div class="small muted">الزمن البشري المقدّر: غير متاح بعد (لا يوجد نموذج مُعايَر). الزمن المقاس: لا يوجد.</div></div>`).join("");
  } catch (e) { $("#cmpOut").textContent = "خطأ: " + e.message; }
};

// ------------------------------------------------------------------ training / timer
const store = { get: () => { try { return JSON.parse(localStorage.getItem("trials") || "[]"); } catch { return []; } },
  set: v => { try { localStorage.setItem("trials", JSON.stringify(v)); } catch { } } };
let tState = "idle", tStart = 0, tInsp = 0, tRaf = 0, tResult = null, tPenalty = 0, tScramble = "", tScrKind = "";
$("#tNew").onclick = async () => {
  if (API) { const r = await api("/api/random"); tScramble = r.scramble; tScrKind = "uniform"; }
  else { tScramble = localScramble(25); tScrKind = "random-moves-25"; }
  $("#tScr").textContent = tScramble;
};
function tick() {
  const now = performance.now();
  if (tState === "insp") {
    const left = 15 - (now - tInsp) / 1000;
    $("#tTimer").textContent = left > 0 ? Math.ceil(left) : (left > -2 ? "+2" : "DNF");
  } else if (tState === "run") $("#tTimer").textContent = ((now - tStart) / 1000).toFixed(2);
  tRaf = requestAnimationFrame(tick);
}
function tPress() {
  const now = performance.now();
  if (tState === "idle" || tState === "done") {
    tResult = null; tPenalty = 0;
    if ($("#pinsp").checked) { tState = "insp"; tInsp = now; $("#tTimer").className = "timer insp"; }
    else { tState = "run"; tStart = now; $("#tTimer").className = "timer run"; }
    cancelAnimationFrame(tRaf); tick();
  } else if (tState === "insp") {
    const used = (now - tInsp) / 1000;
    tPenalty = used > 17 ? "DNF" : used > 15 ? 2 : 0;          // WCA A4d1 / A4d2
    tState = "run"; tStart = now; $("#tTimer").className = "timer run";
  } else if (tState === "run") {
    tResult = (now - tStart) / 1000; tState = "done"; cancelAnimationFrame(tRaf);
    $("#tTimer").className = "timer";
    $("#tTimer").textContent = tResult.toFixed(2) + (tPenalty === 2 ? " (+2)" : tPenalty === "DNF" ? " DNF" : "");
  }
}
$("#tTimer").addEventListener("pointerdown", e => { e.preventDefault(); tPress(); });
document.addEventListener("keydown", e => { if (e.code === "Space" && $("#train").classList.contains("on") && e.target.tagName !== "INPUT") { e.preventDefault(); if (!e.repeat) tPress(); } });
$("#tSave").onclick = async () => {
  if (tResult === null) return ($("#tMsg").textContent = "لا توجد محاولة منتهية.");
  const t = {
    participant: $("#pid").value, level: $("#plevel").value, experience: $("#pexp").value, method: $("#pmethod").value,
    training_minutes: +$("#ptrain").value, kind: $("#pkind").value, protocol: $("#pproto").value,
    inspection_used: $("#pinsp").checked, scramble: tScramble, scramble_kind: tScrKind,
    time_s: tResult, penalty: tPenalty, dnf: $("#tDnf").checked || tPenalty === "DNF", errors: +$("#tErr").value,
    note: $("#tNote").value, client_time: new Date().toISOString(),
    measurement: "press-to-press browser timer (performance.now); not a finger-movement measurement",
  };
  const all = store.get(); all.push(t); store.set(all);
  let msg = "حُفظت محلياً في المتصفح.";
  if (API) { try { await api("/api/trial", t); msg += " وحُفظت في data/human_trials.jsonl على جهازك."; } catch (e) { msg += " (تعذّر الحفظ في الخادم: " + e.message + ")"; } }
  $("#tMsg").textContent = msg; $("#tErr").value = 0; $("#tDnf").checked = false; $("#tNote").value = "";
  drawCurve();
};
function drawCurve() {
  const all = store.get(), svg = $("#curve");
  const ok = all.filter(t => !t.dnf);
  if (!ok.length) { svg.innerHTML = `<text x="200" y="110" text-anchor="middle" fill="currentColor" font-size="12">لا محاولات بعد</text>`; $("#tList").textContent = ""; return; }
  const methods = [...new Set(ok.map(t => t.method || "?"))];
  const maxT = Math.max(...ok.map(t => t.time_s)) * 1.1, n = Math.max(...methods.map(m => ok.filter(t => (t.method || "?") === m).length));
  const pal = ["#2a6fdb", "#d1495b", "#2e933c", "#a05195", "#e28c05"];
  let h = `<line x1="30" y1="200" x2="395" y2="200" stroke="currentColor" stroke-width=".5"/><line x1="30" y1="10" x2="30" y2="200" stroke="currentColor" stroke-width=".5"/>
    <text x="4" y="14" font-size="9" fill="currentColor">${maxT.toFixed(0)}ث</text><text x="380" y="214" font-size="9" fill="currentColor">#${n}</text>`;
  methods.forEach((m, mi) => {
    const pts = ok.filter(t => (t.method || "?") === m).map((t, i) => [30 + 360 * (n > 1 ? i / (n - 1) : 0.5), 200 - 190 * t.time_s / maxT, t.kind]);
    h += `<polyline fill="none" stroke="${pal[mi % 5]}" stroke-width="1.5" points="${pts.map(p => p.slice(0, 2).join(",")).join(" ")}"/>`;
    h += pts.map(p => `<circle cx="${p[0]}" cy="${p[1]}" r="${p[2] === "test" ? 3.5 : 2}" fill="${pal[mi % 5]}"/>`).join("");
    h += `<text x="${40 + mi * 90}" y="24" font-size="10" fill="${pal[mi % 5]}">${m}</text>`;
  });
  svg.innerHTML = h;
  $("#tList").textContent = `${all.length} محاولة محفوظة (${all.filter(t => t.kind === "test").length} اختبار). الدوائر الكبيرة = اختبار.`;
}
$("#tExport").onclick = () => {
  const all = store.get(); if (!all.length) return;
  const keys = Object.keys(all[0]);
  const csv = [keys.join(",")].concat(all.map(t => keys.map(k => JSON.stringify(t[k] ?? "")).join(","))).join("\n");
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = "trials.csv"; a.click();
};
$("#tClear").onclick = () => { if (confirm("مسح كل المحاولات المحفوظة في هذا المتصفح؟ (لا يمسح ملف الخادم)")) { store.set([]); drawCurve(); } };

// ABBA schedule with disguised (rotated) copies of the same scramble
const ROTS = ["", "y", "y2", "y'", "x", "x'", "x2", "z", "z'", "x y", "x y'", "x' y", "x' y'", "z y", "z' y", "x2 y", "z y2", "z' y2", "x y2", "x' y2", "z y'", "z' y'", "x2 y'", "x2 y2"];
function relabel(scr, rot) {        // same state, seen after a whole-cube rotation
  if (!rot) return scr;
  const c = new StickerCube().apply(parseMoves(rot));
  const map = {};
  for (const f of "URFDLB") { const n = { U: [0, 1, 0], D: [0, -1, 0], R: [1, 0, 0], L: [-1, 0, 0], F: [0, 0, 1], B: [0, 0, -1] }[f];
    const st = c.st.find(s => s.home.join() === n.join() && isCentre(s.home)); const g = "URFDLB".split("").find(F => ({ U: [0, 1, 0], D: [0, -1, 0], R: [1, 0, 0], L: [-1, 0, 0], F: [0, 0, 1], B: [0, 0, -1] })[F].join() === st.p.join()); map[f] = g; }
  return parseMoves(scr).map(m => moveStr({ base: map[m.base] || m.base, power: m.power })).join(" ");
}
$("#abGen").onclick = async () => {
  const A = $("#abA").value || "A", B = $("#abB").value || "B", n = Math.max(2, +$("#abN").value);
  const rows = [];
  for (let i = 0; i < n; i += 2) {
    const s = API ? (await api("/api/random")).scramble : localScramble(25);
    const order = (i / 2) % 2 === 0 ? [A, B] : [B, A];
    const r1 = ROTS[Math.floor(Math.random() * 24)], r2 = ROTS[Math.floor(Math.random() * 24)];
    rows.push([i + 1, order[0], relabel(s, r1)], [i + 2, order[1], relabel(s, r2)]);
  }
  $("#abOut").innerHTML = `<p class="muted">كل محاولتين متتاليتين لهما الحالة نفسها لكن بتدوير مختلف للمكعب (لتقليل ميزة التذكر)، وترتيب الطريقتين يتبادل (ABBA).</p>
    <table class="tbl"><tr><th>#</th><th>الطريقة</th><th>الخلط</th></tr>${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="num">${r[2]}</td></tr>`).join("")}</table>`;
};

// ------------------------------------------------------------------ recognition drill
const dview = new View($("#dscene"), $("#dcube"));
let drill = null;
const dscore = () => { try { return JSON.parse(localStorage.getItem("drill") || '{"n":0,"ok":0}'); } catch { return { n: 0, ok: 0 }; } };
$("#dNew").onclick = async () => {
  if (!API) return alert("شغّل الخادم المحلي");
  $("#dOut").textContent = "جارٍ التحضير...";
  const r = await api("/api/random");
  const sol = await api("/api/solve", { facelets: r.facelets, method: "CFOP/fixed" });
  const c = StickerCube.fromFacelets(r.facelets).apply(parseMoves(sol.steps[0].moves.join(" ")));
  drill = { alts: sol.steps[1].alternatives, sol: sol.steps[1] };
  dview.render(c);
  $("#dChoices").innerHTML = Object.keys(drill.alts).map(k => `<button data-k="${k}">${k}</button>`).join("");
  $("#dOut").textContent = "أي زوج تبدأ به؟ (FR = الأمامي الأيمن، FL = الأمامي الأيسر، BL = الخلفي الأيسر، BR = الخلفي الأيمن)";
};
$("#dChoices").onclick = e => {
  const k = e.target.dataset.k; if (!k || !drill) return;
  const best = Math.min(...Object.values(drill.alts)), ok = drill.alts[k] === best;
  const s = dscore(); s.n++; if (ok) s.ok++; try { localStorage.setItem("drill", JSON.stringify(s)); } catch { }
  $("#dOut").innerHTML = `${ok ? "✓ من الأقصر" : "✗ ليس الأقصر"} — الأطوال المثلى: ${Object.entries(drill.alts).map(([a, b]) => `${a}=${b}`).join("، ")}<br>
    حل مثالي للزوج ${drill.sol.choice}: <span dir="ltr">${drill.sol.moves.join(" ")}</span>`;
  $("#dScore").textContent = `الدقة: ${s.ok}/${s.n}`;
  drill = null;
};

// ------------------------------------------------------------------ results
async function loadResults() {
  if (!API) { $("#resOut").textContent = "شغّل الخادم المحلي لعرض النتائج."; return; }
  const r = await api("/api/results");
  let h = "";
  for (const [k, v] of Object.entries(r.results)) {
    if (v.summary) {
      h += `<h3>${k}</h3><p class="small muted">${JSON.stringify(v.provenance || {})}</p><table class="tbl"><tr><th>الطريقة</th><th>STM متوسط ± خطأ معياري</th><th>HTM</th><th>متوسط الخطوات</th></tr>`;
      for (const [m, s] of Object.entries(v.summary))
        h += `<tr><td>${m}</td><td class="num">${s.STM.mean.toFixed(2)} ± ${s.STM.sem.toFixed(2)}</td><td class="num">${s.HTM.mean.toFixed(2)}</td><td class="num">${Object.entries(s.steps_mean).map(([a, b]) => `${a} ${b.toFixed(2)}`).join(" · ")}</td></tr>`;
      h += "</table>";
    } else h += `<h3>${k}</h3><pre dir="ltr">${JSON.stringify(v, null, 1)}</pre>`;
  }
  for (const [k, v] of Object.entries(r.docs)) h += `<h3>${k}</h3><pre>${v.replace(/</g, "&lt;")}</pre>`;
  $("#resOut").innerHTML = h;
}

// ------------------------------------------------------------------ tabs, help, boot
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("on", x === b));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.id === b.dataset.tab));
  if (b.dataset.tab === "res") loadResults();
  if (b.dataset.tab === "sim") view.render(cube);
});
document.querySelectorAll(".try").forEach(td => td.onclick = () => {
  document.querySelector('#tabs button[data-tab="sim"]').click();
  clearPlayer(); run(parseMoves(td.textContent));
});
(async () => {
  view.render(cube);
  drawCurve();
  try {
    const ms = await api("/api/methods");
    API = true;
    const opts = Object.entries(ms).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
    $("#method").innerHTML = opts; $("#mA").innerHTML = opts; $("#mB").innerHTML = opts;
    $("#mB").selectedIndex = Math.min(5, $("#mB").options.length - 1);
    $("#apistatus").textContent = "الخادم المحلي متصل.";
  } catch {
    $("#apistatus").textContent = "وضع بلا خادم: المحاكاة اليدوية تعمل؛ الحل والمقارنة يحتاجان python3 server.py";
  }
})();
window.addEventListener("resize", () => view.render(cube));
