/* ===== CashTrap — SIH 2026 | Fullstack Interactive App Logic ===== */

const API_BASE = window.location.origin + '/api';

// Global state
let dashboardMap = null;
let hotspotMap = null;
let trendChart = null;
let statusChart = null;
let typeChart = null;
let allAlertsCache = [];
let activeCountdowns = {};
let currentAlertFilter = 'all';

// ===== Utilities =====
function fmtTime(iso) {
    try {
        const d = new Date(iso);
        return d.toLocaleString('en-IN', {
            day: '2-digit', month: 'short',
            hour: '2-digit', minute: '2-digit',
            hour12: false,
        });
    } catch { return iso; }
}

function fmtCurrency(amount) {
    return '₹' + amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function riskClass(level) {
    return { 'High': 'risk-high', 'Medium': 'risk-medium', 'Low': 'risk-low' }[level] || 'risk-low';
}

function probColor(prob) {
    if (prob >= 0.65) return 'var(--neon-red)';
    if (prob >= 0.35) return 'var(--neon-yellow)';
    return 'var(--neon-green)';
}

function statusClass(status) {
    return {
        'Under Review': 'status-review',
        'Resolved': 'status-resolved',
        'Escalated': 'status-escalated',
    }[status] || 'status-review';
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.borderColor = type === 'success' ? 'var(--neon-green)' : (type === 'danger' ? 'var(--neon-red)' : 'var(--neon-cyan)');
    toast.innerHTML = `<span>📢 ${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ===== Clock & Countdown Timers =====
function updateClock() {
    const now = new Date();
    const el = document.getElementById('live-clock');
    if (el) el.textContent = now.toLocaleTimeString('en-IN', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

function startCountdownTick() {
    setInterval(() => {
        document.querySelectorAll('.timer-value-dynamic').forEach(el => {
            const alertId = el.dataset.alertId;
            if (!activeCountdowns[alertId]) {
                activeCountdowns[alertId] = Math.floor(Math.random() * 600) + 720;
            }
            if (activeCountdowns[alertId] > 0) {
                activeCountdowns[alertId]--;
            }
            const mins = Math.floor(activeCountdowns[alertId] / 60);
            const secs = activeCountdowns[alertId] % 60;
            el.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')} MINS`;
        });
    }, 1000);
}
startCountdownTick();

// ===== Navigation & Role Switching =====
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');
const pageTitle = document.getElementById('page-title');
const pageSub = document.getElementById('page-sub');
const roleSelect = document.getElementById('role-select');
const roleNameDisplay = document.getElementById('role-name-display');

const roleMeta = {
    sho: { title: 'Command Dashboard', sub: 'SHO / Inspector Operational View', view: 'dashboard' },
    constable: { title: 'Constable Mobile PCR App', sub: 'Field PCR Interception GPS View', view: 'constable' },
    bank: { title: 'Bank ATM Security Portal', sub: 'Branch Manager Advance Warning System', view: 'bank' },
    dcp: { title: 'DCP / SP District Command', sub: 'District Executive Analytics & Allocation', view: 'dcp' },
    i4c: { title: 'I4C National Intelligence', sub: 'State-wise Fraud Migration & Advisories', view: 'i4c' },
    family: { title: 'Family Pre-Crime Shield', sub: 'Voluntary Protection for Elderly Relatives', view: 'family' },
};

roleSelect.addEventListener('change', (e) => {
    const roleKey = e.target.value;
    const meta = roleMeta[roleKey];
    if (meta) {
        roleNameDisplay.textContent = meta.title;
        switchView(meta.view, meta.title, meta.sub);
        showToast(`Switched operational context to ${meta.title}`, 'info');
        
        // Trigger role specific data loading
        if (roleKey === 'dcp') loadDCPMetrics();
        if (roleKey === 'i4c') loadI4CNationalData();
        if (roleKey === 'bank') loadBankPortalData();
        if (roleKey === 'constable') loadConstableAppData();
    }
});

function switchView(viewName, titleText, subText) {
    navItems.forEach(n => n.classList.remove('active'));
    const matchingNav = document.querySelector(`.nav-item[data-view="${viewName}"]`);
    if (matchingNav) matchingNav.classList.add('active');

    views.forEach(v => v.classList.remove('active'));
    const targetView = document.getElementById('view-' + viewName);
    if (targetView) targetView.classList.add('active');

    if (pageTitle) pageTitle.textContent = titleText;
    if (pageSub) pageSub.textContent = subText;

    if (viewName === 'hotspots' && !hotspotMap) {
        setTimeout(initHotspotMap, 100);
    }
    if (viewName === 'hotspots' && hotspotMap) {
        setTimeout(() => hotspotMap.invalidateSize(), 100);
    }
    if (viewName === 'reports') {
        setTimeout(loadReports, 100);
    }
}

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.dataset.view;
        switchView(view, view.charAt(0).toUpperCase() + view.slice(1), 'Proactive Cybercrime Analytics');
    });
});

document.getElementById('menu-toggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});

// ===== API Fetching =====
async function fetchJSON(endpoint, options = {}) {
    try {
        let res = await fetch(API_BASE + endpoint, options);
        if (!res.ok && window.location.port === '5173') {
            res = await fetch('http://127.0.0.1:8000/api' + endpoint, options);
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        if (window.location.port === '5173') {
            try {
                const fallbackRes = await fetch('http://127.0.0.1:8000/api' + endpoint, options);
                if (fallbackRes.ok) return await fallbackRes.json();
            } catch (e) {}
        }
        console.error(`Fetch error [${endpoint}]:`, err);
        return null;
    }
}

// ===== KPIs =====
async function loadKPIs() {
    const data = await fetchJSON('/kpis');
    if (!data) return;
    document.getElementById('kpi-total').textContent = data.total_complaints;
    document.getElementById('kpi-high-risk').textContent = data.high_risk_alerts;
    document.getElementById('kpi-predicted').textContent = data.predicted_withdrawals;
    document.getElementById('kpi-recovery').textContent = data.recovery_rate + '%';

    const threatEl = document.getElementById('threat-level');
    if (data.high_risk_alerts > 5) {
        threatEl.textContent = 'CRITICAL';
        threatEl.style.color = 'var(--neon-red)';
    } else if (data.high_risk_alerts > 2) {
        threatEl.textContent = 'HIGH RISK';
        threatEl.style.color = 'var(--neon-yellow)';
    } else {
        threatEl.textContent = 'MODERATE';
        threatEl.style.color = 'var(--neon-green)';
    }
}

// ===== Dashboard Map =====
const DEFAULT_HOTSPOTS = [
    { name: "Andheri West ATM Zone", latitude: 19.1197, longitude: 72.8464, intensity: 0.95, active_cases: 24 },
    { name: "Bandra Cyber Corridor", latitude: 19.0596, longitude: 72.8295, intensity: 0.88, active_cases: 19 },
    { name: "Connaught Place Hub", latitude: 28.6315, longitude: 77.2167, intensity: 0.82, active_cases: 15 },
    { name: "MG Road Cash Zone", latitude: 12.9716, longitude: 77.5946, intensity: 0.76, active_cases: 12 },
    { name: "Park Street Corridor", latitude: 22.5551, longitude: 88.3516, intensity: 0.70, active_cases: 9 }
];

async function initDashboardMap() {
    const [hotspotsRes, predictions] = await Promise.all([
        fetchJSON('/hotspots'),
        fetchJSON('/predictions'),
    ]);

    const hotspots = (hotspotsRes && hotspotsRes.length > 0) ? hotspotsRes : DEFAULT_HOTSPOTS;

    if (dashboardMap) dashboardMap.remove();

    dashboardMap = L.map('map', {
        center: [20.5937, 78.9629],
        zoom: 5,
        zoomControl: true,
        attributionControl: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(dashboardMap);

    const heatPoints = hotspots.map(h => [h.latitude, h.longitude, h.intensity]);
    if (typeof L.heatLayer === 'function') {
        L.heatLayer(heatPoints, {
            radius: 45, blur: 35, maxZoom: 12,
            gradient: { 0.0: '#0000ff', 0.3: '#00e5ff', 0.6: '#ffd84d', 0.8: '#ff3860', 1.0: '#ff0000' },
        }).addTo(dashboardMap);
    }

    // Render prediction markers with Top 3 info
    if (predictions && predictions.length > 0) {
        predictions.forEach(p => {
            const isHigh = p.risk_level === 'High';
            const color = isHigh ? '#ff3860' : (p.risk_level === 'Medium' ? '#ffc107' : '#00ff9d');
            const marker = L.circleMarker([p.predicted_lat, p.predicted_lon], {
                radius: isHigh ? 12 : 8,
                fillColor: color, color: color, weight: 2, fillOpacity: 0.7
            }).addTo(dashboardMap);

            let top3HTML = '';
            if (p.top3_locations && p.top3_locations.length > 0) {
                top3HTML = `<br><strong>Top 3 Predicted Cashout Targets:</strong><br>` +
                    p.top3_locations.map(t => `${t.rank}. ${t.name} (${(t.probability*100).toFixed(0)}%)`).join('<br>');
            }

            marker.bindPopup(
                `<div style="font-family:var(--font-main);">` +
                `<strong>🚨 Predicted Cashout ATM</strong><br>` +
                `<span style="color:${color};font-weight:700;">${p.predicted_location}</span><br>` +
                `Risk: ${p.risk_level} (${(p.probability * 100).toFixed(0)}%)` +
                top3HTML +
                `</div>`
            );
        });
    }

    const countEl = document.getElementById('hotspot-count');
    if (countEl) countEl.textContent = hotspots.length + ' active zones';

    setTimeout(() => { if (dashboardMap) dashboardMap.invalidateSize(); }, 200);
}

// ===== Hotspots Map =====
async function initHotspotMap() {
    const [hotspotsRes, predictions] = await Promise.all([
        fetchJSON('/hotspots'),
        fetchJSON('/predictions'),
    ]);
    const hotspots = (hotspotsRes && hotspotsRes.length > 0) ? hotspotsRes : DEFAULT_HOTSPOTS;

    if (hotspotMap) hotspotMap.remove();

    hotspotMap = L.map('map-hotspots', {
        center: [20.5937, 78.9629], zoom: 5, zoomControl: true, attributionControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(hotspotMap);

    const heatPoints = hotspots.map(h => [h.latitude, h.longitude, h.intensity]);
    if (typeof L.heatLayer === 'function') {
        L.heatLayer(heatPoints, {
            radius: 50, blur: 40, maxZoom: 12,
            gradient: { 0.0: '#0000ff', 0.3: '#00e5ff', 0.6: '#ffd84d', 0.8: '#ff3860', 1.0: '#ff0000' }
        }).addTo(hotspotMap);
    }

    renderHotspotsTable(hotspots);
}

function renderHotspotsTable(hotspots) {
    const tbody = document.getElementById('hotspots-table-body');
    if (!tbody) return;
    tbody.innerHTML = hotspots.sort((a, b) => b.intensity - a.intensity).map(h => {
        const pct = (h.intensity * 100).toFixed(0);
        const statusColor = h.intensity > 0.8 ? 'var(--neon-red)' : (h.intensity > 0.65 ? 'var(--neon-yellow)' : 'var(--neon-green)');
        const status = h.intensity > 0.8 ? 'Critical' : (h.intensity > 0.65 ? 'High Activity' : 'Moderate');
        return `
            <tr>
                <td style="color:var(--text-primary);font-weight:500;">${h.name}</td>
                <td style="font-family:var(--font-mono);font-size:12px;">${h.latitude.toFixed(4)}, ${h.longitude.toFixed(4)}</td>
                <td>
                    <div class="prob-cell">
                        <div class="prob-bar" style="width:80px;"><div class="prob-fill" style="width:${pct}%;background:${statusColor};"></div></div>
                        <span class="prob-text">${pct}%</span>
                    </div>
                </td>
                <td style="color:var(--text-primary);font-weight:600;">${h.active_cases}</td>
                <td><span class="risk-badge ${h.intensity > 0.8 ? 'risk-high' : h.intensity > 0.65 ? 'risk-medium' : 'risk-low'}">${status}</span></td>
            </tr>
        `;
    }).join('');
}

// ===== Trend Chart =====
async function loadTrendChart() {
    const data = await fetchJSON('/trends');
    if (!data) return;

    const labels = data.map(d => fmtDate(d.date));
    const complaintsData = data.map(d => d.complaints);
    const resolvedData = data.map(d => d.resolved);

    const ctx = document.getElementById('trend-chart');
    if (!ctx) return;
    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Fraud Complaints',
                    data: complaintsData,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.08)',
                    borderWidth: 2.5, fill: true, tension: 0.4
                },
                {
                    label: 'Interception Recoveries',
                    data: resolvedData,
                    borderColor: '#059669',
                    backgroundColor: 'rgba(5, 150, 105, 0.08)',
                    borderWidth: 2.5, fill: true, tension: 0.4
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#334155', font: { weight: '600' } } } },
            scales: {
                x: { grid: { color: '#e2e8f0' }, ticks: { color: '#475569' } },
                y: { grid: { color: '#e2e8f0' }, ticks: { color: '#475569' }, beginAtZero: true }
            }
        }
    });
}

// ===== Alerts Table =====
async function loadAlertsTable() {
    const alerts = await fetchJSON('/alerts?limit=10');
    if (!alerts) return;
    allAlertsCache = alerts;
    renderAlertsTable(alerts, 'alerts-table-body');
}

function renderAlertsTable(alerts, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-row">No active alerts.</td></tr>';
        return;
    }

    tbody.innerHTML = alerts.map(a => {
        const pct = (a.probability * 100).toFixed(0);
        const statusText = a.dispatch_status || 'Pending';
        return `
            <tr>
                <td style="font-family:var(--font-mono);color:var(--neon-cyan);">#${a.id}</td>
                <td style="color:var(--text-primary);font-weight:500;">
                    ${a.title}<br>
                    <span style="font-size:11px;color:var(--text-muted);">${a.description}</span>
                </td>
                <td style="font-size:12px;color:var(--text-secondary);">${a.predicted_location}</td>
                <td><span class="risk-badge ${riskClass(a.risk_level)}">${a.risk_level}</span></td>
                <td>
                    <div class="prob-cell">
                        <div class="prob-bar"><div class="prob-fill" style="width:${pct}%;background:${probColor(a.probability)};"></div></div>
                        <span class="prob-text">${pct}%</span>
                    </div>
                </td>
                <td>
                    <span class="countdown-badge">
                        ⏱️ <span class="timer-value-dynamic" data-alert-id="${a.id}">14:32 MINS</span>
                    </span>
                </td>
                <td>
                    <div style="display:flex;gap:6px;">
                        <button class="btn-action btn-forecast" style="padding:4px 8px;" onclick="openShapModal(${a.id})">🧠 Why</button>
                        <button class="btn-action btn-ingest" style="padding:4px 8px;" onclick="openSMSModal(${a.id})">📲 SMS Officer</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// ===== SHAP Modal =====
window.openShapModal = function(alertId) {
    const alert = allAlertsCache.find(a => a.id === alertId);
    if (!alert) return;

    const modal = document.getElementById('shap-modal');
    const body = document.getElementById('shap-modal-body');
    const factors = alert.shap_explanation || [];
    const maxContrib = Math.max(...factors.map(f => Math.abs(f.contribution)), 0.01);

    body.innerHTML = `
        <p style="color:var(--text-secondary);margin-bottom:15px;">
            Alert <strong style="color:var(--neon-cyan);">#${alert.id}</strong> prediction confidence:
            <strong style="color:${probColor(alert.probability)};">${(alert.probability*100).toFixed(0)}%</strong>.
            Feature attribution breakdown computed by CashTrap XGBoost TreeExplainer:
        </p>
        ${factors.map(f => {
            const isPos = f.contribution >= 0;
            const width = (Math.abs(f.contribution) / maxContrib * 100).toFixed(0);
            return `
                <div class="shap-factor">
                    <div class="shap-factor-header">
                        <span class="shap-factor-name">${f.feature}</span>
                        <span class="shap-factor-value ${isPos ? 'positive' : 'negative'}">
                            ${isPos ? '+' : ''}${f.contribution.toFixed(3)}
                        </span>
                    </div>
                    <div class="shap-bar-container">
                        <div class="shap-bar ${isPos ? 'positive' : 'negative'}" style="width:${width}%;"></div>
                    </div>
                    <div class="shap-factor-desc">${f.description}</div>
                </div>
            `;
        }).join('')}
    `;

    modal.classList.add('active');
};

document.getElementById('modal-close').addEventListener('click', () => {
    document.getElementById('shap-modal').classList.remove('active');
});

// ===== SMS Dispatch Modal =====
window.openSMSModal = function(alertId) {
    const alert = allAlertsCache.find(a => a.id === alertId);
    if (!alert) return;

    const modal = document.getElementById('sms-modal');
    const body = document.getElementById('sms-modal-body');

    body.innerHTML = `
        <div style="background:#09131d;border:1px solid var(--border-color);padding:15px;border-radius:8px;font-family:var(--font-mono);font-size:12px;color:var(--neon-cyan);margin-bottom:15px;">
            🚨 CASHTRAP DISPATCH SMS ALERTS 🚨<br>
            TARGET: ${alert.predicted_location}<br>
            RISK: ${alert.risk_level.toUpperCase()} (${(alert.probability*100).toFixed(0)}% prob)<br>
            STATION: ${alert.nearest_police_station || 'Central Cyber Station'}<br>
            ASSIGNED PCR: ${alert.assigned_constable || 'Constable PCR-14'}<br>
            CASH-OUT REMAINING: 14 MINS
        </div>
        <div style="display:flex;gap:10px;">
            <button class="btn-action btn-ingest" style="flex:1;" onclick="sendSMSDispatch(${alert.id}, 'constable')">📲 Dispatch Constable SMS</button>
            <button class="btn-action btn-forecast" style="flex:1;" onclick="sendSMSDispatch(${alert.id}, 'bank_manager')">🏦 Dispatch Bank Manager SMS</button>
        </div>
    `;

    modal.classList.add('active');
};

window.sendSMSDispatch = async function(alertId, recipientType) {
    const res = await fetchJSON('/dispatch-sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alertId, recipient_type: recipientType })
    });
    if (res && res.success) {
        showToast(`Instant SMS dispatched to ${recipientType.toUpperCase()}!`, 'success');
        document.getElementById('sms-modal').classList.remove('active');
    }
};

document.getElementById('sms-modal-close').addEventListener('click', () => {
    document.getElementById('sms-modal').classList.remove('active');
});

// ===== Ingestion Modal =====
const ingestModal = document.getElementById('ingest-modal');
document.getElementById('btn-open-ingest').addEventListener('click', () => {
    ingestModal.classList.add('active');
});
document.getElementById('ingest-modal-close').addEventListener('click', () => {
    ingestModal.classList.remove('active');
});

document.getElementById('form-ingest-complaint').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        victim_name: document.getElementById('inp-victim-name').value,
        victim_phone: document.getElementById('inp-victim-phone').value,
        victim_age: parseInt(document.getElementById('inp-victim-age').value),
        amount: parseFloat(document.getElementById('inp-amount').value),
        complaint_type: document.getElementById('inp-complaint-type').value,
        location: document.getElementById('inp-location').value,
    };

    const res = await fetchJSON('/complaints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res && res.prediction) {
        showToast(`Complaint #${res.complaint_id} ingested! Risk: ${res.prediction.risk_level}`, 'success');
        const container = document.getElementById('ingest-result-container');
        container.style.display = 'block';
        
        let top3List = res.prediction.top3_locations.map(t => 
            `<li style="margin-bottom:4px;">Rank ${t.rank}: <strong>${t.name}</strong> (${(t.probability*100).toFixed(0)}% confidence) — ${t.distance_km} km away</li>`
        ).join('');

        container.innerHTML = `
            <div style="background:#0d1829;border:1px solid var(--neon-cyan);padding:15px;border-radius:8px;">
                <h4 style="color:var(--neon-cyan);">AI Prediction Result:</h4>
                <p><strong>Predicted Withdrawal ATM:</strong> ${res.prediction.predicted_location}</p>
                <p><strong>Risk Level:</strong> <span class="risk-badge ${riskClass(res.prediction.risk_level)}">${res.prediction.risk_level} (${(res.prediction.probability*100).toFixed(0)}%)</span></p>
                <h5 style="margin-top:10px;color:var(--text-secondary);">Top 3 Withdrawal Locations Forecasted:</h5>
                <ul style="padding-left:20px;font-size:12px;color:var(--text-primary);">${top3List}</ul>
            </div>
        `;

        loadKPIs();
        loadAlertsTable();
        initDashboardMap();
    }
});

// ===== Simulation & Retraining Action Triggers =====
document.getElementById('btn-trigger-forecast').addEventListener('click', async () => {
    showToast('Running 24-hour future fraud forecast simulation...', 'info');
    const res = await fetchJSON('/simulate-fraud', { method: 'POST' });
    if (res && res.success) {
        showToast(`Generated ${res.generated_count} simulated future risk alerts!`, 'success');
        loadKPIs();
        loadAlertsTable();
        initDashboardMap();
    }
});

document.getElementById('btn-trigger-retrain').addEventListener('click', async () => {
    showToast('Triggering AI Model Retraining Pipeline (XGBoost + DBSCAN)...', 'info');
    const res = await fetchJSON('/retrain', { method: 'POST' });
    if (res && res.status === 'Success') {
        showToast(`ML Model retrained! Accuracy: ${res.metrics.accuracy}, Clusters: ${res.metrics.new_clusters}`, 'success');
    }
});

// ===== Role Specific Data Loaders =====
async function loadDCPMetrics() {
    const data = await fetchJSON('/district-kpis');
    if (!data) return;
    document.getElementById('dcp-active-pcrs').textContent = data.active_pcrs + ' PCRs';
    document.getElementById('dcp-avg-time').textContent = data.avg_response_time_mins + ' Mins';
    document.getElementById('dcp-funds-saved').textContent = data.funds_saved_today_inr;

    const tbody = document.getElementById('dcp-station-table');
    tbody.innerHTML = data.station_performance.map(s => `
        <tr>
            <td style="color:#fff;font-weight:600;">${s.station}</td>
            <td>${s.dispatches}</td>
            <td style="color:var(--neon-green);font-weight:700;">${s.apprehended}</td>
            <td style="font-family:var(--font-mono);">${s.success_rate}</td>
        </tr>
    `).join('');
}

async function loadI4CNationalData() {
    const data = await fetchJSON('/national-data');
    if (!data) return;

    const tbody = document.getElementById('i4c-state-table');
    tbody.innerHTML = data.state_fraud_volumes.map(s => `
        <tr>
            <td style="color:#fff;font-weight:600;">${s.state}</td>
            <td>${s.complaints}</td>
            <td>₹ ${s.amount_lakhs} Lakhs</td>
            <td><span class="risk-badge risk-high">${s.risk_index}</span></td>
        </tr>
    `).join('');

    const corridorBox = document.getElementById('i4c-corridor-list');
    corridorBox.innerHTML = data.migration_corridors.map(c => `
        <div style="background:#0d1829;border:1px solid var(--border-color);padding:12px;border-radius:8px;margin-bottom:10px;">
            <div style="display:flex;justify-space-between;margin-bottom:4px;">
                <strong style="color:var(--neon-cyan);">${c.corridor}</strong>
                <span style="color:var(--neon-red);font-family:var(--font-mono);font-weight:700;">${c.surge}</span>
            </div>
            <span style="font-size:12px;color:var(--text-muted);">Pattern: ${c.mule_pattern}</span>
        </div>
    `).join('');
}

async function loadBankPortalData() {
    const alerts = await fetchJSON('/alerts?limit=5');
    if (!alerts) return;

    const tbody = document.getElementById('bank-atm-table-body');
    tbody.innerHTML = alerts.map(a => `
        <tr>
            <td style="color:#fff;">${a.predicted_location}</td>
            <td><span class="risk-badge ${riskClass(a.risk_level)}">${a.risk_level}</span></td>
            <td><span style="color:var(--neon-yellow);font-weight:600;">Under Watch (15m window)</span></td>
            <td><button class="btn-action btn-forecast" onclick="toggleFreezeATM('${a.predicted_location}')">🔒 Freeze ATM</button></td>
        </tr>
    `).join('');
}

window.toggleFreezeATM = async function(atmName) {
    const res = await fetchJSON('/bank/freeze-atm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ atm_name: atmName, frozen: true })
    });
    if (res && res.success) {
        showToast(`ATM ${atmName} cash dispenser frozen for security!`, 'success');
    }
};

async function loadConstableAppData() {
    const alerts = await fetchJSON('/alerts?limit=1');
    if (alerts && alerts.length > 0) {
        const topAlert = alerts[0];
        document.getElementById('constable-atm-name').textContent = topAlert.predicted_location;
        document.getElementById('constable-alert-desc').textContent = topAlert.description;
    }
}

// Constable Action Buttons
document.getElementById('btn-constable-enroute').addEventListener('click', () => {
    showToast('PCR-14 Status: EN ROUTE TO ATM', 'info');
});
document.getElementById('btn-constable-arrived').addEventListener('click', () => {
    showToast('PCR-14 Status: ARRIVED AT ATM LOCATION', 'warning');
});
document.getElementById('btn-constable-apprehend').addEventListener('click', () => {
    showToast('🎉 MULE APPREHENDED! ₹ 2,50,000 RECOVERED AT ATM!', 'success');
});

// Family Guard Buttons
document.getElementById('btn-fam-approve').addEventListener('click', async () => {
    showToast('Transaction Approved by Family Guardian', 'info');
});
document.getElementById('btn-fam-block').addEventListener('click', async () => {
    showToast('🛑 TRANSACTION BLOCKED & ESCALATED TO 1930 CYBER HELPLINE!', 'danger');
});

// ===== Reports View =====
async function loadReports() {
    const complaints = await fetchJSON('/complaints');
    if (!complaints) return;

    const total = complaints.length;
    const escalated = complaints.filter(c => c.status === 'Escalated').length;
    const resolved = complaints.filter(c => c.status === 'Resolved').length;
    const avgAmount = total > 0 ? complaints.reduce((s, c) => s + c.amount, 0) / total : 0;

    document.getElementById('rpt-total').textContent = total;
    document.getElementById('rpt-escalated').textContent = escalated;
    document.getElementById('rpt-resolved').textContent = resolved;
    document.getElementById('rpt-avg-amount').textContent = fmtCurrency(avgAmount);

    const tbody = document.getElementById('complaints-table-body');
    tbody.innerHTML = complaints.map(c => `
        <tr>
            <td style="font-family:var(--font-mono);color:var(--neon-cyan);">#${c.id}</td>
            <td style="color:var(--text-primary);">${c.victim_name}</td>
            <td style="font-size:12px;">${c.victim_phone || '+91 98765 43210'} (${c.victim_age || 45} yrs)</td>
            <td>${c.complaint_type}</td>
            <td style="font-family:var(--font-mono);color:var(--text-primary);">${fmtCurrency(c.amount)}</td>
            <td>${c.location}</td>
            <td><span class="risk-badge ${c.status === 'Resolved' ? 'risk-low' : (c.status === 'Escalated' ? 'risk-high' : 'risk-medium')}">${c.status}</span></td>
        </tr>
    `).join('');
}

// ===== Initialization =====
async function init() {
    await Promise.all([
        loadKPIs(),
        initDashboardMap(),
        loadTrendChart(),
        loadAlertsTable(),
    ]);
}

init();
