/**
 * AI-Powered Timetable Generator — Frontend JavaScript
 */

"use strict";

// ====================================================================
// State
// ====================================================================
const state = {
  classes:  [],
  subjects: [],
  teachers: [],
  rooms:    [],
  grid:     {},
  entries:  [],
};

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

// ====================================================================
// Tab management
// ====================================================================
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

// ====================================================================
// Row management for input tables
// ====================================================================

const tableConfig = {
  classes:  { fields: ["id","name","strength"],  defaults: ["", "", "30"] },
  subjects: { fields: ["id","name","sessions_per_week"], defaults: ["", "", "3"] },
  teachers: { fields: ["id","name","subjects"],   defaults: ["", "", ""] },
  rooms:    { fields: ["id","name","capacity"],   defaults: ["", "", "30"] },
};

function addRow(type, values) {
  const cfg = tableConfig[type];
  const tbody = document.querySelector(`#${type}-table tbody`);
  const tr = document.createElement("tr");
  tr.dataset.type = type;

  cfg.fields.forEach((field, i) => {
    const td = document.createElement("td");
    const input = document.createElement("input");
    input.type = (field === "strength" || field === "sessions_per_week" || field === "capacity") ? "number" : "text";
    input.placeholder = field.replace(/_/g, " ");
    input.value = values ? values[i] : cfg.defaults[i];
    input.dataset.field = field;
    if (input.type === "number") {
      input.min = "1";
    }
    td.appendChild(input);
    tr.appendChild(td);
  });

  const tdBtn = document.createElement("td");
  const btn = document.createElement("button");
  btn.className = "remove-btn";
  btn.textContent = "✕";
  btn.onclick = () => tr.remove();
  tdBtn.appendChild(btn);
  tr.appendChild(tdBtn);

  tbody.appendChild(tr);
}

function collectTable(type) {
  const cfg = tableConfig[type];
  const rows = document.querySelectorAll(`#${type}-table tbody tr`);
  return Array.from(rows).map(tr => {
    const obj = {};
    cfg.fields.forEach(field => {
      const input = tr.querySelector(`input[data-field="${field}"]`);
      let val = input ? input.value.trim() : "";
      if (field === "strength" || field === "capacity") val = parseInt(val, 10) || 30;
      if (field === "sessions_per_week") val = parseInt(val, 10) || 3;
      if (field === "subjects") val = val.split(",").map(s => s.trim()).filter(Boolean);
      obj[field] = val;
    });
    return obj;
  }).filter(obj => obj.id && obj.name);
}

// ====================================================================
// Load sample data
// ====================================================================
document.getElementById("load-sample-btn").addEventListener("click", async () => {
  const btn = document.getElementById("load-sample-btn");
  btn.disabled = true;
  btn.textContent = "Loading…";
  try {
    const res = await fetch("/api/sample");
    const data = await res.json();
    loadConfig(data);
  } catch {
    showStatus("Failed to load sample data.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Load Sample Data";
  }
});

function loadConfig(data) {
  ["classes", "subjects", "teachers", "rooms"].forEach(type => {
    document.querySelector(`#${type}-table tbody`).innerHTML = "";
  });

  (data.classes  || []).forEach(c => addRow("classes",  [c.id, c.name, c.strength]));
  (data.subjects || []).forEach(s => addRow("subjects", [s.id, s.name, s.sessions_per_week]));
  (data.teachers || []).forEach(t => addRow("teachers", [t.id, t.name, (t.subjects||[]).join(", ")]));
  (data.rooms    || []).forEach(r => addRow("rooms",    [r.id, r.name, r.capacity]));

  if (data.periods_per_day) {
    document.getElementById("periods-select").value = String(data.periods_per_day);
  }
}

// ====================================================================
// Generate
// ====================================================================
document.getElementById("generate-btn").addEventListener("click", async () => {
  const payload = {
    classes:        collectTable("classes"),
    subjects:       collectTable("subjects"),
    teachers:       collectTable("teachers"),
    rooms:          collectTable("rooms"),
    periods_per_day: parseInt(document.getElementById("periods-select").value, 10),
  };

  if (!payload.classes.length || !payload.subjects.length ||
      !payload.teachers.length || !payload.rooms.length) {
    showStatus("Please add at least one class, subject, teacher and room.", "error");
    return;
  }

  showStatus("⚡ Generating timetable using AI scheduler…", "loading");
  document.getElementById("generate-btn").disabled = true;

  try {
    const res = await fetch("/api/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      showStatus("Error: " + (data.error || "Unknown error"), "error");
      return;
    }

    state.grid    = data.grid;
    state.entries = data.entries;

    renderStats(data.stats, payload);
    renderClassSelector(Object.keys(data.grid));
    showStatus(
      `✅ Timetable generated successfully — ${data.stats.total_entries} sessions scheduled.`,
      "success"
    );
    document.getElementById("result-panel").classList.remove("hidden");

  } catch (err) {
    showStatus("Network error: " + err.message, "error");
  } finally {
    document.getElementById("generate-btn").disabled = false;
  }
});

// ====================================================================
// Render helpers
// ====================================================================

function renderStats(stats, payload) {
  const totalRequired = payload.classes.length *
    payload.subjects.reduce((s, sub) => s + (sub.sessions_per_week || 3), 0);
  const pct = totalRequired ? Math.round(stats.total_entries / totalRequired * 100) : 0;

  document.getElementById("stats-bar").innerHTML = `
    <div class="stat-item"><span class="stat-value">${stats.total_entries}</span><span class="stat-label">Sessions Scheduled</span></div>
    <div class="stat-item"><span class="stat-value">${pct}%</span><span class="stat-label">Coverage</span></div>
    <div class="stat-item"><span class="stat-value">${stats.classes}</span><span class="stat-label">Classes</span></div>
    <div class="stat-item"><span class="stat-value">${stats.subjects}</span><span class="stat-label">Subjects</span></div>
    <div class="stat-item"><span class="stat-value">${stats.teachers}</span><span class="stat-label">Teachers</span></div>
    <div class="stat-item"><span class="stat-value">${stats.rooms}</span><span class="stat-label">Rooms</span></div>
  `;
}

function renderClassSelector(classNames) {
  const sel = document.getElementById("class-select");
  sel.innerHTML = classNames.map(cn => `<option value="${cn}">${cn}</option>`).join("");
  sel.onchange = () => renderGrid(sel.value);
  renderGrid(classNames[0]);
}

function renderGrid(className) {
  const classGrid = state.grid[className] || {};

  // Determine periods used
  const periodsSet = new Set();
  DAYS.forEach(day => {
    Object.keys(classGrid[day] || {}).forEach(p => periodsSet.add(Number(p)));
  });
  // Collect all entries for this class to get period times
  const periodEntries = state.entries.filter(e => e.class === className);
  const periodTimeMap = {};
  periodEntries.forEach(e => { periodTimeMap[e.period] = `${e.start_time}–${e.end_time}`; });

  const periods = [...periodsSet].sort((a, b) => a - b);
  if (!periods.length) {
    // No data yet; show a placeholder
    const maxPeriods = parseInt(document.getElementById("periods-select").value, 10);
    for (let p = 1; p <= maxPeriods; p++) periods.push(p);
  }

  // Build subject colour map
  const subjectColours = {};
  let colIdx = 0;
  DAYS.forEach(day => {
    Object.values(classGrid[day] || {}).forEach(cell => {
      if (!subjectColours[cell.subject]) subjectColours[cell.subject] = colIdx++ % 8;
    });
  });

  // Header
  const thead = document.querySelector("#timetable-grid thead");
  thead.innerHTML = `<tr>
    <th>Period</th>
    ${DAYS.map(d => `<th>${d}</th>`).join("")}
  </tr>`;

  // Body
  const tbody = document.querySelector("#timetable-grid tbody");
  tbody.innerHTML = "";

  periods.forEach(period => {
    const tr = document.createElement("tr");
    const timeLabel = periodTimeMap[period] || `Period ${period}`;
    tr.innerHTML = `<td>${timeLabel}</td>`;

    DAYS.forEach(day => {
      const td = document.createElement("td");
      const cell = (classGrid[day] || {})[period];
      if (cell) {
        const colClass = `cell-colour-${subjectColours[cell.subject] || 0}`;
        td.innerHTML = `<div class="cell ${colClass}">
          <div class="cell-subject">${escHtml(cell.subject)}</div>
          <div class="cell-teacher">👤 ${escHtml(cell.teacher)}</div>
          <div class="cell-room">🏫 ${escHtml(cell.room)}</div>
        </div>`;
      } else {
        td.innerHTML = `<div class="empty-cell">—</div>`;
      }
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });
}

// ====================================================================
// Status bar
// ====================================================================
function showStatus(msg, type) {
  const bar = document.getElementById("status-bar");
  bar.textContent = msg;
  bar.className = `status-bar ${type}`;
  bar.classList.remove("hidden");
  if (type === "success") {
    setTimeout(() => { if (bar.classList.contains("success")) bar.classList.add("hidden"); }, 6000);
  }
}

// ====================================================================
// Utils
// ====================================================================
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ====================================================================
// Initialise with one empty row in each table
// ====================================================================
(function init() {
  addRow("classes");
  addRow("subjects");
  addRow("teachers");
  addRow("rooms");
})();
