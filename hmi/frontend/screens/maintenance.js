/**
 * maintenance.js — Maintenance screen
 * Raw sensor states, timer/counter values, watchdog heartbeat, last fault
 */

let _prevHB = false;

const SENSOR_LABELS = {
  IN_START_PB:        "Start PB",
  IN_STOP_PB:         "Stop PB",
  IN_ESTOP:           "E-Stop (NC)",
  IN_FAULT_RESET:     "Fault Reset",
  IN_MODE_SELECT:     "Mode Select",
  IN_MOTOR_FEEDBACK:  "Motor Feedback",
  IN_JAM_SENSOR:      "Jam Sensor",
  IN_BOX_DETECT:      "Box Detect",
  IN_SIZE_SMALL:      "Size — Small",
  IN_SIZE_LARGE:      "Size — Large",
  IN_METAL_DETECT:    "Metal Detect",
  IN_COLOR_RED:       "Color — Red",
  IN_COLOR_BLUE:      "Color — Blue",
  IN_GATE_A_CONFIRM:  "Gate A Confirm",
  IN_GATE_B_CONFIRM:  "Gate B Confirm",
};

function updateMaintenance(t) {
  // ── Sensor grid ────────────────────────────────────────────
  const grid = document.getElementById("sensor-grid");
  if (grid) {
    grid.innerHTML = Object.entries(SENSOR_LABELS).map(([tag, label]) => {
      const val = t[tag];
      const isOn = val === true || val === 1;
      const color = tag === "IN_ESTOP" ? (isOn ? "green" : "red") :
                    tag.startsWith("IN_") ? (isOn ? "green" : "off") : "off";
      return `
        <div class="sensor-item">
          <div class="led ${isOn ? "on-" + (tag==="IN_ESTOP"&&!isOn?"red":"green") : "off"}"></div>
          <div>
            <div class="sensor-name">${label}</div>
            <div class="sensor-val">${isOn ? "ON" : "OFF"}</div>
          </div>
        </div>`;
    }).join("");
  }

  // ── Timer / counter values ─────────────────────────────────
  const tv = document.getElementById("timer-values");
  if (tv) {
    const jamPreset = t.HR_JAM_TIMER_PRESET ?? 30;
    const jamAcc = t.IR_JAM_TIMER_ACC ?? 0;
    const jamPct = jamPreset > 0 ? Math.min(100, Math.round((jamAcc / jamPreset) * 100)) : 0;
    tv.innerHTML = `
      <div style="margin-bottom:12px">
        <div class="progress-bar-lbl">
          <span class="text-muted">Jam Timer (TON)</span>
          <span>${jamAcc} / ${jamPreset} ticks</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill ${jamPct > 70 ? "fill-red" : "fill-blue"}" style="width:${jamPct}%"></div>
        </div>
      </div>
      <table class="device-table" style="font-size:12px">
        <tr><td class="text-muted">Total Box Count</td><td>${t.IR_BOX_COUNT_TOTAL ?? 0}</td></tr>
        <tr><td class="text-muted">Small Box Count</td><td>${t.IR_BOX_COUNT_SMALL ?? 0}</td></tr>
        <tr><td class="text-muted">Large Box Count</td><td>${t.IR_BOX_COUNT_LARGE ?? 0}</td></tr>
        <tr><td class="text-muted">Metal Part Count</td><td>${t.IR_BOX_COUNT_METAL ?? 0}</td></tr>
        <tr><td class="text-muted">Alarm Word (bitmask)</td><td>${(t.IR_ALARM_WORD ?? 0).toString(2).padStart(8,"0")} b</td></tr>
        <tr><td class="text-muted">Speed Actual</td><td>${t.IR_SPEED_ACTUAL ?? 0} %</td></tr>
        <tr><td class="text-muted">Speed Setpoint</td><td>${t.HR_SPEED_SETPOINT ?? 0} %</td></tr>
      </table>`;
  }

  // ── Watchdog heartbeat ─────────────────────────────────────
  const hb = t.OUT_HEARTBEAT;
  const hbLed = document.getElementById("hb-led");
  const hbTxt = document.getElementById("hb-text");
  if (hb !== _prevHB) {
    if (hbLed) {
      hbLed.className = "led on-green";
      setTimeout(() => { if(hbLed) hbLed.className = "led off"; }, 200);
    }
    if (hbTxt) {
      hbTxt.textContent = "Heartbeat OK — PLC scan running";
      hbTxt.className = "text-green";
    }
    _prevHB = hb;
  }

  // ── Last fault ─────────────────────────────────────────────
  const lf = document.getElementById("last-fault-info");
  if (lf) {
    const lastFault = t.IR_LAST_FAULT_CODE ?? 0;
    const faultName = FAULT_NAMES[lastFault];
    if (lastFault === 0) {
      lf.textContent = "No faults recorded this session.";
      lf.className = "text-muted";
    } else {
      lf.innerHTML = `<span class="text-red">Fault ${lastFault}: ${faultName}</span>`;
    }
  }
}
