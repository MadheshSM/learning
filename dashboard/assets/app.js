/* ---------------------------------------------------------------------
   Learning Performance Dashboard — shared rendering logic
   Reads window.DASHBOARD_DATA.<track> (populated by data/*.data.js,
   loaded as plain <script> tags so this works via file:// with no server).
--------------------------------------------------------------------- */

const STATUS_ORDER = ["Not Started", "In Progress", "Practiced", "Done"];
const STATUS_VAR = {
  "Not Started": "--status-not-started",
  "In Progress": "--status-in-progress",
  "Practiced": "--status-practiced",
  "Done": "--status-done",
};
const TRACK_META = {
  node: { label: "Node", href: "node.html", var: "--node-color" },
  angular: { label: "Angular", href: "angular.html", var: "--angular-color" },
  python: { label: "Python", href: "python.html", var: "--python-color" },
  cognizant: { label: "Cognizant", href: "cognizant.html", var: "--cognizant-color" },
};

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function pct(part, total) {
  if (!total) return 0;
  return Math.round((part / total) * 1000) / 10;
}

/* ---------------------------------------------------------------------
   Theme toggle
--------------------------------------------------------------------- */

function initTheme() {
  const saved = localStorage.getItem("dashboard-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  const btn = document.querySelector(".theme-toggle");
  if (!btn) return;
  const sync = () => {
    const current = document.documentElement.getAttribute("data-theme");
    const isDark = current
      ? current === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    btn.textContent = isDark ? "☀" : "☾";
  };
  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const isDark = current
      ? current === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    const next = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("dashboard-theme", next);
    sync();
  });
  sync();
}

/* ---------------------------------------------------------------------
   Stats
--------------------------------------------------------------------- */

function computeStats(data) {
  const concepts = data.concepts || [];
  const counts = { "Not Started": 0, "In Progress": 0, "Practiced": 0, "Done": 0 };
  concepts.forEach((c) => { counts[c.status] = (counts[c.status] || 0) + 1; });

  const phaseOrder = [];
  const phaseMap = new Map();
  concepts.forEach((c) => {
    if (!phaseMap.has(c.phase)) {
      phaseMap.set(c.phase, { name: c.phase, total: 0, counts: { "Not Started": 0, "In Progress": 0, "Practiced": 0, "Done": 0 } });
      phaseOrder.push(c.phase);
    }
    const p = phaseMap.get(c.phase);
    p.total += 1;
    p.counts[c.status] = (p.counts[c.status] || 0) + 1;
  });
  const phases = phaseOrder.map((name) => {
    const p = phaseMap.get(name);
    p.pctDone = pct(p.counts["Done"], p.total);
    return p;
  });

  const currentPhase = phases.find((p) => p.pctDone < 100);

  const dates = concepts
    .flatMap((c) => [c.dateStarted, c.dateCompleted])
    .filter(Boolean)
    .sort();
  const lastActivity = dates.length ? dates[dates.length - 1] : null;

  const checklist = data.checklist || [];
  const checklistDone = checklist.filter((i) => i.completed).length;

  return {
    total: concepts.length,
    counts,
    pctDone: pct(counts["Done"], concepts.length),
    phases,
    currentPhase: currentPhase ? currentPhase.name : (phases.length ? phases[phases.length - 1].name : null),
    allDone: !!concepts.length && counts["Done"] === concepts.length,
    lastActivity,
    checklistTotal: checklist.length,
    checklistDone,
    checklistPct: pct(checklistDone, checklist.length),
  };
}

function shortPhaseName(name) {
  return name.replace(/^Phase\s*\d+:\s*/i, "").replace(/^Capstone$/, "Capstone");
}

/* ---------------------------------------------------------------------
   Time & pace — logged from the "Time Log" sheet (Date | Hours Spent | Notes)
--------------------------------------------------------------------- */

function parseISODate(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function daysBetween(a, b) {
  const MS = 86400000;
  return Math.round((b - a) / MS);
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function computeTimeStats(data, stats) {
  const log = data.timeLog || [];
  const totalHours = Math.round(log.reduce((a, e) => a + e.hours, 0) * 10) / 10;

  if (!log.length) {
    return { hasData: false, totalHours: 0, entryCount: 0 };
  }

  const today = new Date();
  const firstDate = parseISODate(log[0].date);
  const lastDate = parseISODate(log[log.length - 1].date);
  const elapsedDays = Math.max(1, daysBetween(firstDate, today) + 1);
  const avgHoursPerDay = Math.round((totalHours / elapsedDays) * 100) / 100;

  const doneCount = stats.counts["Done"];
  const remainingConcepts = stats.total - doneCount;
  const hoursPerConcept = doneCount > 0 ? totalHours / doneCount : null;
  const estRemainingHours = hoursPerConcept !== null ? Math.round(remainingConcepts * hoursPerConcept * 10) / 10 : null;
  const projectedDays = (estRemainingHours !== null && avgHoursPerDay > 0) ? Math.ceil(estRemainingHours / avgHoursPerDay) : null;
  const projectedFinishDate = projectedDays !== null ? formatDate(addDays(today, projectedDays)) : null;

  return {
    hasData: true,
    totalHours,
    entryCount: log.length,
    firstDate: log[0].date,
    lastDate: log[log.length - 1].date,
    elapsedDays,
    avgHoursPerDay,
    hoursPerConcept,
    estRemainingHours,
    projectedDays,
    projectedFinishDate,
    allDone: stats.allDone,
    recent: log.slice().reverse(),
  };
}

/* ---------------------------------------------------------------------
   Stat tiles
--------------------------------------------------------------------- */

function renderStatTiles(el, tiles) {
  el.innerHTML = "";
  el.className = "stat-grid";
  tiles.forEach((t) => {
    const tile = document.createElement("div");
    tile.className = "stat-tile";
    tile.innerHTML = `
      <div class="label">${t.label}</div>
      <div class="value${t.good ? " good" : ""}">${t.value}</div>
    `;
    el.appendChild(tile);
  });
}

/* ---------------------------------------------------------------------
   Overall dashboard: track cards + comparison chart
--------------------------------------------------------------------- */

function renderTrackCards(el, entries) {
  el.innerHTML = "";
  el.className = "track-grid";
  entries.forEach(({ key, data, stats, timeStats }) => {
    const meta = TRACK_META[key];
    const card = document.createElement("div");
    card.className = "track-card";
    let finishLine = "Log time to see a completion estimate";
    if (timeStats && timeStats.hasData) {
      finishLine = stats.allDone
        ? `Finished — ${timeStats.totalHours} hrs logged`
        : (timeStats.projectedFinishDate ? `Projected finish: <strong>${timeStats.projectedFinishDate}</strong>` : `${timeStats.totalHours} hrs logged so far`);
    }
    card.innerHTML = `
      <div class="track-card-head">
        <div>
          <div class="track-name"><span class="track-dot" style="background:var(${meta.var})"></span>${data.title}</div>
          <div class="track-sub">${data.subtitle}</div>
        </div>
        <div class="track-pct">${stats.pctDone}%</div>
      </div>
      <div class="track-meter-track"><div class="track-meter-fill" style="width:${stats.pctDone}%;background:var(${meta.var})"></div></div>
      <div class="track-facts">
        <span>${stats.counts["Done"]} / ${stats.total} concepts done</span>
        <span>Checklist ${stats.checklistDone}/${stats.checklistTotal}</span>
      </div>
      <div class="track-current">
        <div>Current focus: <strong>${stats.allDone ? "All phases complete" : shortPhaseName(stats.currentPhase || "—")}</strong></div>
        <div style="margin-top:4px;">${finishLine}</div>
      </div>
      <a class="track-link" href="${meta.href}">Open ${meta.label} dashboard →</a>
    `;
    el.appendChild(card);
  });
}

function renderCompareChart(el, entries) {
  el.innerHTML = "";
  entries.forEach(({ key, data, stats }) => {
    const meta = TRACK_META[key];
    const row = document.createElement("div");
    row.className = "compare-row";
    row.innerHTML = `
      <div class="compare-label"><span class="track-dot" style="background:var(${meta.var})"></span>${data.title}</div>
      <div class="compare-track">
        <div class="compare-fill" style="width:${Math.max(stats.pctDone, 2)}%;background:var(${meta.var})"></div>
      </div>
      <div class="compare-value">${stats.pctDone}%</div>
    `;
    el.appendChild(row);
  });
}

/* ---------------------------------------------------------------------
   Phase breakdown — stacked bar (part-to-whole) + table-view toggle
--------------------------------------------------------------------- */

function renderLegend(el) {
  el.innerHTML = "";
  el.className = "legend";
  STATUS_ORDER.forEach((s) => {
    const item = document.createElement("span");
    item.className = "legend-item";
    item.innerHTML = `<span class="legend-swatch" style="background:var(${STATUS_VAR[s]})"></span>${s}`;
    el.appendChild(item);
  });
}

function renderPhaseBars(el, phases) {
  el.innerHTML = "";
  phases.forEach((p) => {
    const row = document.createElement("div");
    row.className = "phase-row";
    const segs = STATUS_ORDER.map((s) => {
      const w = pct(p.counts[s], p.total);
      if (!w) return "";
      return `<div class="stack-seg" style="width:${w}%;background:var(${STATUS_VAR[s]})" title="${s}: ${p.counts[s]}"></div>`;
    }).join("");
    row.innerHTML = `
      <div class="phase-row-head">
        <span class="name">${shortPhaseName(p.name)}</span>
        <span class="pct">${p.counts["Done"]}/${p.total} done · ${p.pctDone}%</span>
      </div>
      <div class="stack-bar">${segs}</div>
    `;
    el.appendChild(row);
  });
}

function renderPhaseTable(el, phases) {
  el.innerHTML = "";
  const table = document.createElement("table");
  table.className = "data-table";
  table.innerHTML = `
    <thead><tr>
      <th>Phase</th><th>Total</th><th>Not Started</th><th>In Progress</th><th>Practiced</th><th>Done</th><th>% Complete</th>
    </tr></thead>
    <tbody>
      ${phases.map((p) => `
        <tr>
          <td>${shortPhaseName(p.name)}</td>
          <td>${p.total}</td>
          <td>${p.counts["Not Started"]}</td>
          <td>${p.counts["In Progress"]}</td>
          <td>${p.counts["Practiced"]}</td>
          <td>${p.counts["Done"]}</td>
          <td>${p.pctDone}%</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  const wrap = document.createElement("div");
  wrap.className = "overflow-x";
  wrap.appendChild(table);
  el.appendChild(wrap);
}

function initPhaseBreakdown(chartEl, tableEl, toggleEl, phases) {
  renderPhaseBars(chartEl, phases);
  renderPhaseTable(tableEl, phases);
  tableEl.style.display = "none";
  const [chartBtn, tableBtn] = toggleEl.querySelectorAll("button");
  chartBtn.addEventListener("click", () => {
    chartEl.style.display = "";
    tableEl.style.display = "none";
    chartBtn.classList.add("active");
    tableBtn.classList.remove("active");
  });
  tableBtn.addEventListener("click", () => {
    chartEl.style.display = "none";
    tableEl.style.display = "";
    tableBtn.classList.add("active");
    chartBtn.classList.remove("active");
  });
}

/* ---------------------------------------------------------------------
   Concept table
--------------------------------------------------------------------- */

function renderConceptTable(el, concepts) {
  const rows = [];
  let lastPhase = null;
  concepts.forEach((c) => {
    if (c.phase !== lastPhase) {
      rows.push(`<tr class="phase-group"><td colspan="7">${c.phase}</td></tr>`);
      lastPhase = c.phase;
    }
    rows.push(`
      <tr>
        <td>${c.id}</td>
        <td>${c.concept}</td>
        <td><span class="status-badge"><span class="status-dot" style="background:var(${STATUS_VAR[c.status]})"></span>${c.status}</span></td>
        <td class="yn ${c.practiceDone ? "yes" : "no"}">${c.practiceDone ? "Yes" : "No"}</td>
        <td class="yn ${c.selfCheckPassed ? "yes" : "no"}">${c.selfCheckPassed ? "Yes" : "No"}</td>
        <td>${c.dateCompleted || c.dateStarted || "—"}</td>
        <td class="notes-cell">${c.notes || ""}</td>
      </tr>
    `);
  });
  const table = document.createElement("table");
  table.className = "data-table";
  table.innerHTML = `
    <thead><tr>
      <th>#</th><th>Concept</th><th>Status</th><th>Practiced</th><th>Self-check</th><th>Date</th><th>Notes</th>
    </tr></thead>
    <tbody>${rows.join("")}</tbody>
  `;
  el.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "overflow-x";
  wrap.appendChild(table);
  el.appendChild(wrap);
}

/* ---------------------------------------------------------------------
   Self-assessment checklist
--------------------------------------------------------------------- */

function renderChecklist(el, items) {
  el.innerHTML = "";
  el.className = "checklist";
  if (!items.length) {
    el.innerHTML = `<div class="empty-state">No checklist items.</div>`;
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "checklist-item" + (item.completed ? " done" : "");
    row.innerHTML = `
      <span class="checklist-mark">${item.completed ? "✓" : ""}</span>
      <span class="checklist-text">${item.item}</span>
    `;
    el.appendChild(row);
  });
}

/* ---------------------------------------------------------------------
   Time & pace section (standalone track pages)
--------------------------------------------------------------------- */

function renderTimeStatTiles(el, ts) {
  el.innerHTML = "";
  el.className = "stat-grid";
  if (!ts.hasData) {
    el.innerHTML = `<div class="empty-state">No time logged yet — add rows (Date, Hours Spent, Notes) to the <code>Time Log</code> sheet in <code>learning_tracker.xlsx</code>, then re-run <code>generate_data.py</code>.</div>`;
    return;
  }
  const tiles = [
    { label: "Hours logged", value: ts.totalHours },
    { label: "Days since you started", value: ts.elapsedDays },
    { label: "Avg hours / day", value: ts.avgHoursPerDay },
    {
      label: ts.allDone ? "Finished" : "Projected finish",
      value: ts.allDone ? "🎉" : (ts.projectedFinishDate || "Not enough data"),
      good: ts.allDone,
    },
  ];
  tiles.forEach((t) => {
    const tile = document.createElement("div");
    tile.className = "stat-tile";
    tile.innerHTML = `<div class="label">${t.label}</div><div class="value${t.good ? " good" : ""}">${t.value}</div>`;
    el.appendChild(tile);
  });
}

function renderPaceNote(el, ts) {
  if (!ts.hasData) { el.innerHTML = ""; return; }
  if (ts.allDone) {
    el.textContent = `All concepts done — ${ts.totalHours} hours logged over ${ts.elapsedDays} days. Nice work.`;
    return;
  }
  if (ts.hoursPerConcept === null) {
    el.textContent = `${ts.totalHours} hours logged so far, averaging ${ts.avgHoursPerDay} hrs/day. Mark a concept "Done" to unlock a completion estimate.`;
    return;
  }
  el.textContent = `At your current pace (${ts.avgHoursPerDay} hrs/day, ~${ts.hoursPerConcept.toFixed(1)} hrs/concept), the remaining work is roughly ${ts.estRemainingHours} hours — about ${ts.projectedDays} more days, landing around ${ts.projectedFinishDate}.`;
}

function renderTimeLogTable(el, entries) {
  el.innerHTML = "";
  if (!entries.length) {
    el.innerHTML = `<div class="empty-state">No sessions logged yet.</div>`;
    return;
  }
  const table = document.createElement("table");
  table.className = "data-table";
  table.innerHTML = `
    <thead><tr><th>Date</th><th>Hours</th><th>Notes</th></tr></thead>
    <tbody>
      ${entries.map((e) => `
        <tr>
          <td>${e.date}</td>
          <td class="yn">${e.hours}</td>
          <td class="notes-cell">${e.notes || ""}</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  const wrap = document.createElement("div");
  wrap.className = "overflow-x";
  wrap.appendChild(table);
  el.appendChild(wrap);
}
