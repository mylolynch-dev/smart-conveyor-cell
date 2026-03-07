/**
 * overview.js — Overview screen updater
 * Conveyor animation, state badge, LEDs, metric tiles
 */

let _beltOffset = 0;
let _boxX = -50;
let _boxY = 55;
let _boxVisible = false;
let _boxDiverting = false;
let _boxTargetGateX = 700;
let _boxSpeed = 400;          // px/s — fixed fast speed so each box crosses in ~1.5s
let _boxQueue = [];           // queued boxes waiting to animate: [{type, speed}]
let _prevBoxTotal = null;
let _lastGateType = null;
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

  // Track active gate type so spawnBox can read it even if sensors cleared
  if (t.OUT_GATE_B)      _lastGateType = 'metal';
  else if (t.OUT_GATE_C) _lastGateType = 'large';
  else if (t.OUT_GATE_A) _lastGateType = 'small';

  // ── Box animation trigger ──────────────────────────────────
  // Use total box count instead of IN_BOX_DETECT (which only lasts 200ms,
  // shorter than the 500ms WebSocket poll — so the rising edge was often missed).
  const boxTotal = t.IR_BOX_COUNT_TOTAL ?? 0;
  if (_prevBoxTotal !== null && boxTotal > _prevBoxTotal) {
    spawnBox(t);
  }
  _prevBoxTotal = boxTotal;
}

function animateGate(id, open) {
  const el = document.getElementById(id);
  if (!el) return;
  if (open) {
    // Swing gate 50° from vertical to show the deflector is extended
    const x = parseFloat(el.getAttribute("x1"));
    const y = parseFloat(el.getAttribute("y1"));
    el.setAttribute("transform", `rotate(-50, ${x}, ${y})`);
    el.setAttribute("stroke", "#3fb950");
    el.setAttribute("stroke-width", "4");
  } else {
    el.removeAttribute("transform");
    el.setAttribute("stroke", "#8b949e");
    el.setAttribute("stroke-width", "3");
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
      const box = document.getElementById("box-anim");
      if (!_boxDiverting) {
        _boxX += _boxSpeed * dt;
        box.setAttribute("x", _boxX);
        if (_boxX + 30 >= _boxTargetGateX) {
          _boxDiverting = true;
          _boxX = _boxTargetGateX - 15;
          box.setAttribute("x", _boxX);
        }
        if (_boxX > 700) {
          _boxVisible = false;
          box.setAttribute("opacity", 0);
          box.setAttribute("y", 55);
          _tryDequeue();
        }
      } else {
        _boxY += _boxSpeed * dt;
        box.setAttribute("y", _boxY);
        if (_boxY > 170) {
          _boxVisible = false;
          _boxDiverting = false;
          _boxY = 55;
          box.setAttribute("opacity", 0);
          box.setAttribute("y", 55);
          _tryDequeue();
        }
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
  // Determine box type from gate outputs (more persistent than raw sensor inputs)
  let type = 'unknown';
  if (t.OUT_GATE_B || t.IN_METAL_DETECT)    type = 'metal';
  else if (t.OUT_GATE_C || t.IN_SIZE_LARGE) type = 'large';
  else if (t.OUT_GATE_A || t.IN_SIZE_SMALL) type = 'small';
  else if (_lastGateType)                    type = _lastGateType;

  const entry = { type, beltSpeed: t.IR_SPEED_ACTUAL || 60 };

  if (_boxVisible) {
    // Queue it — drop if queue is already deep to avoid a backlog spiral
    if (_boxQueue.length < 8) _boxQueue.push(entry);
  } else {
    _launchBox(entry);
  }
}

function _tryDequeue() {
  if (_boxQueue.length > 0) {
    _launchBox(_boxQueue.shift());
  }
}

function _launchBox({ type, beltSpeed }) {
  const gateX = { metal: 475, large: 575, small: 375, unknown: 700 };
  const color  = { metal: "#d29922", large: "#58a6ff", small: "#3fb950", unknown: "#8b949e" };

  const box = document.getElementById("box-anim");
  _boxX = 100;
  _boxY = 55;
  _boxDiverting = false;
  _boxTargetGateX = gateX[type];
  _boxVisible = true;
  // Scale speed with belt: faster belt = faster boxes, min 300px/s, max 600px/s
  // At 300–600px/s the belt width (~600px) is crossed in 1–2 seconds
  _boxSpeed = Math.min(Math.max(beltSpeed / 100 * 600, 300), 600);

  const c = color[type];
  box.setAttribute("fill", c + "33");
  box.setAttribute("stroke", c);
  box.setAttribute("opacity", 1);
  box.setAttribute("x", _boxX);
  box.setAttribute("y", _boxY);
}
