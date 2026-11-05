// DOM Elements
const chatHistory = document.getElementById('chatHistory');
const commandForm = document.getElementById('commandForm');
const commandInput = document.getElementById('commandInput');
const executeBtn = document.getElementById('executeBtn');
const stopBtn = document.getElementById('stopBtn');
const clearBtn = document.getElementById('clearBtn');

const backendText = document.getElementById('backendText');
const geminiBadge = document.getElementById('geminiBadge');
const geminiText = document.getElementById('geminiText');
const deviceBadge = document.getElementById('deviceBadge');
const deviceText = document.getElementById('deviceText');

// Device Details Elements
const devModel = document.getElementById('devModel');
const devSerial = document.getElementById('devSerial');
const devType = document.getElementById('devType');
const devStatus = document.getElementById('devStatus');
const devApp = document.getElementById('devApp');
const screenImg = document.getElementById('screenImg');
const refreshDeviceBtn = document.getElementById('refreshDeviceBtn');
const refreshScreenBtn = document.getElementById('refreshScreenBtn');
const historyList = document.getElementById('historyList');

// Wireless Tabs & Controls
const tabQR = document.getElementById('tabQR');
const tabCode = document.getElementById('tabCode');
const tabConnect = document.getElementById('tabConnect');
const viewQR = document.getElementById('viewQR');
const viewCode = document.getElementById('viewCode');
const viewConnect = document.getElementById('viewConnect');

const qrPhoneIp = document.getElementById('qrPhoneIp');
const qrScannerBox = document.getElementById('qrScannerBox');
const startCameraBtn = document.getElementById('startCameraBtn');
const stopCameraBtn = document.getElementById('stopCameraBtn');

const codePhoneIp = document.getElementById('codePhoneIp');
const pairPort = document.getElementById('pairPort');
const pairCode = document.getElementById('pairCode');
const pairCodeBtn = document.getElementById('pairCodeBtn');

const connectIp = document.getElementById('connectIp');
const connectPort = document.getElementById('connectPort');
const connectBtn = document.getElementById('connectBtn');
const disconnectBtn = document.getElementById('disconnectBtn');
const wirelessStatusMsg = document.getElementById('wirelessStatusMsg');

const deviceSelectContainer = document.getElementById('deviceSelectContainer');
const deviceSelector = document.getElementById('deviceSelector');

// Modal Elements
const confirmModal = document.getElementById('confirmModal');
const confirmPromptText = document.getElementById('confirmPromptText');
const confirmApproveBtn = document.getElementById('confirmApproveBtn');
const confirmRejectBtn = document.getElementById('confirmRejectBtn');
let pendingTaskId = null;

let html5QrScanner = null;

// Helper: Show Wireless Feedback
function showWirelessMsg(msg, isError = false) {
  wirelessStatusMsg.innerText = msg;
  wirelessStatusMsg.style.color = isError ? '#f85149' : '#3fb950';
}

// Tab Switching
function switchTab(selected) {
  const tQR = document.getElementById('tabQR');
  const tCode = document.getElementById('tabCode');
  const tConnect = document.getElementById('tabConnect');
  const vQR = document.getElementById('viewQR');
  const vCode = document.getElementById('viewCode');
  const vConnect = document.getElementById('viewConnect');

  if (tQR) tQR.classList.remove('active');
  if (tCode) tCode.classList.remove('active');
  if (tConnect) tConnect.classList.remove('active');

  if (vQR) vQR.style.setProperty('display', 'none', 'important');
  if (vCode) vCode.style.setProperty('display', 'none', 'important');
  if (vConnect) vConnect.style.setProperty('display', 'none', 'important');

  if (selected === 'qr') {
    if (tQR) tQR.classList.add('active');
    if (vQR) vQR.style.setProperty('display', 'block', 'important');
  } else if (selected === 'code') {
    if (tCode) tCode.classList.add('active');
    if (vCode) vCode.style.setProperty('display', 'block', 'important');
    try { stopScanner(); } catch (e) {}
  } else if (selected === 'connect') {
    if (tConnect) tConnect.classList.add('active');
    if (vConnect) vConnect.style.setProperty('display', 'block', 'important');
    try { stopScanner(); } catch (e) {}
  }
}
window.switchTab = switchTab;

tabQR.addEventListener('click', (e) => { e.preventDefault(); switchTab('qr'); });
tabCode.addEventListener('click', (e) => { e.preventDefault(); switchTab('code'); });
tabConnect.addEventListener('click', (e) => { e.preventDefault(); switchTab('connect'); });

// Chat Display
function appendMessage(text, sender = 'user', steps = null) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  
  let content = `<div>${text}</div>`;
  if (steps && steps.length > 0) {
    content += `<div class="action-step-card"><div style="font-weight: 600; margin-bottom: 6px;">Execution Steps & Results:</div>`;
    steps.forEach((s, idx) => {
      const statusClass = (s.status || 'success').toLowerCase();
      const actionName = s.action || s.type || 'ACTION';
      const detailInfo = s.step_description || (s.package ? `Package: ${s.package}` : (s.matched_text ? `Target: "${s.matched_text}"` : (s.matched_desc ? `Desc: "${s.matched_desc}"` : (s.typed_text ? `Typed: "${s.typed_text}"` : ''))));
      const verifyInfo = s.verification && s.verification.details ? s.verification.details : '';
      
      content += `
        <div class="step-item">
          <div>
            <span class="step-badge ${statusClass}">${s.status || 'done'}</span>
            <strong>#${idx + 1} ${actionName}</strong>
            ${detailInfo ? `<div class="step-details">${detailInfo}</div>` : ''}
            ${verifyInfo ? `<div class="step-details" style="color: #58a6ff;">🔍 ${verifyInfo}</div>` : ''}
            ${s.message ? `<div class="step-details" style="color: #f85149;">⚠️ ${s.message}</div>` : ''}
          </div>
        </div>
      `;
    });
    content += `</div>`;
  }
  
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  content += `<div class="message-time">${time}</div>`;
  msgDiv.innerHTML = content;
  
  chatHistory.appendChild(msgDiv);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Health & Status
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.status === 'healthy') {
      backendText.innerText = 'Backend: Online';
      if (data.gemini_configured) {
        geminiBadge.querySelector('.dot').className = 'dot connected';
        geminiText.innerText = 'Gemini: Configured';
      } else {
        geminiBadge.querySelector('.dot').className = 'dot warning';
        geminiText.innerText = 'Gemini: Fallback Mode';
      }
    }
  } catch (err) {
    backendText.innerText = 'Backend: Offline';
  }
}

async function checkDeviceStatus() {
  try {
    const res = await fetch('/api/device/status');
    const data = await res.json();
    const dot = deviceBadge.querySelector('.dot');
    
    if (data.connected) {
      dot.className = 'dot connected';
      deviceText.innerText = `${data.model || 'Device'} (${data.connection_type || 'ADB'})`;
      devModel.innerText = data.model || 'Unknown';
      devSerial.innerText = data.serial || '--';
      devType.innerText = data.connection_type || 'Unknown';
      devStatus.innerText = 'Connected';
      devStatus.style.color = '#3fb950';
      devApp.innerText = data.current_app || 'Home / Unknown';

      // Auto populate connect inputs if ip detected
      if (data.serial && data.serial.includes(':')) {
        const parts = data.serial.split(':');
        if (!connectIp.value) connectIp.value = parts[0];
        if (!connectPort.value) connectPort.value = parts[1];
      }
    } else {
      dot.className = 'dot error';
      deviceText.innerText = 'Device: Disconnected';
      devModel.innerText = '--';
      devSerial.innerText = data.serial || '--';
      devType.innerText = data.connection_type || '--';
      devStatus.innerText = data.status || 'No device';
      devStatus.style.color = '#f85149';
      devApp.innerText = '--';
    }

    if (data.available_devices && data.available_devices.length > 1) {
      deviceSelectContainer.style.display = 'block';
      deviceSelector.innerHTML = '';
      data.available_devices.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.serial;
        opt.innerText = `${d.serial} [${d.state}] (${d.type})`;
        if (d.serial === data.serial) opt.selected = true;
        deviceSelector.appendChild(opt);
      });
    } else {
      deviceSelectContainer.style.display = 'none';
    }
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

deviceSelector.addEventListener('change', async (e) => {
  const chosen = e.target.value;
  try {
    const res = await fetch('/api/device/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ serial: chosen })
    });
    const result = await res.json();
    showWirelessMsg(result.message, !result.success);
    checkDeviceStatus();
    refreshScreenshot();
  } catch (err) {
    showWirelessMsg(`Selection failed: ${err.message}`, true);
  }
});

function refreshScreenshot() {
  screenImg.src = `/api/device/screenshot?t=${Date.now()}`;
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    if (!data || data.length === 0) {
      historyList.innerHTML = '<div style="color: #8b949e;">No previous tasks yet.</div>';
      return;
    }
    historyList.innerHTML = '';
    data.slice(0, 8).forEach(item => {
      const itemEl = document.createElement('div');
      itemEl.style.padding = '6px';
      itemEl.style.background = '#21262d';
      itemEl.style.borderRadius = '4px';
      itemEl.innerHTML = `
        <div style="font-weight: 500; color: ${item.success ? '#3fb950' : '#f85149'};">
          ${item.success ? '✓' : '✗'} ${item.instruction}
        </div>
        <div style="font-size: 0.7rem; color: #8b949e;">${new Date(item.created_at).toLocaleTimeString()}</div>
      `;
      historyList.appendChild(itemEl);
    });
  } catch (err) {
    console.error('Error fetching history:', err);
  }
}

// ----------------- QR Code Scanner Implementation ----------------- //
function stopScanner() {
  if (html5QrScanner) {
    html5QrScanner.stop().then(() => {
      html5QrScanner.clear();
      html5QrScanner = null;
      qrScannerBox.style.display = 'none';
      startCameraBtn.style.display = 'block';
      stopCameraBtn.style.display = 'none';
    }).catch(err => {
      console.warn('Error stopping scanner:', err);
      qrScannerBox.style.display = 'none';
      startCameraBtn.style.display = 'block';
      stopCameraBtn.style.display = 'none';
    });
  } else {
    qrScannerBox.style.display = 'none';
    startCameraBtn.style.display = 'block';
    stopCameraBtn.style.display = 'none';
  }
}

async function onScanSuccess(decodedText) {
  console.log('QR Code detected:', decodedText);
  stopScanner();
  showWirelessMsg('QR code scanned! Processing pairing...', false);

  const fallbackIp = qrPhoneIp.value.trim() || undefined;

  try {
    const res = await fetch('/api/device/pair-qr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qr_payload: decodedText, phone_ip: fallbackIp })
    });
    const result = await res.json();
    showWirelessMsg(result.message, !result.success);
    appendMessage(`QR Pairing: ${result.message}`, 'assistant');

    if (result.success) {
      if (result.ip) {
        connectIp.value = result.ip;
        codePhoneIp.value = result.ip;
        qrPhoneIp.value = result.ip;
      }
      switchTab('connect');
      showWirelessMsg('Paired successfully! Now enter the Connect Port and click Connect.', false);
    }
  } catch (err) {
    showWirelessMsg(`QR Pair error: ${err.message}`, true);
  }
}

startCameraBtn.addEventListener('click', () => {
  qrScannerBox.style.display = 'block';
  startCameraBtn.style.display = 'none';
  stopCameraBtn.style.display = 'block';
  showWirelessMsg('Camera active. Align phone QR code in frame...', false);

  html5QrScanner = new Html5Qrcode('qrReader');
  const config = { fps: 10, qrbox: { width: 220, height: 220 } };

  html5QrScanner.start(
    { facingMode: 'user' },
    config,
    onScanSuccess,
    (errorMessage) => {
      // ignore frame scan frame miss
    }
  ).catch(err => {
    showWirelessMsg(`Camera access failed: ${err}`, true);
    stopScanner();
  });
});

stopCameraBtn.addEventListener('click', () => {
  stopScanner();
  showWirelessMsg('Camera stopped.');
});

// ----------------- Manual Code Pairing ----------------- //
pairCodeBtn.addEventListener('click', async () => {
  const ip = codePhoneIp.value.trim();
  const portStr = pairPort.value.trim();
  const port = parseInt(portStr, 10);
  const code = pairCode.value.trim();

  if (!ip || !portStr || isNaN(port) || !code) {
    showWirelessMsg('Please enter IP, Pairing Port, and Pairing Code', true);
    alert('Please fill in: Phone IP, Pairing Port (number), and 6-Digit Pairing Code.');
    return;
  }

  showWirelessMsg(`Pairing with ${ip}:${port}...`);
  pairCodeBtn.disabled = true;

  try {
    const res = await fetch('/api/device/pair', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip, port, code })
    });
    const result = await res.json();
    showWirelessMsg(result.message, !result.success);
    appendMessage(`Code Pairing: ${result.message}`, 'assistant');

    if (result.success) {
      connectIp.value = ip;
      switchTab('connect');
    }
  } catch (err) {
    showWirelessMsg(`Pair request error: ${err.message}`, true);
    appendMessage(`Pairing Error: ${err.message}`, 'assistant');
  } finally {
    pairCodeBtn.disabled = false;
  }
});

// ----------------- Connect & Disconnect ----------------- //
connectBtn.addEventListener('click', async () => {
  const ip = connectIp.value.trim();
  const portStr = connectPort.value.trim();
  const port = parseInt(portStr, 10);

  if (!ip || !portStr || isNaN(port)) {
    showWirelessMsg('Please enter IP and Connect Port', true);
    alert('Please fill in: Phone IP and Connect Port (number).');
    return;
  }

  showWirelessMsg(`Connecting to ${ip}:${port} via ADB...`);
  connectBtn.disabled = true;

  try {
    const res = await fetch('/api/device/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip, port })
    });
    const result = await res.json();
    showWirelessMsg(result.message, !result.success);
    appendMessage(`Wireless ADB: ${result.message}`, 'assistant');
    checkDeviceStatus();
    refreshScreenshot();
  } catch (err) {
    showWirelessMsg(`Connect error: ${err.message}`, true);
    appendMessage(`Connect Error: ${err.message}`, 'assistant');
  } finally {
    connectBtn.disabled = false;
  }
});

disconnectBtn.addEventListener('click', async () => {
  showWirelessMsg('Disconnecting...');
  try {
    const res = await fetch('/api/device/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const result = await res.json();
    showWirelessMsg(result.message, !result.success);
    appendMessage(`Disconnected: ${result.message}`, 'assistant');
    checkDeviceStatus();
    refreshScreenshot();
  } catch (err) {
    showWirelessMsg(`Disconnect error: ${err.message}`, true);
  }
});

// ----------------- Chat Execution ----------------- //
let progressPollTimer = null;

function startProgressPolling() {
  if (progressPollTimer) clearInterval(progressPollTimer);
  progressPollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/task/progress');
      const data = await res.json();
      if (data && data.status === 'running' && data.current_action) {
        // Find existing live progress message or update status badge
        let liveEl = document.getElementById('liveTaskProgress');
        if (!liveEl) {
          liveEl = document.createElement('div');
          liveEl.id = 'liveTaskProgress';
          liveEl.className = 'message assistant';
          liveEl.style.borderLeft = '3px solid #e3b341';
          chatHistory.appendChild(liveEl);
        }
        liveEl.innerHTML = `
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="dot" style="background-color:#e3b341; animation: pulse 1.5s infinite;"></span>
            <strong>Running:</strong> Step ${data.current_step_index}/${data.total_steps}
          </div>
          <div style="font-size:0.8rem; color:#8b949e; margin-top:4px;">${data.current_action}</div>
        `;
        chatHistory.scrollTop = chatHistory.scrollHeight;
      } else {
        const liveEl = document.getElementById('liveTaskProgress');
        if (liveEl) liveEl.remove();
        if (data.status !== 'running') {
          clearInterval(progressPollTimer);
          progressPollTimer = null;
        }
      }
    } catch (e) {
      // ignore
    }
  }, 1000);
}

function stopProgressPolling() {
  if (progressPollTimer) {
    clearInterval(progressPollTimer);
    progressPollTimer = null;
  }
  const liveEl = document.getElementById('liveTaskProgress');
  if (liveEl) liveEl.remove();
}

commandForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const instruction = commandInput.value.trim();
  if (!instruction) return;

  appendMessage(instruction, 'user');
  commandInput.value = '';
  executeBtn.disabled = true;
  startProgressPolling();

  try {
    const res = await fetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instruction })
    });
    const result = await res.json();
    stopProgressPolling();

    if (result.requires_confirmation) {
      pendingTaskId = result.task_id;
      confirmPromptText.innerText = result.message;
      confirmModal.style.display = 'flex';
      appendMessage(`⚠️ Confirmation required: ${result.message}`, 'assistant');
    } else {
      appendMessage(result.message, 'assistant', result.actions_executed);
      refreshScreenshot();
      checkDeviceStatus();
      fetchHistory();
    }
  } catch (err) {
    stopProgressPolling();
    appendMessage(`Error: ${err.message}`, 'assistant');
  } finally {
    executeBtn.disabled = false;
  }
});

stopBtn.addEventListener('click', async () => {
  try {
    stopProgressPolling();
    const res = await fetch('/api/stop', { method: 'POST' });
    const data = await res.json();
    appendMessage(`🛑 ${data.message}`, 'assistant');
    executeBtn.disabled = false;
  } catch (err) {
    console.error(err);
  }
});

clearBtn.addEventListener('click', () => {
  chatHistory.innerHTML = '';
});

refreshDeviceBtn.addEventListener('click', () => {
  checkDeviceStatus();
});

refreshScreenBtn.addEventListener('click', () => {
  refreshScreenshot();
});

// Confirmation dialog actions
confirmApproveBtn.addEventListener('click', async () => {
  if (pendingTaskId !== null) {
    confirmModal.style.display = 'none';
    const tId = pendingTaskId;
    pendingTaskId = null;
    const res = await fetch('/api/confirmation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: tId, approved: true })
    });
    const result = await res.json();
    appendMessage(result.message, 'assistant', result.actions_executed);
    refreshScreenshot();
    checkDeviceStatus();
    fetchHistory();
  }
});

confirmRejectBtn.addEventListener('click', async () => {
  if (pendingTaskId !== null) {
    confirmModal.style.display = 'none';
    const tId = pendingTaskId;
    pendingTaskId = null;
    const res = await fetch('/api/confirmation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: tId, approved: false })
    });
    const result = await res.json();
    appendMessage(result.message, 'assistant');
  }
});

// Periodic status checks
checkHealth();
checkDeviceStatus();
fetchHistory();
setInterval(() => {
  checkDeviceStatus();
}, 5000);
