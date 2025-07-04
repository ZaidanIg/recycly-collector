document.addEventListener('DOMContentLoaded', () => {
    // --- KONFIGURASI & STATE ---
    const API_BASE_URL = ``;
    const state = { sessionId: sessionStorage.getItem('sessionId'), isQrVisible: false, qrTimer: null, lastKnownState: { bottles: 0, points: 0 }, isPollingActive: false, pollIntervalId: null };
    
    // --- CACHE ELEMENT DOM ---
    const DOMElements = {
        statusIndicator: document.getElementById('status-indicator'),
        scanStatus: document.getElementById('scan-status'),
        bottles: document.getElementById('bottles'),
        points: document.getElementById('points'),
        sessionIdDisplay: document.getElementById('session-id'),
        btnStart: document.getElementById('btn-start'),
        btnStop: document.getElementById('btn-stop'),
        btnGenerate: document.getElementById('btn-generate'),
        qrSection: document.getElementById('qr-section'),
        qrImg: document.getElementById('qr-img'),
        qrInfo: document.getElementById('qr-info'),
        qrTimerBar: document.getElementById('qr-timer-bar'),
        alertArea: document.getElementById('alert-area'),
        btnDownload: document.getElementById('btn-download-qr') // Tambahkan tombol unduh ke cache
    };

    // --- FUNGSI HELPER ---
    const api = {
        async request(endpoint, options = {}) {
            try {
                const response = await fetch(`${API_BASE_URL}/${endpoint}`, { cache: 'no-cache', headers: { 'Content-Type': 'application/json' }, ...options });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'An unknown error occurred.');
                return data;
            } catch (error) {
                showAlert(error.message, 'danger');
                console.error("API Error:", error);
                stopPolling();
                return null;
            }
        },
        getState: () => api.request(`scan_state?session_id=${state.sessionId}`),
        startScan: () => api.request('start_scan', { method: 'POST', body: JSON.stringify({}) }),
        stopScan: () => api.request('stop_scan', { method: 'POST', body: JSON.stringify({ session_id: state.sessionId }) }),
        generateQr: () => api.request('generate_qr', { method: 'POST', body: JSON.stringify({ session_id: state.sessionId }) }),
    };

    function showAlert(msg, color = 'info', timeout = 5000) {
        DOMElements.alertArea.innerHTML = '';
        const alertId = `alert-${Date.now()}`;
        const alertEl = document.createElement('div');
        alertEl.id = alertId;
        alertEl.className = `alert alert-${color} alert-dismissible fade show`;
        alertEl.setAttribute('role', 'alert');
        alertEl.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        DOMElements.alertArea.prepend(alertEl);
        if (timeout) {
            setTimeout(() => {
                const activeAlert = document.getElementById(alertId);
                if (activeAlert && typeof bootstrap !== 'undefined' && bootstrap.Alert.getOrCreateInstance(activeAlert)) {
                    bootstrap.Alert.getOrCreateInstance(activeAlert).close();
                }
            }, timeout);
        }
    }

    // --- FUNGSI UTAMA ---
    function renderUI(scanData) { /* ... Fungsi ini tidak berubah ... */ 
        const bottles = scanData?.bottles ?? 0; const points = scanData?.points ?? 0; const isActive = scanData?.active ?? false;
        DOMElements.bottles.textContent = bottles; DOMElements.points.textContent = points; state.lastKnownState = { bottles, points, historyLength: scanData?.history?.length ?? 0 };
        DOMElements.sessionIdDisplay.textContent = scanData?.session_id ?? "-"; DOMElements.scanStatus.textContent = isActive ? "Active" : "Idle"; DOMElements.statusIndicator.classList.toggle('active', isActive);
        DOMElements.btnStart.disabled = isActive; DOMElements.btnStop.disabled = !isActive; DOMElements.btnGenerate.disabled = isActive || (bottles === 0 && points === 0);
        if (!state.isQrVisible) { DOMElements.qrSection.style.display = 'none'; }
    }

    async function updateStateFromServer() { /* ... Fungsi ini tidak berubah ... */
        if (!state.sessionId) { renderUI(null); stopPolling(); return; }
        const scanData = await api.getState();
        if (scanData) {
            if (scanData.history && scanData.history.length > state.lastKnownState.historyLength) {
                const lastEvent = scanData.history[scanData.history.length - 1];
                if(lastEvent.status === 'accepted'){ showAlert(`<strong>Botol diterima!</strong> +${lastEvent.point} poin`, 'success'); } 
                else if (lastEvent.status === 'rejected') { showAlert(`<strong>Botol ditolak.</strong>`, 'warning'); }
            }
            renderUI(scanData);
            if (!scanData.active) { stopPolling(); }
        } else {
            sessionStorage.removeItem('sessionId'); state.sessionId = null; renderUI(null); stopPolling();
        }
    }
    
    function startPolling() { if (state.isPollingActive) return; state.isPollingActive = true; console.log('Polling status dimulai...'); updateStateFromServer(); state.pollIntervalId = setInterval(updateStateFromServer, 2000); }
    function stopPolling() { if (!state.isPollingActive) return; state.isPollingActive = false; clearInterval(state.pollIntervalId); state.pollIntervalId = null; console.log('Polling status dihentikan.'); }

    // --- EVENT LISTENERS ---
    DOMElements.btnStart.onclick = async () => {
        const res = await api.startScan();
        if (res?.status === 'started') { state.sessionId = res.session_id; sessionStorage.setItem('sessionId', state.sessionId); state.isQrVisible = false; state.lastKnownState = { bottles: 0, points: 0, historyLength: 0 }; showAlert("<strong>Sesi scan dimulai!</strong>", "info"); startPolling(); }
    };

    DOMElements.btnStop.onclick = async () => {
        stopPolling();
        const res = await api.stopScan();
        if (res) { showAlert("<strong>Sesi scan dihentikan.</strong>", "warning"); updateStateFromServer(); } 
        else { startPolling(); }
    };

    DOMElements.btnGenerate.onclick = async () => {
        stopPolling();
        const res = await api.generateQr();
        if (res && res.filename) {
            state.isQrVisible = true;
            
            DOMElements.qrImg.src = `${API_BASE_URL}/display_qr/${res.filename}?t=${new Date().getTime()}`;

            DOMElements.btnDownload.href = `${API_BASE_URL}/download_qr/${res.filename}`;
            
            DOMElements.qrSection.style.display = 'block';
            DOMElements.btnDownload.style.display = 'inline-block';
            
            DOMElements.qrInfo.innerHTML = `Bottles: <b>${res.bottles}</b> | Points: <b>${res.points}</b>`;
            showAlert("<strong>QR Code dibuat!</strong> Silakan pindai atau unduh.", "primary");

            sessionStorage.removeItem('sessionId');
            state.sessionId = null;
            renderUI(null);

            const qrDuration = 30000; 
            let startTime = Date.now();
            if (state.qrTimer) clearInterval(state.qrTimer);
            state.qrTimer = setInterval(() => {
                const elapsedTime = Date.now() - startTime;
                const remainingTime = qrDuration - elapsedTime;
                if (remainingTime <= 0) {
                    clearInterval(state.qrTimer);
                    state.isQrVisible = false;
                    DOMElements.qrSection.style.display = 'none';
                    DOMElements.btnDownload.style.display = 'none';
                } else {
                    const progress = (remainingTime / qrDuration) * 100;
                    DOMElements.qrTimerBar.style.width = `${progress}%`;
                }
            }, 1000); 
        }
    };

    // --- INISIALISASI ---
    function initialize() { if(state.sessionId) { startPolling(); } else { renderUI(null); } }
    initialize();
});