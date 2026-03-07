/**
 * manual.js — Manual Controls screen
 */

function updateManual(t) {
  const isManual = t.IR_MACHINE_STATE === 2;
  const motorOn = t.OUT_MOTOR_RUN;

  // Mode toggle reflects current state
  const tog = document.getElementById("mode-toggle");
  if (tog) tog.checked = (t.HR_MODE_COMMAND === 1 || isManual);

  // Speed slider sync (only update if user is not dragging)
  const slider = document.getElementById("speed-slider");
  const sliderVal = document.getElementById("speed-slider-val");
  if (slider && document.activeElement !== slider) {
    slider.value = t.HR_SPEED_SETPOINT ?? 60;
    if (sliderVal) sliderVal.textContent = `${t.HR_SPEED_SETPOINT ?? 60}%`;
  }

  // Jam timer slider
  const jamSlider = document.getElementById("jam-slider");
  if (jamSlider && document.activeElement !== jamSlider) {
    jamSlider.value = t.HR_JAM_TIMER_PRESET ?? 30;
    const jamVal = document.getElementById("jam-slider-val");
    if (jamVal) jamVal.textContent = t.HR_JAM_TIMER_PRESET ?? 30;
  }

  // Gate indicators
  setLed("man-gate-a", t.OUT_GATE_A, "green");
  setLed("man-gate-b", t.OUT_GATE_B, "amber");
  setLed("man-gate-c", t.OUT_GATE_C, "blue");
}

function updateSpeedLabel(val) {
  document.getElementById("speed-slider-val").textContent = `${val}%`;
}

function updateJamLabel(val) {
  document.getElementById("jam-slider-val").textContent = val;
}

function setSpeed(val) {
  writeTag("HR_SPEED_SETPOINT", parseInt(val));
}

function setJamPreset(val) {
  writeTag("HR_JAM_TIMER_PRESET", parseInt(val));
}

function setMode(val) {
  writeTag("HR_MODE_COMMAND", val);
}
