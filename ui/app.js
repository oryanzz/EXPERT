const $ = (id) => document.getElementById(id);
const intFmt = new Intl.NumberFormat("en-US");
let api = null;
let lastPhase = null;
let gameFound = false;
let lastTest = null;  // last screen-reading test, re-shown when the language changes

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
};

// ---------- language (texts: i18n.js) ----------
let LANG = "he";

function t(key, vars = {}) {
  const s = STRINGS[LANG][key] ?? STRINGS.he[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}
// errors and warnings arrive from Python as short codes (covered, busy, end_failed...)
function errText(code, detail = "") {
  const key = `err.${code}`;
  return !code ? "" : STRINGS[LANG][key] ? t(key, { detail }) : String(code);
}
function warnText(code, reason = "") {
  const key = `warn.${code}`;
  return !code ? "" : STRINGS[LANG][key] ? t(key, { reason: errText(reason) }) : String(code);
}

function applyLang(lang) {
  LANG = STRINGS[lang] ? lang : "en";
  const root = document.documentElement;
  root.lang = LANG;
  root.dir = LANG === "he" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n, { n: el.dataset.n }); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
    if (el.tagName === "BUTTON") el.setAttribute("aria-label", el.title);
  });
  root.classList.remove("i18n-wait");
}

function switchLang() {
  const next = LANG === "he" ? "en" : "he";
  store.set("lang", next);
  applyLang(next);
  if (lastTest) showTest(lastTest);
  lastPhase = null;  // re-render the current view in the new language
  loadHistory();
  tick();
}

// ---------- formatting ----------
function num(n) {
  if (n == null || !isFinite(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e7) return (n / 1e6).toFixed(1) + "M";
  return intFmt.format(Math.round(n));
}
function signed(n) { return (n > 0 ? "+" : "") + num(n); }

function hoursText(h) { return h === 1 ? t("eta.hour1") : h === 2 ? t("eta.hour2") : t("eta.hours", { n: h }); }
function minutesText(m) { return m === 1 ? t("eta.min1") : t("eta.mins", { n: m }); }
function etaLong(min) {
  if (min == null || !isFinite(min)) return "—";
  if (min < 1) return t("eta.lt_min");
  const m = Math.round(min);
  if (m >= 48 * 60) return t("eta.days", { n: (m / 1440).toFixed(1) });
  if (m < 60) return minutesText(m);
  const h = Math.floor(m / 60), r = m % 60;
  return r ? t("eta.and", { h: hoursText(h), m: minutesText(r) }) : hoursText(h);
}
function etaShort(min) {
  if (min == null || !isFinite(min)) return "—";
  if (min < 1) return t("u.lt_min");
  const m = Math.round(min);
  if (m < 60) return t("u.min", { n: m });
  if (m >= 48 * 60) return t("u.days", { n: (m / 1440).toFixed(1) });
  return t("u.hm", { h: Math.floor(m / 60), mm: String(m % 60).padStart(2, "0") });
}
function clock(sec) {
  sec = Math.max(0, Math.ceil(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const mm = String(m).padStart(h ? 2 : 1, "0"), ss = String(s).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
function duration(min) {
  if (min < 1) return t("u.sec", { n: Math.round(min * 60) });
  return t("u.min", { n: Math.round(min) });
}
function readingText(r) {
  return `${intFmt.format(r.exp)} [${r.pct.toFixed(2)}%]` + (r.level ? `  Lv.${r.level}` : "");
}

// ---------- views ----------
const VIEWS = { idle: "idle", cancelled: "idle", countdown: "countdown", running: "running",
                finalizing: "finalizing", done: "done", error: "error" };
const BADGES = {
  idle: ["badge.ready", ""], cancelled: ["badge.ready", ""], countdown: ["badge.starting", "live"],
  running: ["badge.recording", "live"], finalizing: ["badge.summing", "live"], done: ["badge.done", "done"],
  error: ["badge.error", "err"],
};

function showView(phase) {
  const name = VIEWS[phase] || "idle";
  document.querySelectorAll(".view").forEach((v) => { v.hidden = v.id !== `view-${name}`; });
  const [key, cls] = BADGES[phase] || BADGES.idle;
  const b = $("phaseBadge");
  b.textContent = t(key);
  b.className = "badge " + cls;
}

function renderGame(g) {
  const chip = $("gameChip");
  gameFound = g.found && !g.minimized;
  // ⁦…⁩ isolates the LTR size so RTL layout doesn't flip "1920×1200"
  if (g.found && !g.minimized) { chip.className = "chip ok"; $("gameText").textContent = t("game.ok", { size: `⁦${g.size}⁩` }); }
  else if (g.minimized) { chip.className = "chip warn"; $("gameText").textContent = t("game.minimized"); }
  else { chip.className = "chip bad"; $("gameText").textContent = t("game.missing"); }
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
    const lv = n === 1 ? t("run.level_up") : n > 1 ? t("run.levels_up", { n }) : "";
    $("liveStatus").textContent = t("run.last", { s: Math.round(live.last_ago), pct: live.pct.toFixed(2) }) + lv;
  } else {
    $("liveRate").textContent = "—"; $("liveGained").textContent = "—"; $("liveEta").textContent = "—";
    $("liveStatus").textContent = t("run.waiting");
  }
  if (s.failed_reads) $("liveStatus").textContent += t("run.skipped", { n: s.failed_reads });
}

function renderDone(s) {
  const r = s.result;
  $("timerTitle").textContent = t("timer.summary") + (s.map ? ` · ⁦${s.map}⁩` : "");
  const warning = warnText(s.warning, s.warning_reason);
  $("doneWarn").hidden = !warning;
  $("doneWarn").textContent = warning;
  $("resRate").textContent = num(r.exp_per_min);
  $("resHour").textContent = num(r.exp_per_hour);
  $("resEta").textContent = r.eta_minutes == null ? "—" : etaLong(r.eta_minutes);
  const lvl = r.level ? t("done.lvl", { a: r.level, b: r.level + 1 }) : "";
  $("resEtaSub").textContent = r.exp_to_level == null ? "" :
    (r.eta_minutes == null || !lvl ? t("done.need", { n: num(r.exp_to_level) }) : t("done.left", { n: num(r.exp_to_level), lvl }));
  $("resGained").textContent = signed(r.exp_gained);
  $("resGained").className = r.exp_gained >= 0 ? "up" : "down";
  $("resPct").textContent = (r.pct_gained >= 0 ? "+" : "") + r.pct_gained.toFixed(2) + "%";
  $("resLevels").textContent = r.levels_gained ? `+${r.levels_gained}` : "0";
  $("resMinutes").textContent = duration(r.minutes);

  $("startCrop").src = s.start.crop;
  $("startVals").textContent = readingText(s.start);
  $("endRow").hidden = !s.end;
  if (s.end) { $("endCrop").src = s.end.crop; $("endVals").textContent = readingText(s.end); }

  $("mapVal").textContent = s.map || t("done.map_none");
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
    if (s.phase === "idle" || s.phase === "cancelled") $("timerTitle").textContent = t("timer.title");
    if (s.phase === "running" || s.phase === "countdown") $("timerTitle").textContent = t("timer.title") + (s.map ? ` · ⁦${s.map}⁩` : "");
    if (s.phase === "done") { renderDone(s); $("editForm").hidden = true; loadHistory(); }
    if (s.phase === "error") $("errorText").textContent = errText(s.error, s.error_detail);
    lastPhase = s.phase;
  }
  if (s.phase === "countdown") $("countdownNum").textContent = Math.max(1, Math.ceil(s.countdown));
  if (s.phase === "running") renderRunning(s);
}

// ---------- actions ----------
function setMinutes(m) {
  $("minutes").value = m;
  const pick = $("cMinutes");
  if (pick && ![...pick.options].some((o) => +o.value === +m)) {
    const o = new Option(t("u.min", { n: m }), m);
    o.dataset.i18n = "u.min"; o.dataset.n = m;  // relabelled when the language changes
    pick.add(o);
  }
  if (pick) pick.value = String(+m);
  document.querySelectorAll("#presets .tab").forEach((tab) => tab.classList.toggle("active", +tab.dataset.min === +m));
}

function wire() {
  document.querySelectorAll("#presets .tab").forEach((tab) => tab.addEventListener("click", () => setMinutes(tab.dataset.min)));
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
    btn.disabled = true; btn.textContent = t("idle.testing");
    try { showTest(await api.test_read()); }
    finally { btn.disabled = !gameFound; btn.textContent = t("idle.test"); }
  });

  $("editBtn").addEventListener("click", () => { $("editForm").hidden = !$("editForm").hidden; $("editError").hidden = true; });
  $("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const res = await api.recompute($("eStartExp").value, $("eStartPct").value,
                                    $("eEndExp").value || 0, $("eEndPct").value || 0, $("eMap").value);
    if (!res.ok) { $("editError").hidden = false; $("editError").textContent = errText(res.error); return; }
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
  $("langLink").addEventListener("click", (e) => { e.preventDefault(); switchLang(); });
}

function showTest(r) {
  lastTest = r;
  const box = $("testResult");
  box.hidden = false;
  box.replaceChildren();
  box.className = "test-result" + (r.ok ? "" : " bad");
  if (!r.ok) { box.textContent = errText(r.error); return; }
  const img = document.createElement("img"); img.src = r.crop; img.alt = "";
  const reading = document.createElement("div"); reading.dir = "ltr"; reading.textContent = readingText(r);
  const ok = document.createElement("div"); ok.textContent = t("idle.test_ok");
  ok.className = "up";
  box.append(img, reading, ok);
  showMap(r.map);
}

function showMap(name) {
  $("mapNote").classList.toggle("found", !!name);
  $("mapNoteText").textContent = name || t("idle.map_none");
  if (name) $("mapNoteText").dir = "ltr"; else $("mapNoteText").removeAttribute("dir");
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
    btn.disabled = true; btn.textContent = t("up.updating");
    const res = await api.start_update();  // on success the app closes and reopens updated
    if (!res.ok) {
      btn.disabled = false; btn.textContent = t("up.button");
      $("updateBar").title = errText(res.error); alert(errText(res.error));
    }
  });
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
  if (view === "error") $("cError").textContent = errText(s.error, s.error_detail);
  $("cStart").disabled = !gameFound;
  const live = s.live || s.result;
  $("compact").title = live ? t("c.gained", { n: signed(live.exp_gained) }) + (s.map ? ` · ${s.map}` : "") : "";
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

// a language the user picked applies at once; otherwise the page stays hidden until Python
// reports the Windows language (i18n-wait), so it never flashes the wrong one
const savedLang = store.get("lang", "");
if (savedLang) applyLang(savedLang);
setTimeout(() => document.documentElement.classList.remove("i18n-wait"), 2000);  // never stay hidden

window.addEventListener("pywebviewready", () => {
  api = window.pywebview.api;
  setMinutes(store.get("minutes", "10"));
  if (store.get("pin", "1") === "0") { $("pinBtn").classList.remove("active"); api.set_on_top(false); }
  wire();
  wireUpdate();
  wireCompact();
  if (store.get("compact", "0") === "1") setCompact(true);
  api.app_info().then((i) => {
    $("appVersion").textContent = "v" + i.version;
    if (!savedLang) { applyLang(i.lang); lastPhase = null; tick(); }
  });
  api.check_update().then(showUpdate);
  $("repoLink").addEventListener("click", (e) => { e.preventDefault(); api.open_repo(); });
  loadHistory();
  tick();
  setInterval(tick, 400);
  new ResizeObserver(fitWindow).observe($("content"));
});
