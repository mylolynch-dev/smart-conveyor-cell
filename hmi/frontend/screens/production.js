/**
 * production.js — Production Stats screen
 * Box counts, throughput, OEE-lite, runtime bars, speed trend sparkline
 */

const MAX_TREND_POINTS = 60;
const _trendData = { labels: [], actual: [], setpoint: [] };

function updateProduction(t) {
  // ── Count tiles ────────────────────────────────────────────
  document.getElementById("prod-total").textContent = t.IR_BOX_COUNT_TOTAL ?? 0;
  document.getElementById("prod-small").textContent = t.IR_BOX_COUNT_SMALL ?? 0;
  document.getElementById("prod-large").textContent = t.IR_BOX_COUNT_LARGE ?? 0;
  document.getElementById("prod-metal").textContent = t.IR_BOX_COUNT_METAL ?? 0;
  document.getElementById("prod-tph").textContent   = t.IR_THROUGHPUT_PER_HR ?? 0;

  // ── OEE-lite ───────────────────────────────────────────────
  const runtime = t.IR_RUNTIME_SECS ?? 0;
  const downtime = t.IR_DOWNTIME_SECS ?? 0;
  const total = runtime + downtime;
  const oee = total > 0 ? Math.round((runtime / total) * 100) : 0;
  document.getElementById("oee-pct").textContent = `${oee}%`;
  document.getElementById("oee-bar").style.width = `${oee}%`;
  document.getElementById("oee-bar").className =
    `progress-bar-fill ${oee >= 85 ? "fill-green" : oee >= 60 ? "fill-blue" : "fill-red"}`;

  // ── Runtime / downtime bars ────────────────────────────────
  document.getElementById("runtime-lbl").textContent  = fmtTime(runtime);
  document.getElementById("downtime-lbl").textContent = fmtTime(downtime);
  if (total > 0) {
    document.getElementById("runtime-bar").style.width  = `${(runtime / total) * 100}%`;
    document.getElementById("downtime-bar").style.width = `${(downtime / total) * 100}%`;
  }

  // ── Trend sparkline ────────────────────────────────────────
  const now = new Date().toLocaleTimeString();
  _trendData.labels.push(now);
  _trendData.actual.push(t.IR_SPEED_ACTUAL ?? 0);
  _trendData.setpoint.push(t.HR_SPEED_SETPOINT ?? 0);

  if (_trendData.labels.length > MAX_TREND_POINTS) {
    _trendData.labels.shift();
    _trendData.actual.shift();
    _trendData.setpoint.shift();
  }

  drawTrend();
}

function drawTrend() {
  const canvas = document.getElementById("trend-canvas");
  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth;
  const H = canvas.clientHeight || 100;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, W, H);

  const data = _trendData.actual;
  const sp   = _trendData.setpoint;
  if (data.length < 2) return;

  const pad = { top: 8, bottom: 18, left: 28, right: 8 };
  const gW = W - pad.left - pad.right;
  const gH = H - pad.top - pad.bottom;

  // Grid lines
  ctx.strokeStyle = "#30363d";
  ctx.lineWidth = 0.5;
  for (let y = 0; y <= 4; y++) {
    const yy = pad.top + (gH * y) / 4;
    ctx.beginPath(); ctx.moveTo(pad.left, yy); ctx.lineTo(W - pad.right, yy); ctx.stroke();
    ctx.fillStyle = "#484f58";
    ctx.font = "9px monospace";
    ctx.fillText(100 - y * 25, 2, yy + 3);
  }

  function plotLine(arr, color) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    arr.forEach((v, i) => {
      const x = pad.left + (i / (arr.length - 1)) * gW;
      const y = pad.top + gH - (v / 100) * gH;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  // Setpoint (dashed)
  ctx.setLineDash([4, 4]);
  plotLine(sp, "#484f58");
  ctx.setLineDash([]);

  // Actual speed
  plotLine(data, "#58a6ff");

  // Legend
  ctx.font = "9px sans-serif";
  ctx.fillStyle = "#58a6ff"; ctx.fillRect(pad.left, H - 14, 12, 2);
  ctx.fillStyle = "#8b949e"; ctx.fillText("Actual", pad.left + 16, H - 10);
  ctx.fillStyle = "#484f58"; ctx.fillRect(pad.left + 60, H - 14, 12, 2);
  ctx.fillStyle = "#8b949e"; ctx.fillText("Setpoint", pad.left + 76, H - 10);
}
