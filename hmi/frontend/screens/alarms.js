/**
 * alarms.js — Alarms screen: active alarm list + history table
 */

function renderActiveAlarms(alarms) {
  const wrap = document.getElementById("active-alarms-wrap");
  if (!alarms || alarms.length === 0) {
    wrap.innerHTML = '<div class="empty-msg">No active alarms</div>';
    return;
  }
  wrap.innerHTML = buildAlarmTable(alarms, true);
}

function renderAlarmHistory(alarms) {
  const wrap = document.getElementById("alarm-history-wrap");
  if (!alarms || alarms.length === 0) {
    wrap.innerHTML = '<div class="empty-msg">No alarms recorded</div>';
    return;
  }
  wrap.innerHTML = buildAlarmTable(alarms, false);
}

function buildAlarmTable(alarms, showAck) {
  const priorityPill = {
    HIGH:   '<span class="pill pill-red">HIGH</span>',
    MEDIUM: '<span class="pill pill-amber">MEDIUM</span>',
    LOW:    '<span class="pill pill-grey">LOW</span>',
  };
  let html = `<table class="alarm-table">
    <thead><tr>
      <th>Time</th>
      <th>Code</th>
      <th>Description</th>
      <th>Priority</th>
      <th>Status</th>
      ${showAck ? '<th></th>' : ''}
    </tr></thead><tbody>`;

  for (const a of alarms) {
    const ts = new Date(a.timestamp).toLocaleTimeString();
    const acked = a.acknowledged;
    const rowClass = `priority-${a.priority}${acked ? " acked" : ""}`;
    const statusPill = acked
      ? '<span class="pill pill-green">ACK</span>'
      : '<span class="pill pill-red">ACTIVE</span>';
    const ackBtn = showAck && !acked
      ? `<button class="btn btn-ghost btn-sm" onclick="ackAlarm(${a.id})">ACK</button>`
      : "";
    html += `<tr class="${rowClass}">
      <td>${ts}</td>
      <td>${a.alarm_code}</td>
      <td>${a.description || ""}</td>
      <td>${priorityPill[a.priority] || a.priority}</td>
      <td>${statusPill}</td>
      ${showAck ? `<td>${ackBtn}</td>` : ""}
    </tr>`;
  }
  html += "</tbody></table>";
  return html;
}

async function ackAlarm(id) {
  try {
    await fetch(`${API}/alarms/ack`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({alarm_id: id})
    });
    await loadAlarms();
  } catch(e) {
    console.error("ACK failed:", e);
  }
}
