/* ===== Tech Titans — SIH 2026 | Frontend Logic ===== */

const API_BASE = window.location.origin + '/api';

// Global state
let dashboardMap = null;
let hotspotMap = null;
let trendChart = null;
let statusChart = null;
let typeChart = null;
let allAlertsCache = [];
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

function fmtDate(iso) {
    try {
        const d = new Date(iso);
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
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

// ===== Clock =====
function updateClock() {
    const now = new Date();
    const el = document.getElementById('live-clock');
    if (el) {
        el.textContent = now.toLocaleTimeString('en-IN', { hour12: false });
    }
}
setInterval(updateClock, 1000);
updateClock();

// ===== Navigation =====
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');
const pageTitle = document.getElementById('page-title');
const pageSub = document.getElementById('page-sub');

const viewMeta = {
    dashboard: { title: 'Dashboard', sub: 'Real-time cybercrime predictive overview' },
    hotspots: { title: 'Hotspots', sub: 'Geospatial analysis of active fraud zones' },
    alerts: { title: 'Alerts', sub: 'All predictive alerts with AI explainability' },
    reports: { title: 'Reports', sub: 'Complaint registry and analytics breakdown' },
};

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.dataset.view;
        navItems.forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        views.forEach(v => v.classList.remove('active'));
        document.getElementById('view-' + view).classList.add('active');
        const meta = viewMeta[view];
        pageTitle.textContent = meta.title;
        pageSub.textContent = meta.sub;

        // Initialize maps on view switch (Leaflet needs visible container)
        if (view === 'hotspots' && !hotspotMap) {
            setTimeout(initHotspotMap, 100);
        }
        if (view === 'hotspots' && hotspotMap) {
            setTimeout(() => hotspotMap.invalidateSize(), 100);
        }
        if (view === 'reports') {
            setTimeout(loadReports, 100);
        }

        // Close mobile sidebar
        document.getElementById('sidebar').classList.remove('open');
    });
});

// Mobile sidebar toggle
document.getElementById('menu-toggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});

// ===== API Fetching =====
async function fetchJSON(endpoint) {
    try {
        const res = await fetch(API_BASE + endpoint);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`Fetch error [${endpoint}]:`, err);
        return null;
    }
}

// ===== KPI Cards =====
async function loadKPIs() {
    const data = await fetchJSON('/kpis');
    if (!data) return;
    document.getElementById('kpi-total').textContent = data.total_complaints;
    document.getElementById('kpi-high-risk').textContent = data.high_risk_alerts;
    document.getElementById('kpi-predicted').textContent = data.predicted_withdrawals;
    document.getElementById('kpi-recovery').textContent = data.recovery_rate + '%';

    // Threat level
    const threatEl = document.getElementById('threat-level');
    if (data.high_risk_alerts > 5) {
        threatEl.textContent = 'CRITICAL';
        threatEl.style.color = 'var(--neon-red)';
    } else if (data.high_risk_alerts > 2) {
        threatEl.textContent = 'ELEVATED';
        threatEl.style.color = 'var(--neon-yellow)';
    } else {
        threatEl.textContent = 'MODERATE';
        threatEl.style.color = 'var(--neon-green)';
    }
}

// ===== Dashboard Map =====
async function initDashboardMap() {
    const [hotspots, predictions] = await Promise.all([
        fetchJSON('/hotspots'),
        fetchJSON('/predictions'),
    ]);

    if (!hotspots) return;

    dashboardMap = L.map('map', {
        center: [22.5, 80],
        zoom: 5,
        zoomControl: true,
        attributionControl: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
    }).addTo(dashboardMap);

    // Heatmap layer
    const heatPoints = hotspots.map(h => [h.latitude, h.longitude, h.intensity]);
    L.heatLayer(heatPoints, {
        radius: 45,
        blur: 35,
        maxZoom: 12,
        gradient: {
            0.0: '#0000ff',
            0.3: '#00e5ff',
            0.6: '#ffd84d',
            0.8: '#ff3860',
            1.0: '#ff0000',
        },
    }).addTo(dashboardMap);

    // Hotspot markers
    hotspots.forEach(h => {
        const radius = 12 + h.intensity * 10;
        const marker = L.circleMarker([h.latitude, h.longitude], {
            radius: radius,
            fillColor: h.intensity > 0.8 ? '#ff3860' : (h.intensity > 0.65 ? '#ffd84d' : '#00e5ff'),
            color: h.intensity > 0.8 ? '#ff3860' : (h.intensity > 0.65 ? '#ffd84d' : '#00e5ff'),
            weight: 2,
            fillOpacity: 0.3,
            opacity: 0.8,
        }).addTo(dashboardMap);

        marker.bindPopup(
            `<strong>${h.name}</strong><br>` +
            `Intensity: ${(h.intensity * 100).toFixed(0)}%<br>` +
            `Active Cases: ${h.active_cases}`
        );
    });

    // Prediction markers (predicted withdrawal locations)
    if (predictions) {
        predictions.forEach(p => {
            if (p.risk_level === 'High') {
                const icon = L.divIcon({
                    className: '',
                    html: `<div class="hotspot-marker marker-high" style="width:14px;height:14px;"></div>`,
                    iconSize: [14, 14],
                });
                L.marker([p.predicted_lat, p.predicted_lon], { icon })
                    .addTo(dashboardMap)
                    .bindPopup(
                        `<strong>Predicted Withdrawal</strong><br>` +
                        `${p.predicted_location}<br>` +
                        `Risk: ${p.risk_level} (${(p.probability * 100).toFixed(0)}%)`
                    );
            }
        });
    }

    const countEl = document.getElementById('hotspot-count');
    if (countEl) countEl.textContent = hotspots.length + ' zones';
}

// ===== Hotspot Map (separate view) =====
async function initHotspotMap() {
    const [hotspots, predictions] = await Promise.all([
        fetchJSON('/hotspots'),
        fetchJSON('/predictions'),
    ]);
    if (!hotspots) return;

    hotspotMap = L.map('map-hotspots', {
        center: [22.5, 80],
        zoom: 5,
        zoomControl: true,
        attributionControl: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
    }).addTo(hotspotMap);

    const heatPoints = hotspots.map(h => [h.latitude, h.longitude, h.intensity]);
    L.heatLayer(heatPoints, {
        radius: 50,
        blur: 40,
        maxZoom: 12,
        gradient: {
            0.0: '#0000ff',
            0.3: '#00e5ff',
            0.6: '#ffd84d',
            0.8: '#ff3860',
            1.0: '#ff0000',
        },
    }).addTo(hotspotMap);

    // All prediction markers
    if (predictions) {
        predictions.forEach(p => {
            const cls = p.risk_level === 'High' ? 'marker-high' :
                        p.risk_level === 'Medium' ? 'marker-medium' : 'marker-low';
            const size = p.risk_level === 'High' ? 16 : (p.risk_level === 'Medium' ? 12 : 8);
            const icon = L.divIcon({
                className: '',
                html: `<div class="hotspot-marker ${cls}" style="width:${size}px;height:${size}px;"></div>`,
                iconSize: [size, size],
            });
            L.marker([p.predicted_lat, p.predicted_lon], { icon })
                .addTo(hotspotMap)
                .bindPopup(
                    `<strong>Predicted Withdrawal</strong><br>` +
                    `${p.predicted_location}<br>` +
                    `Risk: ${p.risk_level} (${(p.probability * 100).toFixed(0)}%)<br>` +
                    `Complaint ID: #${p.complaint_id}`
                );
        });
    }

    hotspotMap.invalidateSize();

    const countEl = document.getElementById('hotspot-count-2');
    if (countEl) countEl.textContent = hotspots.length + ' zones';

    // Populate hotspot table
    renderHotspotsTable(hotspots);
}

function renderHotspotsTable(hotspots) {
    const tbody = document.getElementById('hotspots-table-body');
    if (!tbody) return;
    tbody.innerHTML = hotspots
        .sort((a, b) => b.intensity - a.intensity)
        .map(h => {
            const pct = (h.intensity * 100).toFixed(0);
            const statusColor = h.intensity > 0.8 ? 'var(--neon-red)' :
                                h.intensity > 0.65 ? 'var(--neon-yellow)' : 'var(--neon-green)';
            const status = h.intensity > 0.8 ? 'Critical' :
                           h.intensity > 0.65 ? 'High Activity' : 'Moderate';
            return `
                <tr>
                    <td style="color:var(--text-primary);font-weight:500;">${h.name}</td>
                    <td style="font-family:var(--font-mono);font-size:12px;">${h.latitude.toFixed(4)}, ${h.longitude.toFixed(4)}</td>
                    <td>
                        <div class="prob-cell">
                            <div class="prob-bar" style="width:80px;">
                                <div class="prob-fill" style="width:${pct}%;background:${statusColor};"></div>
                            </div>
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

    const labels = data.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
    });
    const complaintsData = data.map(d => d.complaints);
    const resolvedData = data.map(d => d.resolved);

    const ctx = document.getElementById('trend-chart');
    if (!ctx) return;

    if (trendChart) trendChart.destroy();

    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(0, 229, 255, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 229, 255, 0.0)');

    const gradient2 = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient2.addColorStop(0, 'rgba(0, 255, 157, 0.25)');
    gradient2.addColorStop(1, 'rgba(0, 255, 157, 0.0)');

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'New Complaints',
                    data: complaintsData,
                    borderColor: '#00e5ff',
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#00e5ff',
                    pointBorderColor: '#0a0e17',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                },
                {
                    label: 'Resolved',
                    data: resolvedData,
                    borderColor: '#00ff9d',
                    backgroundColor: gradient2,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#00ff9d',
                    pointBorderColor: '#0a0e17',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#8b9bb4', font: { family: "'Space Grotesk', sans-serif", size: 12 } },
                    position: 'top',
                },
                tooltip: {
                    backgroundColor: '#1a2332',
                    borderColor: '#2a3a55',
                    borderWidth: 1,
                    titleColor: '#00e5ff',
                    bodyColor: '#e8eef5',
                    padding: 12,
                    cornerRadius: 8,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(30, 42, 63, 0.5)' },
                    ticks: { color: '#5a6b85', font: { family: "'JetBrains Mono', monospace", size: 11 } },
                },
                y: {
                    grid: { color: 'rgba(30, 42, 63, 0.5)' },
                    ticks: { color: '#5a6b85', font: { family: "'JetBrains Mono', monospace", size: 11 } },
                    beginAtZero: true,
                },
            },
        },
    });
}

// ===== Alerts Table (Dashboard — top 5) =====
async function loadAlertsTable() {
    const alerts = await fetchJSON('/alerts?limit=5');
    if (!alerts) return;
    renderAlertsTable(alerts, 'alerts-table-body');
}

// ===== All Alerts View =====
async function loadAllAlerts() {
    const alerts = await fetchJSON('/alerts?limit=50');
    if (!alerts) return;
    allAlertsCache = alerts;
    renderAllAlerts();
    const countEl = document.getElementById('alert-total-count');
    if (countEl) countEl.textContent = alerts.length + ' alerts';
}

function renderAllAlerts() {
    const filtered = currentAlertFilter === 'all'
        ? allAlertsCache
        : allAlertsCache.filter(a => a.risk_level === currentAlertFilter);
    renderAlertsTable(filtered, 'all-alerts-table-body');
}

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentAlertFilter = btn.dataset.filter;
        renderAllAlerts();
    });
});

function renderAlertsTable(alerts, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-row">No alerts found.</td></tr>';
        return;
    }

    tbody.innerHTML = alerts.map(a => {
        const pct = (a.probability * 100).toFixed(0);
        return `
            <tr>
                <td style="font-family:var(--font-mono);color:var(--neon-cyan);">#${a.id}</td>
                <td style="color:var(--text-primary);font-weight:500;max-width:220px;overflow:hidden;text-overflow:ellipsis;">${a.title}</td>
                <td style="font-size:12px;">${a.predicted_location}</td>
                <td><span class="risk-badge ${riskClass(a.risk_level)}">${a.risk_level}</span></td>
                <td>
                    <div class="prob-cell">
                        <div class="prob-bar">
                            <div class="prob-fill" style="width:${pct}%;background:${probColor(a.probability)};"></div>
                        </div>
                        <span class="prob-text">${pct}%</span>
                    </div>
                </td>
                <td style="font-size:12px;color:var(--text-muted);">${fmtTime(a.timestamp)}</td>
                <td>
                    <button class="btn-why" onclick="openShapModal(${a.id})">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        Why
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ===== SHAP Modal =====
window.openShapModal = function(alertId) {
    const alert = allAlertsCache.find(a => a.id === alertId)
        || window._dashboardAlerts?.find(a => a.id === alertId);
    if (!alert) return;

    const modal = document.getElementById('shap-modal');
    const body = document.getElementById('shap-modal-body');
    const factors = alert.shap_explanation || [];

    const maxContribution = Math.max(...factors.map(f => Math.abs(f.contribution)), 0.01);

    body.innerHTML = `
        <p class="shap-intro">
            Alert <strong style="color:var(--neon-cyan);">#${alert.id}</strong> was generated for complaint
            <strong>#${alert.complaint_id}</strong> with a <strong style="color:${probColor(alert.probability)};">
            ${(alert.probability * 100).toFixed(0)}%</strong> predicted withdrawal probability.
            The AI model analyzed the following contributing factors:
        </p>
        ${factors.map(f => {
            const isPositive = f.contribution >= 0;
            const barWidth = (Math.abs(f.contribution) / maxContribution * 100).toFixed(0);
            return `
                <div class="shap-factor">
                    <div class="shap-factor-header">
                        <span class="shap-factor-name">${f.feature}</span>
                        <span class="shap-factor-value ${isPositive ? 'positive' : 'negative'}">
                            ${isPositive ? '+' : ''}${f.contribution.toFixed(3)}
                        </span>
                    </div>
                    <div class="shap-bar-container">
                        <div class="shap-bar ${isPositive ? 'positive' : 'negative'}" style="width:${barWidth}%;"></div>
                    </div>
                    <div class="shap-factor-desc">${f.description}</div>
                </div>
            `;
        }).join('')}
        <div class="shap-summary">
            <div class="shap-summary-icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
            </div>
            <div class="shap-summary-text">
                <strong>Model Summary:</strong> This alert was flagged because the complaint exhibits
                patterns consistent with imminent cash-out activity. The primary drivers are
                ${factors.filter(f => f.contribution > 0).slice(0, 2).map(f => f.feature.toLowerCase()).join(' and ')}.
                Law enforcement is advised to monitor the predicted withdrawal location at
                <strong>${alert.predicted_location}</strong>.
            </div>
        </div>
    `;

    modal.classList.add('active');
};

document.getElementById('modal-close').addEventListener('click', () => {
    document.getElementById('shap-modal').classList.remove('active');
});

document.getElementById('shap-modal').addEventListener('click', (e) => {
    if (e.target.id === 'shap-modal') {
        document.getElementById('shap-modal').classList.remove('active');
    }
});

// ===== Reports View =====
async function loadReports() {
    const [complaints, kpis] = await Promise.all([
        fetchJSON('/complaints'),
        fetchJSON('/kpis'),
    ]);
    if (!complaints) return;

    // Summary KPIs
    const total = complaints.length;
    const escalated = complaints.filter(c => c.status === 'Escalated').length;
    const resolved = complaints.filter(c => c.status === 'Resolved').length;
    const avgAmount = total > 0 ? complaints.reduce((s, c) => s + c.amount, 0) / total : 0;

    document.getElementById('rpt-total').textContent = total;
    document.getElementById('rpt-escalated').textContent = escalated;
    document.getElementById('rpt-resolved').textContent = resolved;
    document.getElementById('rpt-avg-amount').textContent = fmtCurrency(avgAmount);

    const countEl = document.getElementById('rpt-complaint-count');
    if (countEl) countEl.textContent = total + ' records';

    // Complaints table
    const tbody = document.getElementById('complaints-table-body');
    tbody.innerHTML = complaints.map(c => `
        <tr>
            <td style="font-family:var(--font-mono);color:var(--neon-cyan);">#${c.id}</td>
            <td style="color:var(--text-primary);">${c.victim_name}</td>
            <td>${c.complaint_type}</td>
            <td style="font-family:var(--font-mono);color:var(--text-primary);">${fmtCurrency(c.amount)}</td>
            <td>${c.location}</td>
            <td><span class="status-badge ${statusClass(c.status)}">${c.status}</span></td>
            <td style="font-size:12px;color:var(--text-muted);">${fmtTime(c.timestamp)}</td>
        </tr>
    `).join('');

    // Status chart
    renderStatusChart(complaints);
    // Type chart
    renderTypeChart(complaints);
}

function renderStatusChart(complaints) {
    const counts = { 'Under Review': 0, 'Resolved': 0, 'Escalated': 0 };
    complaints.forEach(c => counts[c.status]++);

    const ctx = document.getElementById('status-chart');
    if (!ctx) return;
    if (statusChart) statusChart.destroy();

    statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(counts),
            datasets: [{
                data: Object.values(counts),
                backgroundColor: ['#4d9eff', '#00ff9d', '#ff3860'],
                borderColor: '#141d2e',
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#8b9bb4', font: { family: "'Space Grotesk', sans-serif", size: 12 } },
                    position: 'bottom',
                },
                tooltip: {
                    backgroundColor: '#1a2332',
                    borderColor: '#2a3a55',
                    borderWidth: 1,
                    titleColor: '#00e5ff',
                    bodyColor: '#e8eef5',
                    padding: 12,
                },
            },
        },
    });
}

function renderTypeChart(complaints) {
    const counts = {};
    complaints.forEach(c => { counts[c.complaint_type] = (counts[c.complaint_type] || 0) + 1; });
    const labels = Object.keys(counts);
    const data = Object.values(counts);

    const ctx = document.getElementById('type-chart');
    if (!ctx) return;
    if (typeChart) typeChart.destroy();

    typeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Count',
                data: data,
                backgroundColor: 'rgba(0, 229, 255, 0.5)',
                borderColor: '#00e5ff',
                borderWidth: 1.5,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a2332',
                    borderColor: '#2a3a55',
                    borderWidth: 1,
                    titleColor: '#00e5ff',
                    bodyColor: '#e8eef5',
                    padding: 12,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(30, 42, 63, 0.5)' },
                    ticks: { color: '#5a6b85', font: { family: "'JetBrains Mono', monospace", size: 11 } },
                    beginAtZero: true,
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#8b9bb4', font: { family: "'Space Grotesk', sans-serif", size: 11 } },
                },
            },
        },
    });
}

// ===== Initialization =====
async function init() {
    // Load dashboard data in parallel
    await Promise.all([
        loadKPIs(),
        initDashboardMap(),
        loadTrendChart(),
        loadAlertsTable(),
        loadAllAlerts(),
    ]);

    // Cache alerts for SHAP modal from dashboard table
    const dashAlerts = await fetchJSON('/alerts?limit=20');
    window._dashboardAlerts = dashAlerts || [];
}

init();
