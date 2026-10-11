const $ = (id) => document.getElementById(id);
const intFmt = new Intl.NumberFormat("en-US");
let api = null;
let lastPhase = null;
let gameFound = false;

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
};

// ---------- formatting ----------
function num(n) {
  if (n == null || !isFinite(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e7) return (n / 1e6).toFixed(1) + "M";
  return intFmt.format(Math.round(n));
}
function signed(n) { return (n > 0 ? "+" : "") + num(n); }

function hoursHe(h) { return h === 1 ? "שעה" : h === 2 ? "שעתיים" : `${h} שעות`; }
function minutesHe(m) { return m === 1 ? "דקה" : `${m} דקות`; }
function etaLong(min) {
  if (min == null || !isFinite(min)) return "—";
  if (min < 1) return "פחות מדקה";
  const m = Math.round(min);
  if (m >= 48 * 60) return `${(m / 1440).toFixed(1)} ימים`;
  if (m < 60) return minutesHe(m);
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${hoursHe(h)} ו-${minutesHe(r)}` : hoursHe(h);
}
function etaShort(min) {
  if (min == null || !isFinite(min)) return "—";
  if (min < 1) return "<1 דק'";
  const m = Math.round(min);
  if (m < 60) return `${m} דק'`;
  if (m >= 48 * 60) return `${(m / 1440).toFixed(1)} ימים`;
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")} ש'`;
}
function clock(sec) {
  sec = Math.max(0, Math.ceil(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const mm = String(m).padStart(h ? 2 : 1, "0"), ss = String(s).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
function duration(min) {
  if (min < 1) return `${Math.round(min * 60)} שנ'`;
  return `${Math.round(min)} דק'`;
}
function readingText(r) {
  return `${intFmt.format(r.exp)} [${r.pct.toFixed(2)}%]` + (r.level ? `  Lv.${r.level}` : "");
}

// ---------- views ----------
const VIEWS = { idle: "idle", cancelled: "idle", countdown: "countdown", running: "running",
                finalizing: "finalizing", done: "done", error: "error" };
const BADGES = {
  idle: ["מוכן", ""], cancelled: ["מוכן", ""], countdown: ["מתחיל", "live"], running: ["מקליט", "live"],
  finalizing: ["מסכם", "live"], done: ["הושלם", "done"], error: ["שגיאה", "err"],
};

function showView(phase) {
  const name = VIEWS[phase] || "idle";
  document.querySelectorAll(".view").forEach((v) => { v.hidden = v.id !== `view-${name}`; });
  const [text, cls] = BADGES[phase] || BADGES.idle;
  const b = $("phaseBadge");
  b.textContent = text;
  b.className = "badge " + cls;
}

function renderGame(g) {
  const chip = $("gameChip");
  gameFound = g.found && !g.minimized;
  // \u2066…\u2069 isolates the LTR size so RTL layout doesn't flip "1920×1200"
  if (g.found && !g.minimized) { chip.className = "chip ok"; $("gameText").textContent = `המשחק מחובר · \u2066${g.size}\u2069`; }
  else if (g.minimized) { chip.className = "chip warn"; $("gameText").textContent = "המשחק ממוזער"; }
  else { chip.className = "chip bad"; $("gameText").textContent = "MapleStory לא פתוח"; }
  $("startBtn").disabled = !gameFound;
  $("testBtn").disabled = !gameFound;
}

function renderRunning(s) {
  $("clock").textContent = clock(s.remaining);
  const done = s.total ? 1 - s.remaining / s.total : 0;
  $("progress").style.width = `${(done * 100).toFixed(2)}%`;
  $("progressText").textContent = `${Math.floor(done * 100)}%`;
  const live = s.live;
  if (live && live.minutes > 0) {
    $("liveRate").textContent = num(live.exp_per_min);
    $("liveGained").textContent = signed(live.exp_gained);
    $("liveEta").textContent = etaShort(live.eta_minutes);
    const n = live.levels_gained;
    const lv = n === 1 ? " · עלית רמה!" : n > 1 ? ` · עלית ${n} רמות!` : "";
    $("liveStatus").textContent = `קריאה אחרונה לפני ${Math.round(live.last_ago)} שנ' · ${live.pct.toFixed(2)}%${lv}`;
  } else {
    $("liveRate").textContent = "—"; $("liveGained").textContent = "—"; $("liveEta").textContent = "—";
    $("liveStatus").textContent = "מחכה לקריאה הבאה (כל 10 שניות)…";
  }
  if (s.failed_reads) $("liveStatus").textContent += ` · ${s.failed_reads} קריאות דולגו`;
}

function renderDone(s) {
  const r = s.result;
  $("timerTitle").textContent = "סיכום סשן" + (s.map ? ` · \u2066${s.map}\u2069` : "");
  $("doneWarn").hidden = !s.warning;
  $("doneWarn").textContent = s.warning || "";
  $("resRate").textContent = num(r.exp_per_min);
  $("resHour").textContent = num(r.exp_per_hour);
  $("resEta").textContent = r.eta_minutes == null ? "—" : etaLong(r.eta_minutes);
  const lvl = r.level ? `רמה ${r.level} ← ${r.level + 1}` : "";
  $("resEtaSub").textContent = r.exp_to_level == null ? "" :
    (r.eta_minutes == null ? `צריך עוד ${num(r.exp_to_level)} EXP` : `עוד ${num(r.exp_to_level)} EXP · ${lvl}`);
  $("resGained").textContent = signed(r.exp_gained);
  $("resGained").className = r.exp_gained >= 0 ? "up" : "down";
  $("resPct").textContent = (r.pct_gained >= 0 ? "+" : "") + r.pct_gained.toFixed(2) + "%";
  $("resLevels").textContent = r.levels_gained ? `+${r.levels_gained}` : "0";
  $("resMinutes").textContent = duration(r.minutes);

  $("startCrop").src = s.start.crop;
  $("startVals").textContent = readingText(s.start);
  $("endRow").hidden = !s.end;
  if (s.end) { $("endCrop").src = s.end.crop; $("endVals").textContent = readingText(s.end); }

  $("mapVal").textContent = s.map || "לא זוהתה. אפשר להוסיף בתיקון ידני";
  $("mapVal").className = "proof-map" + (s.map ? "" : " missing");
  $("eMap").value = s.map || "";
  $("eStartExp").value = s.start.exp; $("eStartPct").value = s.start.pct;
  document.querySelectorAll(".edit-end").forEach((el) => { el.hidden = !s.end; });
  if (s.end) { $("eEndExp").value = s.end.exp; $("eEndPct").value = s.end.pct; }
}

async function loadHistory() {
  const rows = await api.history();
  const body = $("histBody");
  body.replaceChildren();
  $("histEmpty").hidden = rows.length > 0;
  for (const r of rows) {
    const tr = document.createElement("tr");
    const cell = (text, cls) => { const td = document.createElement("td"); td.textContent = text; if (cls) td.className = cls; tr.appendChild(td); return td; };
    cell(shortDate(r.date));
    const mapCell = cell("", "map");
    const mapText = document.createElement("span");
    mapText.dir = "ltr";  // English names: ellipsis at the end, not the start
    mapText.textContent = r.map || "—";
    mapCell.title = r.map || "";
    mapCell.appendChild(mapText);
    cell(r.minutes ? String(Math.round(+r.minutes * 10) / 10) : "—", "num");
    cell(num(+r.exp_per_min), "num").dir = "ltr";
    const lv = cell("");
    const pill = document.createElement("span");
    pill.className = "lvl-pill" + (+r.levels_gained ? "" : " zero");
    pill.textContent = +r.levels_gained ? `+${r.levels_gained}` : "0";
    lv.appendChild(pill);
    body.appendChild(tr);
  }
}
function shortDate(d) {
  // "2026-10-11 01:30" -> "11/10 01:30"
  const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})/.exec(d || "");
  return m ? `${+m[3]}/${+m[2]} ${m[4]}` : d || "";
}

// ---------- polling ----------
async function tick() {
  let s;
  try { s = await api.get_state(); } catch { return; }
  renderGame(s.game);
  renderCompact(s);
  if (s.phase !== lastPhase && s.phase === "countdown" && s.game.overlay && !compact) setCompact(true, false);
  if (s.phase !== lastPhase) {
    showView(s.phase);
    if (s.phase === "idle" || s.phase === "cancelled") $("timerTitle").textContent = "טיימר פארם";
    if (s.phase === "running" || s.phase === "countdown") $("timerTitle").textContent = "טיימר פארם" + (s.map ? ` · \u2066${s.map}\u2069` : "");
    if (s.phase === "done") { renderDone(s); $("editForm").hidden = true; loadHistory(); }
    if (s.phase === "error") $("errorText").textContent = s.error;
    lastPhase = s.phase;
  }
  if (s.phase === "countdown") $("countdownNum").textContent = Math.max(1, Math.ceil(s.countdown));
  if (s.phase === "running") renderRunning(s);
}

// ---------- actions ----------
function setMinutes(m) {
  $("minutes").value = m;
  const pick = $("cMinutes");
  if (pick && ![...pick.options].some((o) => +o.value === +m)) pick.add(new Option(`${m} דק'`, m));
  if (pick) pick.value = String(+m);
  document.querySelectorAll("#presets .tab").forEach((t) => t.classList.toggle("active", +t.dataset.min === +m));
}

function wire() {
  document.querySelectorAll("#presets .tab").forEach((t) => t.addEventListener("click", () => setMinutes(t.dataset.min)));
  $("minutes").addEventListener("input", () => setMinutes($("minutes").value));

  $("startBtn").addEventListener("click", async () => {
    const minutes = +$("minutes").value;
    store.set("minutes", minutes);
    const res = await api.start(minutes, 3);
    if (!res.ok) { showTest({ ok: false, error: res.error }); return; }
    lastPhase = null; tick();
  });
  $("cancelBtn").addEventListener("click", () => api.reset().then(tick));
  $("stopBtn").addEventListener("click", () => api.stop());
  $("againBtn").addEventListener("click", () => api.reset().then(() => { lastPhase = null; tick(); }));
  $("backBtn").addEventListener("click", () => api.reset().then(() => { lastPhase = null; tick(); }));
  $("shotsBtn").addEventListener("click", () => api.open_shots());

  $("testBtn").addEventListener("click", async () => {
    const btn = $("testBtn");
    btn.disabled = true; btn.textContent = "קורא מהמסך…";
    try { showTest(await api.test_read()); }
    finally { btn.disabled = !gameFound; btn.textContent = "בדיקת קריאה מהמסך"; }
  });

  $("editBtn").addEventListener("click", () => { $("editForm").hidden = !$("editForm").hidden; $("editError").hidden = true; });
  $("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api.recompute($("eStartExp").value, $("eStartPct").value,
                                    $("eEndExp").value || 0, $("eEndPct").value || 0, $("eMap").value);
    if (!res.ok) { $("editError").hidden = false; $("editError").textContent = res.error; return; }
    renderDone(await api.get_state());
    $("editForm").hidden = true;
    loadHistory();
  });

  // title-bar buttons sit inside the drag region: don't let a click nudge the window
  document.querySelectorAll(".tb-btn, .c-btn, .c-dur").forEach((b) => b.addEventListener("mousedown", (e) => e.stopPropagation()));
  $("minBtn").addEventListener("click", () => api.minimize());
  $("closeBtn").addEventListener("click", () => api.close());

  $("pinBtn").addEventListener("click", () => {
    const on = !$("pinBtn").classList.contains("active");
    $("pinBtn").classList.toggle("active", on);
    $("pinBtn").setAttribute("aria-pressed", on);
    store.set("pin", on ? "1" : "0");
    api.set_on_top(on);
  });
}

function showTest(r) {
  const box = $("testResult");
  box.hidden = false;
  box.replaceChildren();
  box.className = "test-result" + (r.ok ? "" : " bad");
  if (!r.ok) { box.textContent = r.error; return; }
  const img = document.createElement("img"); img.src = r.crop; img.alt = "";
  const t = document.createElement("div"); t.dir = "ltr"; t.textContent = readingText(r);
  const ok = document.createElement("div"); ok.textContent = "✓ הקריאה עובדת, אפשר להתחיל";
  ok.className = "up";
  box.append(img, t, ok);
  showMap(r.map);
}

function showMap(name) {
  $("mapNote").classList.toggle("found", !!name);
  $("mapNoteText").textContent = name || "לא רואה מיני-מפה. תזוהה בתחילת הטיימר אם תיפתח";
  $("mapNoteText").dir = name ? "ltr" : "rtl";
  $("mapNote").title = name || "";
}

// ---------- updates ----------
function showUpdate(info) {
  if (!info) return;
  $("updateVersion").textContent = "v" + info.version;
  $("updateBar").hidden = false;
}

function wireUpdate() {
  $("updateNotes").addEventListener("click", (e) => { e.preventDefault(); api.open_release(); });
  $("updateBtn").addEventListener("click", async () => {
    const btn = $("updateBtn");
    btn.disabled = true; btn.textContent = "מעדכן…";
    const res = await api.start_update();  // on success the app closes and reopens updated
    if (!res.ok) { btn.disabled = false; btn.textContent = "עדכון"; $("updateBar").title = res.error; alert(res.error); }
  });
}

// ---------- global show/hide key ----------
async function applyHotkey(spec) {
  const res = await api.set_hotkey(spec);
  const chip = $("keyChip");
  chip.classList.toggle("taken", !res.ok);
  chip.title = res.ok
    ? (spec === "off" ? "אין מקש להצגה/הסתרה" : `${spec} מציג ומסתיר את EXPERT, גם מתוך המשחק`)
    : `${spec} תפוס ע״י Windows או תוכנה אחרת. בחר מקש אחר`;
}

function wireHotkey() {
  const pick = $("hotkey");
  pick.value = store.get("hotkey", "F11");
  if (!pick.value) pick.value = "F11";
  pick.addEventListener("change", () => { store.set("hotkey", pick.value); applyHotkey(pick.value); });
  applyHotkey(pick.value);
}

// ---------- compact mode (full-screen play) ----------
let compact = false;
let lastCompact = "";

function setCompact(on, remember = true) {
  if (on === compact) return;
  compact = on;
  document.body.classList.toggle("compact-mode", on);
  if (remember) store.set("compact", on ? "1" : "0");
  api.compact(on).then(() => {
    if (on) { lastCompact = ""; fitCompact(); } else { lastFit = 0; fitWindow(); }
  });
}

function fitCompact() {
  if (!compact) return;
  const w = Math.ceil($("compact").getBoundingClientRect().width) + 4;  // + body border
  const key = String(w);
  if (key === lastCompact) return;
  lastCompact = key;
  api.fit_compact(w, 50, window.devicePixelRatio || 1);
}

function shortNum(n) {
  return n != null && Math.abs(n) >= 10000 ? Math.round(n / 1000) + "K" : num(n);
}

function renderCompact(s) {
  const views = { idle: "idle", cancelled: "idle", countdown: "countdown", running: "running",
                  finalizing: "finalizing", done: "done", error: "error" };
  const view = views[s.phase] || "idle";
  document.querySelectorAll(".c-view").forEach((v) => v.classList.toggle("on", v.dataset.phase === view));
  if (view === "countdown") $("cCount").textContent = Math.max(1, Math.ceil(s.countdown));
  if (view === "running") {
    $("cClock").textContent = clock(s.remaining);
    $("cRate").textContent = s.live && s.live.minutes > 0 ? num(s.live.exp_per_min) : "—";
  }
  if (view === "done" && s.result) {
    $("cDoneRate").textContent = num(s.result.exp_per_min);
    $("cDoneHour").textContent = shortNum(s.result.exp_per_hour);
    $("cDoneEta").textContent = s.result.eta_minutes == null ? "—" : etaShort(s.result.eta_minutes);
  }
  if (view === "error") $("cError").textContent = s.error || "";
  $("cStart").disabled = !gameFound;
  const live = s.live || s.result;
  $("compact").title = live ? `EXP שנצבר: ${signed(live.exp_gained)}` + (s.map ? ` · ${s.map}` : "") : "";
}

function wireCompact() {
  $("compactBtn").addEventListener("click", () => setCompact(true));
  $("cExpand").addEventListener("click", () => setCompact(false));
  $("cStart").addEventListener("click", async () => {
    const minutes = +$("cMinutes").value;
    setMinutes(minutes);
    store.set("minutes", minutes);
    const res = await api.start(minutes, 3);
    if (!res.ok) { setCompact(false); showTest({ ok: false, error: res.error }); return; }
    lastPhase = null; tick();
  });
  $("cCancel").addEventListener("click", () => api.reset().then(() => { lastPhase = null; tick(); }));
  $("cStop").addEventListener("click", () => api.stop());
  $("cAgain").addEventListener("click", () => api.reset().then(() => { lastPhase = null; tick(); }));
  new ResizeObserver(fitCompact).observe($("compact"));
}

// the window hugs its content: report the height whenever it changes (phase, history, edit form)
let lastFit = 0;
function fitWindow() {
  if (compact) return;
  const scroll = document.querySelector(".scroll");
  const pad = parseFloat(getComputedStyle(scroll).paddingTop) + parseFloat(getComputedStyle(scroll).paddingBottom);
  const total = document.querySelector(".titlebar").offsetHeight + $("content").offsetHeight + pad + 4;  // + body border
  if (Math.abs(total - lastFit) < 2) return;
  lastFit = total;
  api.fit_height(total, window.devicePixelRatio || 1);
}

window.addEventListener("pywebviewready", () => {
  api = window.pywebview.api;
  setMinutes(store.get("minutes", "10"));
  if (store.get("pin", "1") === "0") { $("pinBtn").classList.remove("active"); api.set_on_top(false); }
  wire();
  wireUpdate();
  wireCompact();
  wireHotkey();
  if (store.get("compact", "0") === "1") setCompact(true);
  api.app_info().then((i) => { $("appVersion").textContent = "v" + i.version; });
  api.check_update().then(showUpdate);
  $("repoLink").addEventListener("click", (e) => { e.preventDefault(); api.open_repo(); });
  loadHistory();
  tick();
  setInterval(tick, 400);
  new ResizeObserver(fitWindow).observe($("content"));
});
