// app/static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // --- KONFIGURASI & STATE ---
    const API_BASE_URL = `http://192.168.18.53:5001`; // <-- Sesuaikan jika perlu
    const state = {
        sessionId: sessionStorage.getItem('sessionId'),
        isQrVisible: false,
        qrTimer: null,
        lastKnownState: { bottles: 0, points: 0 },
    };

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
    };

    // --- FUNGSI HELPER ---
    const api = {
        async request(endpoint, options = {}) {
            try {
                const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
                    cache: 'no-cache',
                    headers: { 'Content-Type': 'application/json' },
                    ...options,
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'An unknown error occurred.');
                return data;
            } catch (error) {
                showAlert(error.message, 'danger');
                console.error("API Error:", error);
                return null;
            }
        },
        getState: () => api.request(`scan_state?session_id=${state.sessionId}`),
        startScan: () => api.request('start_scan', { method: 'POST', body: JSON.stringify({}) }),
        stopScan: () => api.request('stop_scan', { method: 'POST', body: JSON.stringify({ session_id: state.sessionId }) }),
        generateQr: () => api.request('generate_qr', { method: 'POST', body: JSON.stringify({ session_id: state.sessionId }) }),
    };
    
    // <<< FUNGSI INI DIPERBARUI AGAR TIDAK MENUMPUK >>>
    function showAlert(msg, color = 'info', timeout = 3000) {
        // Hapus notifikasi lama sebelum menampilkan yang baru
        DOMElements.alertArea.innerHTML = '';

        const alertId = `alert-${Date.now()}`;
        const alertEl = document.createElement('div');
        alertEl.id = alertId;
        // Menambahkan kelas untuk animasi fade-in
        alertEl.className = `alert alert-${color} alert-dismissible fade show`;
        alertEl.setAttribute('role', 'alert');
        alertEl.innerHTML = `
            ${msg}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        DOMElements.alertArea.prepend(alertEl);

        // Atur timer untuk menghilangkan notifikasi secara otomatis
        if (timeout) {
            setTimeout(() => {
                const activeAlert = document.getElementById(alertId);
                // Cek apakah elemen alert masih ada sebelum mencoba menutupnya
                if (activeAlert && bootstrap.Alert.getOrCreateInstance(activeAlert)) {
                    bootstrap.Alert.getOrCreateInstance(activeAlert).close();
                }
            }, timeout);
        }
    }

    function triggerUpdateAnimation(element) {
        element.classList.add('update-animation');
        element.addEventListener('animationend', () => {
            element.classList.remove('update-animation');
        }, { once: true });
    }
    
    // --- FUNGSI UTAMA ---
    function renderUI(scanData) {
        const bottles = scanData?.bottles ?? 0;
        const points = scanData?.points ?? 0;
        const isActive = scanData?.active ?? false;

        // Animate if value increases
        if (bottles > state.lastKnownState.bottles) triggerUpdateAnimation(DOMElements.bottles);
        if (points > state.lastKnownState.points) triggerUpdateAnimation(DOMElements.points);
        
        DOMElements.bottles.textContent = bottles;
        DOMElements.points.textContent = points;
        state.lastKnownState = { bottles, points };

        DOMElements.sessionIdDisplay.textContent = scanData?.session_id ?? "-";
        DOMElements.scanStatus.textContent = isActive ? "Active" : "Idle";
        DOMElements.statusIndicator.classList.toggle('active', isActive);

        DOMElements.btnStart.disabled = isActive;
        DOMElements.btnStop.disabled = !isActive;
        DOMElements.btnGenerate.disabled = isActive || (bottles === 0 && points === 0);

        if (!state.isQrVisible) {
            DOMElements.qrSection.style.display = 'none';
        }
    }

    async function updateStateFromServer() {
        if (!state.sessionId) {
            renderUI(null);
            return;
        }
        const scanData = await api.getState();
        if (scanData) {
            // Cek apakah ada botol baru yang diterima berdasarkan panjang history
            if (scanData.history && scanData.history.length > (state.lastKnownState.historyLength || 0)) {
                showAlert(`<strong>Botol diterima!</strong> +2 poin`, 'success');
            }
            state.lastKnownState.historyLength = scanData.history?.length ?? 0;
            renderUI(scanData);
        } else {
            sessionStorage.removeItem('sessionId');
            state.sessionId = null;
            renderUI(null);
        }
    }

    // --- EVENT LISTENERS ---
    DOMElements.btnStart.onclick = async () => {
        const res = await api.startScan();
        if (res?.status === 'started') {
            state.sessionId = res.session_id;
            sessionStorage.setItem('sessionId', state.sessionId);
            state.isQrVisible = false;
            state.lastKnownState = { bottles: 0, points: 0, historyLength: 0 };
            showAlert("<strong>Sesi scan dimulai!</strong> Mesin siap menerima botol.", "info");
            updateStateFromServer();
        }
    };

    DOMElements.btnStop.onclick = async () => {
        const res = await api.stopScan();
        if (res) {
            showAlert("<strong>Sesi scan dihentikan.</strong>", "warning");
            updateStateFromServer();
        }
    };

    DOMElements.btnGenerate.onclick = async () => {
        const res = await api.generateQr();
        if (res) {
            state.isQrVisible = true;
            DOMElements.qrSection.style.display = 'block';
            DOMElements.qrImg.src = `${API_BASE_URL}/qr_image/${res.id}`;
            DOMElements.qrInfo.innerHTML = `Bottles: <b>${res.bottles}</b> | Points: <b>${res.points}</b>`;
            showAlert("<strong>QR Code dibuat!</strong> Silakan pindai dengan aplikasi user.", "primary", 25000);

            sessionStorage.removeItem('sessionId');
            state.sessionId = null;
            renderUI(null);

            // Timer untuk menyembunyikan QR dan progress bar
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
                } else {
                    const progress = (remainingTime / qrDuration) * 100;
                    DOMElements.qrTimerBar.style.width = `${progress}%`;
                }
            }, 100);
        }
    };

    // --- INISIALISASI ---
    updateStateFromServer();
    setInterval(updateStateFromServer, 2000);
});