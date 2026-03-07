/**
 * app.js — Main HMI controller
 * Manages: WebSocket connection, tab routing, tag state, shared API calls
 */

const API = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

// ── Shared live state ─────────────────────────────────────────────────────
window.tags = {};
window.wsConnected = false;

// State name map
const STATE_NAMES = {0:"IDLE", 1:"AUTO_RUN", 2:"MANUAL", 3:"FAULT", 4:"ESTOP"};
const FAULT_NAMES = {
  0:"No fault",
  1:"Conveyor jam",
  2:"Motor feedback lost",
  3:"Watchdog / comms loss",
  4:"Sensor mismatch"
};

// ── Tab routing ───────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("screen-" + tab).classList.add("active");
    if (tab === "alarms") loadAlarms();
  });
});

// ── WebSocket ─────────────────────────────────────────────────────────────
let ws = null;
let reconnectTimer = null;

function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    window.wsConnected = true;
    setModbusStatus(null); // will be updated when first tag arrives
    console.log("[WS] Connected");
    clearTimeout(reconnectTimer);
  };

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      window.tags = data;
      updateAll(data);
    } catch(e) {
      console.warn("[WS] Parse error", e);
    }
  };

  ws.onerror = () => {
    window.wsConnected = false;
    setModbusStatus(false);
  };

  ws.onclose = () => {
    window.wsConnected = false;
    setModbusStatus(false);
    reconnectTimer = setTimeout(connectWS, 3000);
  };
}

// Send a keepalive ping so the server doesn't close the WS
setInterval(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send("ping");
  }
}, 10000);

// ── Master update dispatcher ──────────────────────────────────────────────
function updateAll(t) {
  updateTopbar(t);
  updateFaultBanner(t);
  updateAlarmBadge(t);

  const activeScreen = document.querySelector(".tab-btn.active")?.dataset.tab;
  if (activeScreen === "overview")    updateOverview(t);
  if (activeScreen === "manual")      updateManual(t);
  if (activeScreen === "production")  updateProduction(t);
  if (activeScreen === "maintenance") updateMaintenance(t);
  if (activeScreen === "network")     updateNetwork(t);
}

// ── Topbar ────────────────────────────────────────────────────────────────
function updateTopbar(t) {
  const ts = t.server_time ? new Date(t.server_time).toLocaleTimeString() : "--:--:--";
  document.getElementById("server-time").textContent = ts;
  setModbusStatus(t.modbus_connected);
}

function setModbusStatus(connected) {
  const dot = document.getElementById("modbus-dot");
  const txt = document.getElementById("modbus-txt");
  if (connected === null) {
    dot.className = "status-dot amber";
    txt.textContent = "Connecting…";
  } else if (connected) {
    dot.className = "status-dot green";
    txt.textContent = "PLC Connected";
  } else {
    dot.className = "status-dot red";
    txt.textContent = "PLC Disconnected";
  }
}

// ── Fault banner ──────────────────────────────────────────────────────────
function updateFaultBanner(t) {
  const banner = document.getElementById("fault-banner");
  const faultCode = t.HR_FAULT_CODE || 0;
  const state = t.IR_MACHINE_STATE;
  if (state === 3 || state === 4 || faultCode !== 0) {
    banner.style.display = "block";
    const stateName = STATE_NAMES[state] || "FAULT";
    const faultName = FAULT_NAMES[faultCode] || `Fault ${faultCode}`;
    document.getElementById("fault-text").textContent =
      `${stateName} — ${faultName}. Acknowledge and press RESET to clear.`;
  } else {
    banner.style.display = "none";
  }
}

// ── Alarm badge on Alarms tab ─────────────────────────────────────────────
let _activeAlarmCount = 0;
function updateAlarmBadge(t) {
  const word = t.IR_ALARM_WORD || 0;
  let count = 0;
  for (let i = 0; i < 8; i++) if (word & (1 << i)) count++;
  const badge = document.getElementById("alarm-badge");
  if (count > 0) {
    badge.style.display = "inline";
    badge.textContent = count;
  } else {
    badge.style.display = "none";
  }
}

// ── LED helper ────────────────────────────────────────────────────────────
function setLed(id, on, color="green") {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = on ? `led on-${color}` : "led off";
}

// ── Format seconds to mm:ss ───────────────────────────────────────────────
function fmtTime(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2,"0")}`;
}

// ── API helpers ───────────────────────────────────────────────────────────
async function sendCommand(cmd) {
  try {
    await fetch(`${API}/command`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({command: cmd})
    });
  } catch(e) {
    console.error("Command failed:", e);
  }
}

async function writeTag(tag, value) {
  try {
    await fetch(`${API}/write`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({tag, value})
    });
  } catch(e) {
    console.error("Write failed:", e);
  }
}

async function loadAlarms() {
  try {
    const [active, history] = await Promise.all([
      fetch(`${API}/alarms`).then(r => r.json()),
      fetch(`${API}/alarms/history`).then(r => r.json()),
    ]);
    renderActiveAlarms(active);
    renderAlarmHistory(history);
  } catch(e) {
    console.error("Alarm load failed:", e);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────
connectWS();
