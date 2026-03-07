/**
 * network.js — Network Status screen
 */

function updateNetwork(t) {
  const connected = t.modbus_connected;

  const statusEl = document.getElementById("net-status");
  if (statusEl) {
    statusEl.innerHTML = connected
      ? '<span class="text-green">Connected</span>'
      : '<span class="text-red">Disconnected</span>';
  }

  const latEl = document.getElementById("net-latency");
  if (latEl) latEl.textContent = `${t.poll_latency_ms ?? "--"} ms`;

  const lastOkEl = document.getElementById("net-last-ok");
  if (lastOkEl && t.server_time) {
    lastOkEl.textContent = new Date(t.server_time).toLocaleTimeString();
  }
}
