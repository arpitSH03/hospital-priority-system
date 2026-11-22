/**
 * Hospital Emergency & Patient Priority Management System - Frontend Application
 * Pure Vanilla JavaScript (Fetch API, DOM Manipulation, Chart.js)
 */

// ============================================================================
// 1. Centralized API Client (api.js style)
// ============================================================================
const api = {
    // Auto-detect environment:
    // - GitHub Pages → use Railway deployed backend
    // - Local → use same-origin FastAPI server
    baseUrl: window.location.hostname === "arpitsh03.github.io"
        ? "https://hospital-priority-system-production.up.railway.app/api"
        : "/api",

    /**
     * Core fetch wrapper with JSON serialization and structured error handling.
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                "Content-Type": "application/json",
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json().catch(() => null);

            if (!response.ok) {
                const errorMsg = data?.detail || data?.message || `HTTP ${response.status} Error`;
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            console.error(`[API Error] ${options.method || "GET"} ${endpoint}:`, error);
            throw error;
        }
    },

    // Patients Endpoints
    async registerPatient(payload) {
        return this.request("/patients", { method: "POST", body: JSON.stringify(payload) });
    },
    async getPatients(status = null) {
        const query = status ? `?status=${encodeURIComponent(status)}` : "";
        return this.request(`/patients${query}`);
    },
    async getPatient(id) {
        return this.request(`/patients/${id}`);
    },
    async updatePriority(id, priority) {
        return this.request(`/patients/${id}/priority`, { method: "PUT", body: JSON.stringify({ priority }) });
    },
    async updateStatus(id, status, note) {
        return this.request(`/patients/${id}/status`, { method: "PUT", body: JSON.stringify({ status, note }) });
    },
    async dischargePatient(id) {
        return this.request(`/patients/${id}/discharge`, { method: "POST" });
    },
    async getPatientHistory(id) {
        return this.request(`/patients/${id}/history`);
    },

    // Queue Endpoints
    async getQueue() {
        return this.request("/queue");
    },
    async allocateDoctor() {
        return this.request("/queue/allocate", { method: "POST" });
    },
    async applyAging(thresholdMinutes = 30) {
        return this.request("/queue/apply-aging", { method: "POST", body: JSON.stringify({ threshold_minutes: thresholdMinutes }) });
    },

    // Doctors Endpoints
    async getDoctors() {
        return this.request("/doctors");
    },
    async addDoctor(name, specialization) {
        return this.request("/doctors", { method: "POST", body: JSON.stringify({ name, specialization }) });
    },
    async updateDoctorAvailability(id, isAvailable) {
        return this.request(`/doctors/${id}/availability`, { method: "PUT", body: JSON.stringify({ is_available: isAvailable }) });
    },

    // Reports Endpoints
    async getReportSummary() {
        return this.request("/reports/summary");
    },

    // Benchmark Endpoint
    async getBenchmark(sizes = "1000,5000,10000") {
        return this.request(`/benchmark?sizes=${encodeURIComponent(sizes)}`);
    },
};

// ============================================================================
// 2. Application State & Controller
// ============================================================================
class HospitalApp {
    constructor() {
        this.currentSection = "dashboard";
        this.queueData = [];
        this.doctorsData = [];
        this.patientsCache = {};
        this.autoRefreshTimer = null;

        // Chart.js instances
        this.chartPriority = null;
        this.chartWaitTimes = null;
        this.chartBenchmark = null;
        this.benchmarkLoaded = false;
    }

    init() {
        this.setupNavigation();
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);

        // Load initial data
        this.refreshAll();

        // 10-second automatic polling for real-time queue synchronization
        this.autoRefreshTimer = setInterval(() => {
            if (this.currentSection === "dashboard" || this.currentSection === "queue" || this.currentSection === "doctors") {
                this.loadQueue();
                this.loadDashboard();
                this.loadDoctors();
            }
        }, 10000);
    }

    updateClock() {
        const timeEl = document.getElementById("system-time");
        if (timeEl) {
            const now = new Date();
            timeEl.innerText = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        }
    }

    setupNavigation() {
        const navButtons = document.querySelectorAll(".nav-btn");
        navButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const section = btn.getAttribute("data-section");
                this.switchSection(section);
            });
        });
    }

    switchSection(sectionName) {
        this.currentSection = sectionName;

        // Update nav buttons
        document.querySelectorAll(".nav-btn").forEach(btn => {
            if (btn.getAttribute("data-section") === sectionName) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        // Update sections
        document.querySelectorAll(".app-section").forEach(sec => {
            if (sec.id === `section-${sectionName}`) {
                sec.classList.add("active");
            } else {
                sec.classList.remove("active");
            }
        });

        // Trigger section-specific reloads
        if (sectionName === "dashboard") this.loadDashboard();
        if (sectionName === "queue") this.loadQueue();
        if (sectionName === "doctors") this.loadDoctors();
        if (sectionName === "reports") this.loadReports();
    }

    async refreshAll() {
        await Promise.allSettled([
            this.loadDashboard(),
            this.loadQueue(),
            this.loadDoctors(),
        ]);
        this.showToast("System state refreshed.", "info");
    }

    // ========================================================================
    // Section 1: Dashboard Logic
    // ========================================================================
    async loadDashboard() {
        try {
            const [reportRes, queueRes, docsRes] = await Promise.all([
                api.getReportSummary(),
                api.getQueue(),
                api.getDoctors(),
            ]);

            const report = reportRes.data || {};
            const queue = queueRes.data || [];
            const doctors = docsRes.data || [];

            // Update KPI cards
            const waitingCount = report.currently_waiting ?? queue.length;
            document.getElementById("kpi-waiting").innerText = waitingCount;
            document.getElementById("kpi-in-treatment").innerText = report.in_treatment ?? 0;

            const docStats = report.doctors || {};
            const busyDocs = docStats.busy ?? 0;
            const freeDocs = (docStats.total ?? doctors.length) - busyDocs;
            document.getElementById("kpi-doctors").innerText = `${freeDocs} Free / ${busyDocs} Busy`;
            document.getElementById("kpi-utilization").innerText = `${docStats.utilization_percentage ?? 0}% Utilization`;

            const avgWaits = report.avg_wait_minutes_by_priority || {};
            const avgOverall = Math.round(Object.values(avgWaits).reduce((a, b) => a + b, 0) / 4);
            document.getElementById("kpi-avg-wait").innerText = `${avgOverall || 0} min`;
            document.getElementById("kpi-crit-wait").innerText = `${avgWaits["1_critical"] || 0} min`;

            // Update queue badge in nav
            document.getElementById("queue-badge").innerText = waitingCount;

            // Render top 5 waiting on dashboard
            this.renderDashboardQueue(queue.slice(0, 5));

            // Render active doctor treatments
            this.renderDashboardActiveDoctors(doctors);

        } catch (err) {
            console.error("Dashboard load failed:", err);
        }
    }

    renderDashboardQueue(topPatients) {
        const tbody = document.querySelector("#dash-queue-table tbody");
        if (!tbody) return;

        if (topPatients.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No emergency patients currently waiting.</td></tr>`;
            return;
        }

        tbody.innerHTML = topPatients.map((p, idx) => `
            <tr class="row-p${p.priority}">
                <td><strong>#${p.queue_rank || idx + 1}</strong></td>
                <td>${this.getPriorityBadge(p.priority)}</td>
                <td><a href="#" class="patient-link" onclick="app.showPatientHistory(${p.id})">${this.escapeHtml(p.name)}</a></td>
                <td>${this.escapeHtml(p.category)}</td>
                <td>${p.waiting_minutes}m</td>
            </tr>
        `).join("");
    }

    renderDashboardActiveDoctors(doctors) {
        const container = document.getElementById("dash-active-doctors");
        if (!container) return;

        const busyDocs = doctors.filter(d => !d.is_available && d.current_patient_id);
        if (busyDocs.length === 0) {
            container.innerHTML = `<p class="empty-state">No doctors are currently engaged in emergency treatments.</p>`;
            return;
        }

        container.innerHTML = busyDocs.map(d => `
            <div class="active-treatment-box" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${this.escapeHtml(d.name)}</strong> <span style="color: #64748b; font-size: 0.8rem;">(${this.escapeHtml(d.specialization)})</span>
                    <div style="font-size: 0.82rem; margin-top: 2px;">
                        Treating: <a href="#" class="patient-link" onclick="app.showPatientHistory(${d.current_patient_id})">Patient #${d.current_patient_id}</a>
                    </div>
                </div>
                <button class="btn btn-secondary btn-sm" onclick="app.dischargePatient(${d.current_patient_id})">
                    Discharge
                </button>
            </div>
        `).join("");
    }

    // ========================================================================
    // Section 2: Patient Registration
    // ========================================================================
    updatePriorityPreview() {
        const cat = document.getElementById("reg-category").value;
        const badge = document.getElementById("preview-priority-badge");
        const desc = document.getElementById("preview-priority-desc");

        const mapping = {
            Critical: { prio: 1, text: "Priority 1 • Critical", cls: "badge-p1", desc: "Life-threatening condition. Placed at the top of the Min-Heap queue." },
            Urgent:   { prio: 2, text: "Priority 2 • Urgent",   cls: "badge-p2", desc: "Severe condition with high risk of deterioration. Prioritized immediately after Critical." },
            Moderate: { prio: 3, text: "Priority 3 • Moderate", cls: "badge-p3", desc: "Distressing but stable condition. Treated after Urgent cases." },
            Minor:    { prio: 4, text: "Priority 4 • Minor",    cls: "badge-p4", desc: "Non-urgent minor condition. Served after all higher categories." },
        };

        const current = mapping[cat] || mapping.Moderate;
        badge.className = `badge ${current.cls}`;
        badge.innerText = current.text;
        desc.innerText = current.desc;
    }

    async handlePatientRegistration(event) {
        event.preventDefault();
        const submitBtn = document.getElementById("btn-submit-patient");
        submitBtn.disabled = true;
        submitBtn.innerText = "Registering & Heapifying...";

        const payload = {
            name: document.getElementById("reg-name").value.trim(),
            age: parseInt(document.getElementById("reg-age").value),
            gender: document.getElementById("reg-gender").value,
            contact: document.getElementById("reg-contact").value.trim(),
            category: document.getElementById("reg-category").value,
            complaint: document.getElementById("reg-complaint").value.trim(),
        };

        try {
            const res = await api.registerPatient(payload);
            const p = res.data;
            this.showToast(`Patient ${p.name} registered as Priority ${p.priority} (${p.category})!`, "success");

            // Reset form
            document.getElementById("patient-registration-form").reset();
            this.updatePriorityPreview();

            // Refresh queue and dashboard
            this.loadQueue();
            this.loadDashboard();

            // Switch to queue to show new insertion
            this.switchSection("queue");
        } catch (err) {
            this.showToast(err.message || "Failed to register patient.", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = "Register & Insert to Min-Heap";
        }
    }

    // ========================================================================
    // Section 3: Emergency Queue Logic
    // ========================================================================
    async loadQueue() {
        try {
            const res = await api.getQueue();
            this.queueData = res.data || [];
            document.getElementById("queue-badge").innerText = this.queueData.length;
            this.filterQueueTable();
        } catch (err) {
            console.error("Failed to load queue:", err);
        }
    }

    filterQueueTable() {
        const query = (document.getElementById("queue-search")?.value || "").toLowerCase().trim();
        const tbody = document.getElementById("queue-table-body");
        if (!tbody) return;

        const filtered = this.queueData.filter(p => 
            p.name.toLowerCase().includes(query) ||
            p.id.toString().includes(query) ||
            p.complaint.toLowerCase().includes(query) ||
            p.category.toLowerCase().includes(query)
        );

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state">${query ? "No waiting patients match your search." : "No emergency patients currently waiting."}</td></tr>`;
            return;
        }

        tbody.innerHTML = filtered.map((p, idx) => `
            <tr class="row-p${p.priority}">
                <td><strong>#${p.queue_rank || idx + 1}</strong></td>
                <td>${this.getPriorityBadge(p.priority)}</td>
                <td>
                    <a href="#" class="patient-link" onclick="app.showPatientHistory(${p.id})">
                        ${this.escapeHtml(p.name)}
                    </a>
                    <div style="font-size: 0.75rem; color: #64748b;">ID #${p.id} &bull; ${this.escapeHtml(p.contact || "No phone")}</div>
                </td>
                <td>${p.age}y / ${p.gender}</td>
                <td>
                    <span style="font-weight: 500;">${this.escapeHtml(p.category)}:</span>
                    <span style="color: #475569;">${this.escapeHtml(p.complaint)}</span>
                </td>
                <td>
                    <strong>${p.waiting_minutes} min</strong>
                    <div style="font-size: 0.72rem; color: #94a3b8;">${new Date(p.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </td>
                <td>
                    <select class="priority-select" onchange="app.changePatientPriority(${p.id}, this.value)">
                        <option value="1" ${p.priority === 1 ? "selected" : ""}>1 - Critical</option>
                        <option value="2" ${p.priority === 2 ? "selected" : ""}>2 - Urgent</option>
                        <option value="3" ${p.priority === 3 ? "selected" : ""}>3 - Moderate</option>
                        <option value="4" ${p.priority === 4 ? "selected" : ""}>4 - Minor</option>
                    </select>
                </td>
            </tr>
        `).join("");
    }

    async changePatientPriority(patientId, newPriority) {
        try {
            await api.updatePriority(patientId, parseInt(newPriority));
            this.showToast(`Patient #${patientId} reprioritized to Priority ${newPriority}. Min-Heap updated.`, "success");
            await this.loadQueue();
            await this.loadDashboard();
        } catch (err) {
            this.showToast(err.message || "Failed to update priority.", "error");
            this.loadQueue(); // revert UI dropdown
        }
    }

    async allocateNextPatient() {
        try {
            const res = await api.allocateDoctor();
            if (res.success) {
                const patName = res.data.patient?.name || "Patient";
                const docName = res.data.doctor?.name || "Doctor";
                this.showToast(`Allocated ${patName} to ${docName}.`, "success");
            } else {
                this.showToast(res.message, "warning");
            }
            await this.loadQueue();
            await this.loadDoctors();
            await this.loadDashboard();
        } catch (err) {
            this.showToast(err.message || "Allocation failed.", "error");
        }
    }

    async applyAgingPrompt() {
        const threshold = prompt("Enter waiting duration threshold in minutes for aging boost:", "30");
        if (threshold === null) return;

        const minutes = parseInt(threshold);
        if (isNaN(minutes) || minutes < 1) {
            alert("Please enter a valid number of minutes.");
            return;
        }

        try {
            const res = await api.applyAging(minutes);
            const boosted = res.data?.boosted_patients || [];
            if (boosted.length > 0) {
                const names = boosted.map(b => `${b.name} (${b.old_priority} -> ${b.new_priority})`).join(", ");
                this.showToast(`Aging Boost: ${boosted.length} patient(s) escalated: ${names}`, "warning");
            } else {
                this.showToast(`No patients waiting over ${minutes} minutes qualify for an aging boost.`, "info");
            }
            await this.loadQueue();
            await this.loadDashboard();
        } catch (err) {
            this.showToast(err.message || "Aging boost failed.", "error");
        }
    }

    // ========================================================================
    // Section 4: Doctors Management
    // ========================================================================
    async loadDoctors() {
        try {
            const res = await api.getDoctors();
            this.doctorsData = res.data || [];
            this.renderDoctorsGrid();
        } catch (err) {
            console.error("Failed to load doctors:", err);
        }
    }

    renderDoctorsGrid() {
        const container = document.getElementById("doctors-container");
        if (!container) return;

        if (this.doctorsData.length === 0) {
            container.innerHTML = `<p class="empty-state">No doctors registered in the system roster.</p>`;
            return;
        }

        container.innerHTML = this.doctorsData.map(d => {
            let statusBadge = "";
            let treatmentInfo = "";

            if (!d.is_available && d.current_patient_id) {
                statusBadge = `<span class="doc-status-badge busy">Busy (In Treatment)</span>`;
                treatmentInfo = `
                    <div class="active-treatment-box">
                        <strong>Actively Treating:</strong>
                        <div style="margin-top: 4px; display: flex; justify-content: space-between; align-items: center;">
                            <a href="#" class="patient-link" onclick="app.showPatientHistory(${d.current_patient_id})">
                                Patient #${d.current_patient_id}
                            </a>
                            <button class="btn btn-secondary btn-sm" onclick="app.dischargePatient(${d.current_patient_id})">
                                Discharge Patient
                            </button>
                        </div>
                    </div>
                `;
            } else if (d.is_available) {
                statusBadge = `<span class="doc-status-badge available">Available in Queue</span>`;
                treatmentInfo = `<div class="active-treatment-box" style="color: #64748b;">Ready in FIFO queue for allocation</div>`;
            } else {
                statusBadge = `<span class="doc-status-badge offduty">Off-Duty</span>`;
                treatmentInfo = `<div class="active-treatment-box" style="color: #94a3b8;">Doctor is currently off-duty</div>`;
            }

            const toggleText = d.is_available ? "Set Off-Duty" : "Set Available";
            const toggleNewState = !d.is_available;
            const disableToggle = (!d.is_available && d.current_patient_id) ? "disabled title='Cannot change availability while in active treatment'" : "";

            return `
                <div class="doctor-card">
                    <div>
                        <div class="doc-header">
                            <div>
                                <h3 class="doc-name">${this.escapeHtml(d.name)}</h3>
                                <p class="doc-spec">${this.escapeHtml(d.specialization)}</p>
                            </div>
                            ${statusBadge}
                        </div>
                        <div style="margin-top: 14px;">
                            ${treatmentInfo}
                        </div>
                    </div>
                    <div class="doc-actions">
                        <span style="font-size: 0.78rem; color: #94a3b8;">Doctor ID #${d.id}</span>
                        <button class="btn btn-secondary btn-sm" ${disableToggle} onclick="app.toggleDoctorAvailability(${d.id}, ${toggleNewState})">
                            ${toggleText}
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    }

    async toggleDoctorAvailability(docId, newState) {
        try {
            await api.updateDoctorAvailability(docId, newState);
            this.showToast(`Doctor availability updated.`, "info");
            await this.loadDoctors();
            await this.loadDashboard();
        } catch (err) {
            this.showToast(err.message || "Failed to update doctor availability.", "error");
        }
    }

    showAddDoctorModal() {
        document.getElementById("modal-add-doctor").classList.remove("hidden");
    }

    closeAddDoctorModal() {
        document.getElementById("modal-add-doctor").classList.add("hidden");
        document.getElementById("form-add-doctor").reset();
    }

    async handleAddDoctorSubmit(event) {
        event.preventDefault();
        const name = document.getElementById("doc-name").value.trim();
        const spec = document.getElementById("doc-spec").value.trim();

        try {
            const res = await api.addDoctor(name, spec);
            this.showToast(`Doctor ${res.data.name} added to roster!`, "success");
            this.closeAddDoctorModal();
            await this.loadDoctors();
            await this.loadDashboard();
        } catch (err) {
            this.showToast(err.message || "Failed to add doctor.", "error");
        }
    }

    async dischargePatient(patientId) {
        if (!confirm(`Are you sure you want to discharge Patient #${patientId}? This will free the assigned doctor.`)) {
            return;
        }

        try {
            const res = await api.dischargePatient(patientId);
            this.showToast(res.message || `Patient #${patientId} discharged.`, "success");

            if (res.data?.auto_allocation?.success) {
                const nextPat = res.data.auto_allocation.patient?.name || "next patient";
                const doc = res.data.auto_allocation.doctor?.name || "doctor";
                setTimeout(() => {
                    this.showToast(`Auto-allocated ${nextPat} to ${doc}!`, "info");
                }, 800);
            }

            await this.loadQueue();
            await this.loadDoctors();
            await this.loadDashboard();
        } catch (err) {
            this.showToast(err.message || "Discharge failed.", "error");
        }
    }

    // ========================================================================
    // Section 5: Reports & Analytics
    // ========================================================================
    async loadReports() {
        try {
            const res = await api.getReportSummary();
            const data = res.data || {};

            // Render stats summary boxes
            document.getElementById("stat-total-treated").innerText = data.total_patients ?? 0;
            document.getElementById("stat-doctor-util").innerText = `${data.doctors?.utilization_percentage ?? 0}%`;
            document.getElementById("stat-discharged-count").innerText = data.discharged ?? 0;

            // Render Charts
            this.renderPriorityChart(data.priority_breakdown || {});
            this.renderWaitTimeChart(data.avg_wait_minutes_by_priority || {});

            // Auto-run DSA benchmark on first report visit
            if (!this.benchmarkLoaded) {
                this.runBenchmark();
            }
        } catch (err) {
            console.error("Failed to load reports:", err);
        }
    }

    renderPriorityChart(breakdown) {
        const ctx = document.getElementById("chart-priority-distribution");
        if (!ctx) return;

        if (this.chartPriority) {
            this.chartPriority.destroy();
        }

        const labels = ["Priority 1: Critical", "Priority 2: Urgent", "Priority 3: Moderate", "Priority 4: Minor"];
        const counts = [
            breakdown["1_critical"] || 0,
            breakdown["2_urgent"] || 0,
            breakdown["3_moderate"] || 0,
            breakdown["4_minor"] || 0,
        ];

        this.chartPriority = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Patients Registered",
                    data: counts,
                    backgroundColor: ["#ef4444", "#f97316", "#f59e0b", "#10b981"],
                    borderColor: ["#b91c1c", "#c2410c", "#b45309", "#047857"],
                    borderWidth: 1,
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                    },
                },
            },
        });
    }

    renderWaitTimeChart(avgWaits) {
        const ctx = document.getElementById("chart-avg-waiting");
        if (!ctx) return;

        if (this.chartWaitTimes) {
            this.chartWaitTimes.destroy();
        }

        const labels = ["P1 (Critical)", "P2 (Urgent)", "P3 (Moderate)", "P4 (Minor)"];
        const waits = [
            avgWaits["1_critical"] || 0,
            avgWaits["2_urgent"] || 0,
            avgWaits["3_moderate"] || 0,
            avgWaits["4_minor"] || 0,
        ];

        this.chartWaitTimes = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Average Wait (Minutes)",
                    data: waits,
                    backgroundColor: "#0284c7",
                    borderColor: "#0369a1",
                    borderWidth: 1,
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Minutes" },
                    },
                },
            },
        });
    }

    // ========================================================================
    // DSA Empirical Benchmark (MinHeap vs Sorted List vs Linear Scan)
    // ========================================================================
    async runBenchmark() {
        const btn = document.getElementById("btn-run-benchmark");
        const tbody = document.getElementById("benchmark-table-body");
        if (btn) {
            btn.disabled = true;
            btn.innerText = "Running Benchmark (N=1k, 5k, 10k)...";
        }
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color: var(--primary);">Running live timed trials (N = 1,000, 5,000, 10,000 elements)... Please wait ~1-2 seconds.</td></tr>`;
        }

        try {
            const res = await api.getBenchmark("1000,5000,10000");
            const data = res.data;
            this.benchmarkLoaded = true;
            this.renderBenchmarkTable(data);
            this.renderBenchmarkChart(data);
            this.showToast("DSA Benchmark completed successfully!", "success");
        } catch (err) {
            console.error("Benchmark failed:", err);
            this.showToast(err.message || "Benchmark failed.", "error");
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color: #ef4444;">Benchmark failed: ${err.message}</td></tr>`;
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Live Benchmark`;
            }
        }
    }

    renderBenchmarkTable(benchmarkData) {
        const tbody = document.getElementById("benchmark-table-body");
        if (!tbody) return;

        const results = benchmarkData.results || [];
        const r1000 = results.find(r => r.n === 1000) || {};
        const r5000 = results.find(r => r.n === 5000) || {};
        const r10000 = results.find(r => r.n === 10000) || {};

        const heapTotal10k = r10000.min_heap?.total_ms || 1;
        const sortRatio = (r10000.sorted_list?.total_ms / heapTotal10k).toFixed(1);
        const linRatio = (r10000.linear_scan?.total_ms / heapTotal10k).toFixed(1);

        tbody.innerHTML = `
            <tr class="row-p4">
                <td>
                    <strong>Custom Indexed Min-Heap</strong>
                    <div style="font-size: 0.75rem; color: #047857;">Array Binary Tree + Position Map</div>
                </td>
                <td><code>O(log N)</code></td>
                <td><code>O(log N)</code></td>
                <td><strong>${r1000.min_heap?.total_ms ?? 0} ms</strong></td>
                <td><strong>${r5000.min_heap?.total_ms ?? 0} ms</strong></td>
                <td><strong>${r10000.min_heap?.total_ms ?? 0} ms</strong></td>
                <td><span class="benchmark-badge-best">1.0x (Fastest Baseline)</span></td>
            </tr>
            <tr class="row-p2">
                <td>
                    <strong>Naive Sorted List</strong>
                    <div style="font-size: 0.75rem; color: #9a3412;">Re-sort array on every insert</div>
                </td>
                <td><code>O(N log N)</code></td>
                <td><code>O(1)</code></td>
                <td>${r1000.sorted_list?.total_ms ?? 0} ms</td>
                <td>${r5000.sorted_list?.total_ms ?? 0} ms</td>
                <td>${r10000.sorted_list?.total_ms ?? 0} ms</td>
                <td><span class="badge badge-p2">${sortRatio}x Slower</span></td>
            </tr>
            <tr class="row-p1">
                <td>
                    <strong>Naive Linear Scan</strong>
                    <div style="font-size: 0.75rem; color: #991b1b;">Linear scan for extract-min</div>
                </td>
                <td><code>O(1)</code></td>
                <td><code>O(N)</code></td>
                <td>${r1000.linear_scan?.total_ms ?? 0} ms</td>
                <td>${r5000.linear_scan?.total_ms ?? 0} ms</td>
                <td>${r10000.linear_scan?.total_ms ?? 0} ms</td>
                <td><span class="badge badge-p1">${linRatio}x Slower</span></td>
            </tr>
        `;
    }

    renderBenchmarkChart(benchmarkData) {
        const ctx = document.getElementById("chart-dsa-benchmark");
        if (!ctx) return;

        if (this.chartBenchmark) {
            this.chartBenchmark.destroy();
        }

        const results = benchmarkData.results || [];
        const labels = results.map(r => `N = ${r.n.toLocaleString()}`);

        const heapTimes = results.map(r => r.min_heap?.total_ms ?? 0);
        const sortTimes = results.map(r => r.sorted_list?.total_ms ?? 0);
        const linTimes = results.map(r => r.linear_scan?.total_ms ?? 0);

        this.chartBenchmark = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Custom Min-Heap O(log N)",
                        data: heapTimes,
                        borderColor: "#10b981",
                        backgroundColor: "rgba(16, 185, 129, 0.15)",
                        borderWidth: 3,
                        pointRadius: 6,
                        tension: 0.15,
                        fill: true,
                    },
                    {
                        label: "Naive Sorted List O(N log N)",
                        data: sortTimes,
                        borderColor: "#f97316",
                        backgroundColor: "rgba(249, 115, 22, 0.1)",
                        borderWidth: 2,
                        pointRadius: 5,
                        tension: 0.15,
                    },
                    {
                        label: "Naive Linear Scan O(N)",
                        data: linTimes,
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239, 68, 68, 0.1)",
                        borderWidth: 2,
                        pointRadius: 5,
                        tension: 0.15,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: { boxWidth: 14, font: { weight: "600" } },
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y} ms`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Total Execution Time (ms)" },
                    },
                    x: {
                        title: { display: true, text: "Number of Patients (N)" },
                    },
                },
            },
        });
    }

    // ========================================================================
    // Patient History Modal (Singly LinkedList Visualization)
    // ========================================================================
    async showPatientHistory(patientId) {
        const modal = document.getElementById("modal-history");
        const timeline = document.getElementById("modal-timeline");
        const summary = document.getElementById("modal-patient-summary");

        modal.classList.remove("hidden");
        timeline.innerHTML = `<p class="empty-state">Loading timeline history...</p>`;
        summary.innerHTML = `<p class="empty-state">Loading patient profile...</p>`;

        try {
            const [patientRes, historyRes] = await Promise.all([
                api.getPatient(patientId),
                api.getPatientHistory(patientId),
            ]);

            const p = patientRes.data;
            const logs = historyRes.data || [];

            document.getElementById("modal-patient-name").innerText = `${p.name} (Patient #${p.id})`;

            summary.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <strong>Demographics:</strong> ${p.age} years old &bull; ${p.gender} &bull; ${p.contact || "No contact"}<br>
                        <strong>Triage Category:</strong> ${p.category} &bull; ${this.getPriorityBadge(p.priority)}<br>
                        <strong>Chief Complaint:</strong> ${this.escapeHtml(p.complaint)}
                    </div>
                    <div>
                        <span class="badge badge-status ${p.status.toLowerCase()}">${p.status}</span>
                    </div>
                </div>
            `;

            if (logs.length === 0) {
                timeline.innerHTML = `<p class="empty-state">No treatment log records found in LinkedList.</p>`;
                return;
            }

            timeline.innerHTML = logs.map(log => `
                <div class="timeline-item">
                    <div class="timeline-bullet"></div>
                    <div class="timeline-header">
                        <span class="badge badge-status ${log.status.toLowerCase()}">${log.status}</span>
                        <span class="timeline-time">${new Date(log.created_at).toLocaleString()}</span>
                    </div>
                    <div class="timeline-note">
                        ${this.escapeHtml(log.note)}
                    </div>
                </div>
            `).join("");

        } catch (err) {
            timeline.innerHTML = `<p class="empty-state" style="color: #ef4444;">Failed to load patient history: ${err.message}</p>`;
        }
    }

    closeHistoryModal() {
        document.getElementById("modal-history").classList.add("hidden");
    }

    closeModalOnBackdrop(event) {
        if (event.target.classList.contains("modal-backdrop")) {
            event.target.classList.add("hidden");
        }
    }

    // ========================================================================
    // UI Helpers
    // ========================================================================
    getPriorityBadge(priority) {
        const badges = {
            1: `<span class="badge badge-p1">&#9679; Critical (1)</span>`,
            2: `<span class="badge badge-p2">&#9679; Urgent (2)</span>`,
            3: `<span class="badge badge-p3">&#9679; Moderate (3)</span>`,
            4: `<span class="badge badge-p4">&#9679; Minor (4)</span>`,
        };
        return badges[priority] || `<span class="badge badge-p3">P${priority}</span>`;
    }

    showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span>${this.escapeHtml(message)}</span>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "fadeOut 0.3s forwards";
            setTimeout(() => toast.remove(), 300);
        }, 3800);
    }

    escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Instantiate global app controller
const app = new HospitalApp();
document.addEventListener("DOMContentLoaded", () => app.init());
