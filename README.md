# Hospital Emergency & Patient Priority Management System

An enterprise-grade, college Data Structures & Algorithms (DSA) capstone project implementing a real-time emergency room triage and patient priority management system.

Built with **Python 3.11+**, **FastAPI**, **MySQL**, and a responsive **Vanilla HTML5/CSS3/JavaScript** frontend.

---

## 1. Problem Statement

Traditional First-Come, First-Served (FCFS) hospital intake systems are fundamentally unsuited for Emergency Departments (ED). In acute clinical settings, medical severity must strictly dictate treatment order rather than arrival time; a patient presenting with an acute myocardial infarction (heart attack) cannot wait behind a patient with a minor ankle sprain.

Furthermore, naive software implementations—such as continuously re-sorting an array upon each arrival ($O(N \log N)$ or $O(N^2)$) or scanning linearly to extract the highest-urgency patient ($O(N)$)—create unacceptable algorithmic latency under mass-casualty intake.

This project solves both problems:
1. **Algorithmic Efficiency:** Implements an in-memory **Indexed Min-Heap** with a position hash map that achieves $O(\log N)$ patient insertions, $O(\log N)$ extractions, and $O(\log N)$ priority re-triaging, alongside a linked-list **FIFO Queue** for fair physician allocation and **Singly Linked Lists** for immutable patient treatment timelines.
2. **Clinical Reliability:** Couples custom in-memory data structures with transactional **MySQL** database persistence, ensuring zero patient loss upon system restarts while eliminating queue starvation via an automated **Aging Boost** algorithm.

---

## 2. Key Features

- **Triage Level Hierarchy:** Standardized 4-tier medical urgency:
  - `Priority 1 (Critical)`: Immediate resuscitation, cardiac arrest, polytrauma.
  - `Priority 2 (Urgent)`: Severe dyspnea, acute appendicitis, high risk of deterioration.
  - `Priority 3 (Moderate)`: Closed fractures, deep lacerations, severe distress.
  - `Priority 4 (Minor)`: Sprains, superficial wounds, seasonal viral syndromes.
- **Fair FIFO Tie-Breaking:** Patients sharing the same priority are ordered strictly by arrival timestamp `(priority, arrival_timestamp)`.
- **Dynamic Doctor Allocation:** Pulls the highest-priority patient from the Min-Heap and pairs them with the front on-duty physician from the linked-list FIFO Queue.
- **Discharge & Immediate Auto-Allocation:** Discharging a patient frees their attending physician, enqueues the doctor back into rotation, and automatically triggers allocation for the next waiting emergency patient.
- **Starvation Prevention (Aging Boost):** Automatically escalates the priority of patients waiting longer than a configurable threshold (e.g. 30 minutes) by $1$ tier ($4 \to 3 \to 2 \to 1$).
- **Granular Treatment History Timeline:** Complete patient audit trail stored linearly in a custom Singly Linked List and inspectable via an interactive modal.
- **Empirical DSA Benchmark Suite (`/api/benchmark`):** Compares our Min-Heap against naive Sorted Lists and Linear Scans for $N = 1,000, 5,000, 10,000$ operations, displayed via interactive Chart.js line charts.
- **Operational KPI Dashboard:** Auto-refreshing metrics showing waiting counts, active treatments, physician roster utilization, and average wait time per triage priority.

---

## 3. Tech Stack

- **Backend Framework:** FastAPI (Python 3.11+)
- **ASGI Server:** Uvicorn (standard event loop)
- **Database:** MySQL 8.0+ via `mysql-connector-python`
- **Data Validation & Envelopes:** Pydantic v2
- **Data Structures Layer:** Hand-written pure Python (no `heapq`, `queue.PriorityQueue`, or `collections.deque`)
- **Frontend:** Vanilla HTML5, CSS3 (Medical Blue/White Theme), Vanilla JavaScript (Fetch API)
- **Data Visualization:** Chart.js (CDN)
- **Testing Suite:** Pytest

---

## 4. System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend (Single Page Application)"]
        UI["Web Browser (HTML5 / CSS3 / Vanilla JS)"]
        Charts["Chart.js Analytics & Live Benchmark"]
    end

    subgraph API ["FastAPI Backend Layer (main.py)"]
        RouterPatients["/api/patients (Triage & History)"]
        RouterQueue["/api/queue (Heap, Allocate, Aging)"]
        RouterDoctors["/api/doctors (Roster & Availability)"]
        RouterReports["/api/reports & /api/benchmark"]
    end

    subgraph Service ["Singleton HospitalService (hospital_service.py)"]
        direction TB
        Orchestrator["HospitalService Coordinator"]
    end

    subgraph Memory ["Hand-Written In-Memory DSA Layer"]
        Heap["Indexed Min-Heap (min_heap.py)<br/>Key: (priority, arrival_ts, id)<br/>pos map: patient_id -> index"]
        Queue["FIFO Queue (queue.py)<br/>Head/Tail Pointers for Free Doctors"]
        HistList["Singly LinkedList (linked_list.py)<br/>Patient Treatment Timeline"]
        HashMap["Separate Chaining HashMap (hash_utils.py)<br/>patient_id -> Patient | doc_id -> Doctor"]
    end

    subgraph Persistence ["Persistent Storage Layer"]
        MySQL[("MySQL 8.0+ Database (hospital_db)")]
        T_Patients[("patients table")]
        T_Doctors[("doctors table")]
        T_Log[("treatment_log table")]
    end

    UI -->|JSON HTTP / REST| API
    API --> Orchestrator
    Orchestrator <-->|O(1) & O(log N) Reads/Updates| Memory
    Orchestrator <-->|Transactional Sync & Load| Persistence
    MySQL --- T_Patients
    MySQL --- T_Doctors
    MySQL --- T_Log
```

---

## 5. DSA Implementation & Complexity Breakdown

Every core data structure is implemented by hand without external standard libraries.

| Data Structure | Module | System Purpose | Insert Complexity | Extract Complexity | Update Complexity | Space Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Indexed Min-Heap** | `dsa/min_heap.py` | Priority triage queue with tie-breaking | $O(\log N)$ | $O(\log N)$ | $O(\log N)$ via `pos` map | $O(N)$ |
| **FIFO Queue** | `dsa/queue.py` | Available doctor rotation | $O(1)$ | $O(1)$ | $O(N)$ arbitrary removal | $O(N)$ |
| **Singly Linked List** | `dsa/linked_list.py` | Linear patient treatment timeline | $O(1)$ append / prepend | $O(1)$ head removal | $O(N)$ search / find | $O(N)$ |
| **Custom HashMap** | `dsa/hash_utils.py` | $O(1)$ lookups for doctors & patients | $O(1)$ amortized | $O(1)$ remove | $O(1)$ lookup | $O(N)$ (0.75 load factor) |

### Empirical Performance Comparison ($N = 10,000$ Patients)

Empirically measured using Python's `time.perf_counter()` via `/api/benchmark`:

| Implementation Approach | Insertion Time ($N=10k$) | Extraction Time ($N=10k$) | Total Time ($N=10k$) | Speedup vs Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **Custom Indexed Min-Heap** | **18.83 ms** | **173.76 ms** | **192.59 ms** | **1.0x (Fastest)** |
| **Naive Sorted List** *(Re-sort on insert)* | 1,930.77 ms | 300.95 ms | 2,231.72 ms | **~11.6x Slower** |
| **Naive Linear Scan** *(Unsorted list)* | 0.56 ms | 11,639.37 ms | 11,639.93 ms | **~60.4x Slower** |

---

## 6. Folder Structure

```text
hospital-priority-system/
├── backend/
│   ├── __init__.py
│   ├── config.py                 # Loads .env configurations & paths
│   ├── database.py               # MySQL connection helper and schema executor
│   ├── main.py                   # FastAPI app, lifespan setup, router registration, static mounting
│   ├── models.py                 # Pydantic validation schemas & API response envelope
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── benchmark.py          # GET /api/benchmark performance test
│   │   ├── doctors.py            # POST/GET/PUT /api/doctors roster management
│   │   ├── patients.py           # Patient CRUD, priority update, status, discharge, history
│   │   ├── queue.py              # GET /api/queue, POST allocate, POST apply-aging
│   │   └── reports.py            # GET /api/reports/summary operational metrics
│   └── services/
│       ├── __init__.py
│       └── hospital_service.py   # Singleton tying in-memory DSA with MySQL transactions
├── dsa/
│   ├── __init__.py
│   ├── hash_utils.py             # Custom separate-chaining HashMap with dynamic resizing
│   ├── linked_list.py            # Node and singly LinkedList with head and tail pointers
│   ├── min_heap.py               # Array-based binary MinHeap with position map
│   └── queue.py                  # FIFO Queue backed by custom LinkedList
├── frontend/
│   ├── app.js                    # Vanilla JS SPA controller, API client, Chart.js logic
│   ├── index.html                # 5-section UI (Dashboard, Register, Queue, Doctors, Reports)
│   └── style.css                 # Medical blue & white theme, priority color-coding
├── sql/
│   └── schema.sql                # MySQL DDL schema, indexes, and initial seed data
├── tests/
│   ├── __init__.py
│   ├── api_tests.http            # HTTP request test script for REST Client extensions
│   ├── test_api_flow.py          # End-to-end integration test of the emergency workflow
│   ├── test_benchmark.py         # Automated unit test for benchmark endpoint
│   ├── test_dsa.py               # 20 pure unit tests for all custom DSA implementations
│   ├── test_frontend_serving.py  # Tests verifying static asset serving
│   └── test_service.py           # 10 comprehensive tests for HospitalService & edge cases
├── .env.example                  # Environment variable configuration template
├── .gitignore                    # Git ignore file for Python, venv, and caches
├── requirements.txt              # Project Python dependencies
└── README.md                     # Capstone documentation
```

---

## 7. Database Schema Summary

The MySQL schema is defined in [sql/schema.sql](file:///d:/hospital%20emergency%20A6/hospital-priority-system/sql/schema.sql):

### 1. `doctors`
- `id` (INT PK AUTO_INCREMENT): Primary key.
- `name` (VARCHAR(100) NOT NULL): Full physician name.
- `specialization` (VARCHAR(100) NOT NULL): Clinical department.
- `is_available` (BOOLEAN DEFAULT TRUE): Availability status.
- `current_patient_id` (INT NULL): ID of the patient actively receiving treatment.

### 2. `patients`
- `id` (INT PK AUTO_INCREMENT): Primary key.
- `name` (VARCHAR(100) NOT NULL): Patient full name.
- `age` (INT NOT NULL): Age in years.
- `gender` (VARCHAR(10) NOT NULL): Patient gender.
- `contact` (VARCHAR(20) NOT NULL): Emergency contact telephone.
- `complaint` (TEXT NOT NULL): Chief medical complaint and symptoms.
- `category` (VARCHAR(50) NOT NULL): Triage classification.
- `priority` (TINYINT NOT NULL): Priority level (1=Critical, 2=Urgent, 3=Moderate, 4=Minor).
- `status` (ENUM('WAITING', 'IN_TREATMENT', 'DISCHARGED') DEFAULT 'WAITING').
- `arrival_time` (DATETIME NOT NULL): Check-in timestamp.
- `treatment_start` (DATETIME NULL): Timestamp when doctor allocation occurred.
- `discharge_time` (DATETIME NULL): Timestamp when treatment completed.
- `assigned_doctor_id` (INT NULL FK -> doctors.id).

### 3. `treatment_log`
- `id` (INT PK AUTO_INCREMENT): Primary key.
- `patient_id` (INT NOT NULL FK -> patients.id ON DELETE CASCADE).
- `status` (VARCHAR(50) NOT NULL): Recorded state (`WAITING`, `IN_TREATMENT`, `DISCHARGED`).
- `note` (TEXT NOT NULL): Clinical treatment note or priority adjustment reason.
- `created_at` (DATETIME DEFAULT CURRENT_TIMESTAMP): Event timestamp.

**Indexes:**
- `CREATE INDEX idx_patients_status_priority ON patients(status, priority);`
- `CREATE INDEX idx_treatment_log_patient_id ON treatment_log(patient_id);`

---

## 8. Full API Specification

All endpoints return a standardized JSON envelope: `{ "success": bool, "data": Any, "message": str }`.

| Category | Method | Endpoint | Request Body | Description |
| :--- | :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | None | Health check endpoint |
| **Patients** | `POST` | `/api/patients` | `{ name, age, gender, contact, complaint, category, [priority] }` | Register patient & insert to Min-Heap |
| **Patients** | `GET` | `/api/patients` | Query: `?status=WAITING` | List all patients (optional status filter) |
| **Patients** | `GET` | `/api/patients/{id}` | None | Retrieve single patient details |
| **Patients** | `PUT` | `/api/patients/{id}/priority` | `{ priority: 1..4 }` | Update triage priority in Min-Heap |
| **Patients** | `PUT` | `/api/patients/{id}/status` | `{ status, note }` | Update patient clinical status & log |
| **Patients** | `POST` | `/api/patients/{id}/discharge` | None | Discharge patient, free doctor, auto-allocate next |
| **Patients** | `GET` | `/api/patients/{id}/history` | None | Get patient timeline from custom LinkedList |
| **Queue** | `GET` | `/api/queue` | None | Get sorted emergency queue with waiting minutes |
| **Queue** | `POST` | `/api/queue/allocate` | None | Pair next Min-Heap patient with next FIFO doctor |
| **Queue** | `POST` | `/api/queue/apply-aging` | `{ threshold_minutes: 30 }` | Run starvation prevention priority boost |
| **Doctors** | `POST` | `/api/doctors` | `{ name, specialization }` | Add doctor to roster and FIFO Queue |
| **Doctors** | `GET` | `/api/doctors` | None | List doctors, current status, and active patient |
| **Doctors** | `PUT` | `/api/doctors/{id}/availability` | `{ is_available: bool }` | Toggle on-duty availability |
| **Reports** | `GET` | `/api/reports/summary` | None | Hospital operational KPIs & queue metrics |
| **Benchmark** | `GET` | `/api/benchmark` | Query: `?sizes=1000,5000,10000` | Run empirical Min-Heap vs Naive benchmark |

---

## 9. Setup & Installation Guide

### Prerequisites
- Python 3.11+
- MySQL Server 8.0+
- Git

### Step-by-Step Installation

```powershell
# 1. Clone the repository
git clone https://github.com/your-username/hospital-priority-system.git
cd hospital-priority-system

# 2. Set up Python virtual environment
python -m venv venv

# In Windows PowerShell:
.\venv\Scripts\Activate.ps1
# (Or in CMD):
# .\venv\Scripts\activate.bat

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

Edit `.env` with your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=hospital_db
```

### 5. Initialize MySQL Database
```powershell
mysql -u root -p < sql/schema.sql
```
*(Alternatively, FastAPI's startup event will auto-execute `sql/schema.sql` on first run).*

### 6. Run the Application
```powershell
uvicorn backend.main:app --reload
```

- **Web Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Docs (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 7. Run Automated Tests
```powershell
python -m pytest tests/ -v
```
Output:
```text
======================== 34 passed in 2.05s ========================
```

---

## 10. Application Screenshots

*(Screenshots can be placed in `docs/screenshots/`)*

| View | Screenshot Placeholder |
| :--- | :--- |
| **Dashboard** | `![Dashboard](docs/screenshots/dashboard.png)` |
| **Patient Registration & Triage** | `![Registration](docs/screenshots/registration.png)` |
| **Color-Coded Emergency Queue** | `![Emergency Queue](docs/screenshots/queue.png)` |
| **Doctor Roster & Assignments** | `![Doctor Roster](docs/screenshots/doctors.png)` |
| **Analytics & DSA Benchmark** | `![Reports & Benchmark](docs/screenshots/benchmark.png)` |
| **LinkedList Patient Timeline Modal** | `![Patient History Timeline](docs/screenshots/history_modal.png)` |

---

## 11. Team Members & Individual Contributions

| Name | Role / Area | Key Contributions |
| :--- | :--- | :--- |
| **[Student 1 Name]** | Project Lead & Backend Architect | Designed FastAPI architecture, database schema, and `HospitalService` coordinator. |
| **[Student 2 Name]** | DSA Specialist | Hand-wrote `MinHeap` with position map, `LinkedList`, `Queue`, and `HashMap`. |
| **[Student 3 Name]** | Frontend Developer | Implemented Single Page Application, color-coded tables, Chart.js graphs, and modal. |
| **[Student 4 Name]** | QA & Empirical Benchmarking | Developed 34 unit & integration tests and implemented the `/api/benchmark` suite. |

---

## 12. Future Scope

1. **AI-Driven Clinical Triage:** Integrate a lightweight NLP model to analyze patient complaints and vitals (blood pressure, SpO2, heart rate) to recommend triage categories automatically.
2. **Distributed Multi-Hospital Queuing:** Implement Redis-backed distributed locks and WebSocket events for multi-hospital regional ER coordination.
3. **Automated Patient SMS Updates:** Integrate Twilio or SMS gateways to alert patient relatives on live queue status changes and doctor allocation.
4. **Bed & Trauma Bay Allocation:** Extend the Min-Heap allocation engine to assign specialized resuscitation bays, ICU beds, and ventilators.
5. **Ambulance Telemetry Integration:** Allow inbound emergency paramedics to pre-register patients and place them into the triage Min-Heap prior to hospital arrival.
