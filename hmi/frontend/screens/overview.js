/**
 * overview.js — Overview screen updater
 * Conveyor animation, state badge, LEDs, metric tiles
 */

let _beltOffset = 0;
let _boxX = -50;
let _boxVisible = false;
let _prevBoxDetect = false;
let _animFrame = null;

function updateOverview(t) {
  // ── State badge ────────────────────────────────────────────
  const stateNum = t.IR_MACHINE_STATE ?? 0;
  const stateName = STATE_NAMES[stateNum] || "IDLE";
  const badge = document.getElementById("state-badge");
  badge.textContent = stateName;
  badge.className = "state-badge " + stateName;

  // Mode pill
  const modeBadge = document.getElementById("mode-badge");
  modeBadge.textContent = stateNum === 2 ? "MANUAL" : "AUTO";
  modeBadge.className = stateNum === 2 ? "pill pill-amber" : "pill pill-grey";

  // ── LEDs ───────────────────────────────────────────────────
  setLed("led-motor", t.OUT_MOTOR_RUN, "green");
  setLed("led-estop", t.OUT_ESTOP_LIGHT, "red");
  setLed("led-fault", t.OUT_FAULT_LIGHT, "red");
  setLed("led-horn",  t.OUT_ALARM_HORN, "amber");

  // ── Gate animations ────────────────────────────────────────
  animateGate("gate-a", t.OUT_GATE_A);
  animateGate("gate-b", t.OUT_GATE_B);
  animateGate("gate-c", t.OUT_GATE_C);

  // ── Speed label ────────────────────────────────────────────
  document.getElementById("speed-label").textContent =
    `Speed: ${t.IR_SPEED_ACTUAL ?? 0}%  (set: ${t.HR_SPEED_SETPOINT ?? 0}%)`;

  // ── Metric tiles ───────────────────────────────────────────
  document.getElementById("ov-total").textContent  = t.IR_BOX_COUNT_TOTAL ?? 0;
  document.getElementById("ov-tph").textContent    = t.IR_THROUGHPUT_PER_HR ?? 0;
  document.getElementById("ov-speed").innerHTML   =
    `${t.IR_SPEED_ACTUAL ?? 0}<span style="font-size:16px">%</span>`;
  document.getElementById("ov-setpt").textContent  = t.HR_SPEED_SETPOINT ?? 0;
  document.getElementById("ov-runtime").textContent = fmtTime(t.IR_RUNTIME_SECS ?? 0);
  document.getElementById("ov-down").textContent   = fmtTime(t.IR_DOWNTIME_SECS ?? 0);

  // ── Belt animation ─────────────────────────────────────────
  const motorOn = t.OUT_MOTOR_RUN;
  if (motorOn) {
    if (!_animFrame) startBeltAnimation(t.IR_SPEED_ACTUAL || 60);
  } else {
    stopBeltAnimation();
  }

  // ── Box animation trigger ──────────────────────────────────
  const boxDetect = t.IN_BOX_DETECT;
  if (boxDetect && !_prevBoxDetect) {
    spawnBox(t);
  }
  _prevBoxDetect = boxDetect;
}

function animateGate(id, open) {
  const el = document.getElementById(id);
  if (!el) return;
  if (open) {
    // Rotate gate 45° to show diversion
    el.setAttribute("transform", `rotate(45, ${el.getAttribute("x1")}, ${el.getAttribute("y1")})`);
    el.setAttribute("stroke", "#3fb950");
  } else {
    el.removeAttribute("transform");
    el.setAttribute("stroke", "#8b949e");
  }
}

function startBeltAnimation(speed) {
  let lastTime = null;
  function frame(ts) {
    if (!lastTime) lastTime = ts;
    const dt = (ts - lastTime) / 1000;
    lastTime = ts;
    const pxPerSec = (speed / 100) * 200; // max 200 px/s
    _beltOffset = (_beltOffset + pxPerSec * dt) % 80;

    // Move belt lines to simulate motion
    const lines = document.querySelectorAll("#belt-lines line");
    lines.forEach((line, i) => {
      const baseX = 80 + i * 80;
      const x = ((baseX - _beltOffset) % 640) + 30;
      line.setAttribute("x1", x);
      line.setAttribute("x2", x);
    });

    // Move box if visible
    if (_boxVisible) {
      _boxX += pxPerSec * dt;
      const box = document.getElementById("box-anim");
      box.setAttribute("x", _boxX);
      if (_boxX > 700) {
        _boxVisible = false;
        box.setAttribute("opacity", 0);
      }
    }

    _animFrame = requestAnimationFrame(frame);
  }
  _animFrame = requestAnimationFrame(frame);
}

function stopBeltAnimation() {
  if (_animFrame) {
    cancelAnimationFrame(_animFrame);
    _animFrame = null;
  }
}

function spawnBox(t) {
  const box = document.getElementById("box-anim");
  _boxX = 100;
  _boxVisible = true;
  // Color by type
  const color = t.IN_METAL_DETECT ? "#d29922"
              : t.IN_SIZE_LARGE   ? "#58a6ff"
              : t.IN_SIZE_SMALL   ? "#3fb950"
              : "#8b949e";
  box.setAttribute("fill", color + "33");
  box.setAttribute("stroke", color);
  box.setAttribute("opacity", 1);
  box.setAttribute("x", _boxX);
}
