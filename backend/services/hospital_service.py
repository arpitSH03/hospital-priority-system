"""
Hospital Emergency Service (Singleton).

Coordinates in-memory custom Data Structures (MinHeap, LinkedList, Queue, HashMap)
with persistent MySQL storage.

In-Memory State:
- waiting_heap: MinHeap storing (priority, arrival_ts, patient_id) for patients in WAITING status.
- patients: HashMap mapping patient_id -> Patient dictionary.
- doctors: HashMap mapping doctor_id -> Doctor dictionary.
- available_doctors: Queue maintaining available doctors in FIFO rotation.
- history: HashMap mapping patient_id -> LinkedList of treatment logs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    mysql = None
    Error = Exception

from backend.database import get_db_connection
from dsa.hash_utils import HashMap
from dsa.linked_list import LinkedList
from dsa.min_heap import MinHeap
from dsa.queue import Queue


class HospitalService:
    """
    Singleton service managing the hospital emergency workflow.
    Ensures every operation updates MySQL and synchronized in-memory custom data structures.
    """

    _instance: Optional["HospitalService"] = None

    def __new__(cls) -> "HospitalService":
        if cls._instance is None:
            cls._instance = super(HospitalService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        # In-memory DSA instances
        self.waiting_heap: MinHeap = MinHeap()
        self.patients: HashMap = HashMap(initial_capacity=32)
        self.doctors: HashMap = HashMap(initial_capacity=16)
        self.available_doctors: Queue = Queue()
        self.history: HashMap = HashMap(initial_capacity=32)

        self._initialized = True

    # -------------------------------------------------------------------------
    # Database Synchronization & Rehydration
    # -------------------------------------------------------------------------

    def load_from_db(self) -> None:
        """
        Rebuilds the entire in-memory state from the MySQL database on startup.
        
        - Doctors: Populates doctors HashMap; free doctors (is_available=True, current_patient_id=None)
          are enqueued into the available_doctors FIFO Queue.
        - Patients: Populates patients HashMap; WAITING patients are inserted into the waiting MinHeap.
        - Treatment Log: Populates history HashMap with a LinkedList for each patient.
        """
        # Reset current in-memory structures
        self.waiting_heap = MinHeap()
        self.patients = HashMap(initial_capacity=32)
        self.doctors = HashMap(initial_capacity=16)
        self.available_doctors = Queue()
        self.history = HashMap(initial_capacity=32)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # 1. Load Doctors
            cursor.execute("SELECT id, name, specialization, is_available, current_patient_id FROM doctors ORDER BY id ASC")
            db_doctors = cursor.fetchall()
            for doc in db_doctors:
                # Convert boolean
                doc["is_available"] = bool(doc["is_available"])
                self.doctors[doc["id"]] = doc
                if doc["is_available"] and doc["current_patient_id"] is None:
                    self.available_doctors.enqueue(doc["id"])

            # 2. Load Patients
            cursor.execute("""
                SELECT id, name, age, gender, contact, complaint, category, priority, 
                       status, arrival_time, treatment_start, discharge_time, assigned_doctor_id 
                FROM patients ORDER BY id ASC
            """)
            db_patients = cursor.fetchall()
            for p in db_patients:
                pid = p["id"]
                self.patients[pid] = p
                self.history[pid] = LinkedList()

                if p["status"] == "WAITING":
                    arr_time = p.get("arrival_time")
                    if arr_time is None:
                        arr_time = datetime.now()
                        p["arrival_time"] = arr_time
                    ts = arr_time.timestamp() if isinstance(arr_time, datetime) else datetime.fromisoformat(str(arr_time)).timestamp()
                    self.waiting_heap.insert(p["priority"], ts, pid)

            # 3. Load Treatment Logs into Patient History Linked Lists
            cursor.execute("SELECT id, patient_id, status, note, created_at FROM treatment_log ORDER BY id ASC")
            db_logs = cursor.fetchall()
            for log in db_logs:
                pid = log["patient_id"]
                if not self.history.contains(pid):
                    self.history[pid] = LinkedList()
                self.history[pid].append(log)

            print(f"[HospitalService] Rehydrated from DB: {self.patients.size()} patients ({self.waiting_heap.size()} waiting), "
                  f"{self.doctors.size()} doctors ({self.available_doctors.size()} available in queue).")

        except Error as e:
            print(f"[HospitalService Error] Failed to load data from MySQL: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # Helper Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def map_category_to_priority(category: str, explicit_priority: Optional[int] = None) -> int:
        """
        Maps a triage category or explicit input to priority integer:
        1 = Critical, 2 = Urgent, 3 = Moderate, 4 = Minor.
        """
        if explicit_priority in [1, 2, 3, 4]:
            return explicit_priority

        cat_upper = str(category).strip().upper()
        if "CRITICAL" in cat_upper or "CARDIAC" in cat_upper or "ARREST" in cat_upper:
            return 1
        elif "URGENT" in cat_upper or "TRAUMA" in cat_upper or "RESPIRATORY" in cat_upper:
            return 2
        elif "MODERATE" in cat_upper or "SURGERY" in cat_upper or "ORTHOPEDIC" in cat_upper:
            return 3
        elif "MINOR" in cat_upper or "GENERAL" in cat_upper:
            return 4
        return 3  # Default Moderate

    # -------------------------------------------------------------------------
    # Patient Workflow Methods
    # -------------------------------------------------------------------------

    def register_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registers a new emergency patient.
        Computes priority, writes to MySQL (patients + treatment_log),
        pushes into the Min-Heap, stores in HashMap, and appends to the history LinkedList.
        """
        category = data.get("category", "General")
        explicit_priority = data.get("priority")
        priority = self.map_category_to_priority(category, explicit_priority)
        arrival_time = datetime.now()

        patient_record = {
            "name": str(data.get("name", "")).strip(),
            "age": int(data.get("age", 0)),
            "gender": str(data.get("gender", "Other")),
            "contact": str(data.get("contact", "")),
            "complaint": str(data.get("complaint", "")),
            "category": category,
            "priority": priority,
            "status": "WAITING",
            "arrival_time": arrival_time,
            "treatment_start": None,
            "discharge_time": None,
            "assigned_doctor_id": None,
        }

        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        try:
            # 1. Insert into patients table
            cursor.execute("""
                INSERT INTO patients 
                (name, age, gender, contact, complaint, category, priority, status, arrival_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                patient_record["name"], patient_record["age"], patient_record["gender"],
                patient_record["contact"], patient_record["complaint"], patient_record["category"],
                patient_record["priority"], patient_record["status"], patient_record["arrival_time"]
            ))
            patient_id = cursor.lastrowid
            patient_record["id"] = patient_id

            # 2. Insert initial log entry
            log_note = f"Registered in ER. Assigned Priority {priority} based on '{category}' triage."
            cursor.execute("""
                INSERT INTO treatment_log (patient_id, status, note, created_at)
                VALUES (%s, %s, %s, %s)
            """, (patient_id, "WAITING", log_note, arrival_time))
            log_id = cursor.lastrowid

            conn.commit()

            # 3. Synchronize in-memory structures
            self.patients[patient_id] = patient_record
            arrival_ts = arrival_time.timestamp()
            self.waiting_heap.insert(priority, arrival_ts, patient_id)

            if not self.history.contains(patient_id):
                self.history[patient_id] = LinkedList()
            self.history[patient_id].append({
                "id": log_id,
                "patient_id": patient_id,
                "status": "WAITING",
                "note": log_note,
                "created_at": arrival_time,
            })

            return patient_record

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def update_priority(self, patient_id: int, new_priority: int) -> Dict[str, Any]:
        """
        Updates the triage priority of a WAITING patient.
        Performs O(log n) update on Min-Heap, logs to treatment_log, and updates MySQL.
        """
        if not self.patients.contains(patient_id):
            raise KeyError(f"Patient with ID {patient_id} does not exist.")

        patient = self.patients[patient_id]
        if patient["status"] != "WAITING":
            raise ValueError(f"Cannot update priority for patient {patient_id}; status is '{patient['status']}', expected 'WAITING'.")

        if new_priority not in [1, 2, 3, 4]:
            raise ValueError("Priority must be between 1 (Critical) and 4 (Minor).")

        old_priority = patient["priority"]
        if old_priority == new_priority:
            return patient

        now = datetime.now()
        note = f"Triage priority updated from {old_priority} to {new_priority}."

        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("UPDATE patients SET priority = %s WHERE id = %s", (new_priority, patient_id))
            cursor.execute("""
                INSERT INTO treatment_log (patient_id, status, note, created_at)
                VALUES (%s, %s, %s, %s)
            """, (patient_id, "WAITING", note, now))
            log_id = cursor.lastrowid
            conn.commit()

            # Update in-memory
            patient["priority"] = new_priority
            self.waiting_heap.update_priority(patient_id, new_priority)

            if not self.history.contains(patient_id):
                self.history[patient_id] = LinkedList()
            self.history[patient_id].append({
                "id": log_id,
                "patient_id": patient_id,
                "status": "WAITING",
                "note": note,
                "created_at": now,
            })

            return patient

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_waiting_list(self) -> List[Dict[str, Any]]:
        """
        Returns the sorted list of currently waiting patients directly from the Min-Heap.
        Calculates live waiting minutes for each patient.
        """
        sorted_tuples = self.waiting_heap.to_sorted_list()
        now = datetime.now()
        result = []

        for rank, (priority, arrival_ts, patient_id) in enumerate(sorted_tuples, start=1):
            if not self.patients.contains(patient_id):
                continue
            p = dict(self.patients[patient_id])
            arr_time = p["arrival_time"]
            if isinstance(arr_time, datetime):
                waiting_mins = round((now - arr_time).total_seconds() / 60.0, 1)
            else:
                dt = datetime.fromisoformat(str(arr_time))
                waiting_mins = round((now - dt).total_seconds() / 60.0, 1)

            p["queue_rank"] = rank
            p["waiting_minutes"] = max(0.0, waiting_mins)
            result.append(p)

        return result

    def allocate_doctor(self) -> Dict[str, Any]:
        """
        Allocates the next highest priority patient from Min-Heap to the next available doctor in Queue.
        Performs transactional DB update and synchronizes in-memory heap, queue, and hashmaps.
        """
        if self.waiting_heap.is_empty():
            return {"success": False, "message": "No patients currently waiting in the emergency queue."}

        # Evict any stale or unavailable doctors from the front of the queue
        while not self.available_doctors.is_empty():
            doc_id = self.available_doctors.peek()
            if self.doctors.contains(doc_id):
                doc = self.doctors[doc_id]
                if doc.get("is_available") and doc.get("current_patient_id") is None:
                    break
            self.available_doctors.dequeue()

        if self.available_doctors.is_empty():
            return {"success": False, "message": "No doctors are currently available in the queue."}

        # Peek highest priority patient and front doctor
        min_tuple = self.waiting_heap.peek()
        patient_id = min_tuple[2]
        doc_id = self.available_doctors.peek()

        patient = self.patients[patient_id]
        doctor = self.doctors[doc_id]
        treatment_start = datetime.now()
        note = f"Assigned to {doctor['name']} ({doctor['specialization']}). Emergency treatment started."

        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        try:
            # 1. Update patient in DB
            cursor.execute("""
                UPDATE patients 
                SET status = 'IN_TREATMENT', assigned_doctor_id = %s, treatment_start = %s 
                WHERE id = %s
            """, (doc_id, treatment_start, patient_id))

            # 2. Update doctor in DB
            cursor.execute("""
                UPDATE doctors 
                SET is_available = FALSE, current_patient_id = %s 
                WHERE id = %s
            """, (patient_id, doc_id))

            # 3. Add treatment log
            cursor.execute("""
                INSERT INTO treatment_log (patient_id, status, note, created_at)
                VALUES (%s, 'IN_TREATMENT', %s, %s)
            """, (patient_id, note, treatment_start))
            log_id = cursor.lastrowid

            conn.commit()

            # 4. Update in-memory state after successful commit
            self.waiting_heap.extract_min()
            self.available_doctors.dequeue()

            patient["status"] = "IN_TREATMENT"
            patient["assigned_doctor_id"] = doc_id
            patient["treatment_start"] = treatment_start

            doctor["is_available"] = False
            doctor["current_patient_id"] = patient_id

            if not self.history.contains(patient_id):
                self.history[patient_id] = LinkedList()
            self.history[patient_id].append({
                "id": log_id,
                "patient_id": patient_id,
                "status": "IN_TREATMENT",
                "note": note,
                "created_at": treatment_start,
            })

            return {
                "success": True,
                "message": f"Assigned Patient #{patient_id} ({patient['name']}) to {doctor['name']}.",
                "patient": patient,
                "doctor": doctor,
            }

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def update_status(self, patient_id: int, status: str, note: str) -> Dict[str, Any]:
        """
        Updates a patient's status and records a treatment note.
        Validates clinical state transitions (WAITING -> IN_TREATMENT -> DISCHARGED).
        """
        if not self.patients.contains(patient_id):
            raise KeyError(f"Patient with ID {patient_id} does not exist.")

        status_upper = status.strip().upper()
        allowed_statuses = ["WAITING", "IN_TREATMENT", "DISCHARGED"]
        if status_upper not in allowed_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(allowed_statuses)}.")

        patient = self.patients[patient_id]
        current_status = patient.get("status", "WAITING")

        # DISCHARGED is a terminal state
        if current_status == "DISCHARGED":
            raise ValueError(f"Cannot update status for Patient #{patient_id}; patient is already DISCHARGED.")

        # If discharging, delegate to discharge_patient to free doctor & auto-allocate
        if status_upper == "DISCHARGED":
            return self.discharge_patient(patient_id)

        # Disallow reverting from IN_TREATMENT back to WAITING
        if current_status == "IN_TREATMENT" and status_upper == "WAITING":
            raise ValueError("Invalid transition: Cannot revert patient from 'IN_TREATMENT' back to 'WAITING'. Discharge the patient instead.")

        # Disallow manually jumping to IN_TREATMENT without an assigned doctor
        if current_status == "WAITING" and status_upper == "IN_TREATMENT":
            if not patient.get("assigned_doctor_id"):
                raise ValueError("Invalid transition: Cannot set status to 'IN_TREATMENT' without an assigned doctor. Use allocate_doctor() instead.")
        now = datetime.now()

        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("UPDATE patients SET status = %s WHERE id = %s", (status_upper, patient_id))
            cursor.execute("""
                INSERT INTO treatment_log (patient_id, status, note, created_at)
                VALUES (%s, %s, %s, %s)
            """, (patient_id, status_upper, note, now))
            log_id = cursor.lastrowid
            conn.commit()

            patient["status"] = status_upper
            if not self.history.contains(patient_id):
                self.history[patient_id] = LinkedList()
            self.history[patient_id].append({
                "id": log_id,
                "patient_id": patient_id,
                "status": status_upper,
                "note": note,
                "created_at": now,
            })

            return patient

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def discharge_patient(self, patient_id: int) -> Dict[str, Any]:
        """
        Discharges a patient, frees the assigned doctor, enqueues the doctor back into FIFO Queue,
        and automatically calls allocate_doctor() once to treat the next waiting patient.
        """
        if not self.patients.contains(patient_id):
            raise KeyError(f"Patient with ID {patient_id} does not exist.")

        patient = self.patients[patient_id]
        if patient["status"] == "DISCHARGED":
            raise ValueError(f"Patient #{patient_id} is already discharged.")

        discharge_time = datetime.now()
        doc_id = patient.get("assigned_doctor_id")
        note = "Patient successfully discharged from emergency care."

        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        try:
            # 1. Update patient in DB
            cursor.execute("""
                UPDATE patients 
                SET status = 'DISCHARGED', discharge_time = %s 
                WHERE id = %s
            """, (discharge_time, patient_id))

            # 2. Free doctor in DB if assigned
            if doc_id:
                cursor.execute("""
                    UPDATE doctors 
                    SET is_available = TRUE, current_patient_id = NULL 
                    WHERE id = %s
                """, (doc_id,))

            # 3. Log discharge
            cursor.execute("""
                INSERT INTO treatment_log (patient_id, status, note, created_at)
                VALUES (%s, 'DISCHARGED', %s, %s)
            """, (patient_id, note, discharge_time))
            log_id = cursor.lastrowid

            conn.commit()

            # 4. Synchronize in-memory structures
            patient["status"] = "DISCHARGED"
            patient["discharge_time"] = discharge_time

            # If patient was in waiting heap (e.g. discharged before treatment started)
            if self.waiting_heap.contains(patient_id):
                self.waiting_heap.remove(patient_id)

            if doc_id and self.doctors.contains(doc_id):
                doc = self.doctors[doc_id]
                doc["is_available"] = True
                doc["current_patient_id"] = None
                if not self.available_doctors.contains(doc_id):
                    self.available_doctors.enqueue(doc_id)

            if not self.history.contains(patient_id):
                self.history[patient_id] = LinkedList()
            self.history[patient_id].append({
                "id": log_id,
                "patient_id": patient_id,
                "status": "DISCHARGED",
                "note": note,
                "created_at": discharge_time,
            })

            # Auto-call allocate_doctor() once to pick up the next waiting patient
            auto_alloc = None
            if not self.waiting_heap.is_empty() and not self.available_doctors.is_empty():
                auto_alloc = self.allocate_doctor()

            return {
                "patient": patient,
                "message": f"Patient #{patient_id} ({patient['name']}) discharged. Doctor freed.",
                "auto_allocation": auto_alloc,
            }

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def apply_aging(self, minutes_threshold: int = 30) -> Dict[str, Any]:
        """
        Escalates priority by 1 for any WAITING patient with priority > 1
        who has waited longer than minutes_threshold (aging boost).
        """
        now = datetime.now()
        boosted_list = []

        # Make a snapshot of heap tuples to evaluate
        waiting_tuples = list(self.waiting_heap.heap)

        for priority, arrival_ts, patient_id in waiting_tuples:
            if not self.waiting_heap.contains(patient_id) or not self.patients.contains(patient_id):
                continue

            p = self.patients[patient_id]
            current_priority = p.get("priority", priority)
            if current_priority <= 1:
                continue  # Already at highest priority (Critical)

            arr_time = p.get("arrival_time")
            if isinstance(arr_time, datetime):
                waiting_mins = (now - arr_time).total_seconds() / 60.0
            elif arr_time:
                dt = datetime.fromisoformat(str(arr_time))
                waiting_mins = (now - dt).total_seconds() / 60.0
            else:
                waiting_mins = 0.0

            if waiting_mins >= minutes_threshold:
                new_priority = current_priority - 1
                note = f"Aging boost: Priority escalated from {current_priority} to {new_priority} after {round(waiting_mins, 1)} minutes waiting."

                conn = get_db_connection()
                conn.autocommit = False
                cursor = conn.cursor(dictionary=True)

                try:
                    cursor.execute("UPDATE patients SET priority = %s WHERE id = %s", (new_priority, patient_id))
                    cursor.execute("""
                        INSERT INTO treatment_log (patient_id, status, note, created_at)
                        VALUES (%s, 'WAITING', %s, %s)
                    """, (patient_id, note, now))
                    log_id = cursor.lastrowid
                    conn.commit()

                    # In-memory updates
                    p["priority"] = new_priority
                    self.waiting_heap.update_priority(patient_id, new_priority)

                    if not self.history.contains(patient_id):
                        self.history[patient_id] = LinkedList()
                    self.history[patient_id].append({
                        "id": log_id,
                        "patient_id": patient_id,
                        "status": "WAITING",
                        "note": note,
                        "created_at": now,
                    })

                    boosted_list.append({
                        "patient_id": patient_id,
                        "name": p["name"],
                        "old_priority": priority,
                        "new_priority": new_priority,
                        "waiting_minutes": round(waiting_mins, 1),
                    })

                except Exception as e:
                    conn.rollback()
                    print(f"[Aging Error] Could not boost patient {patient_id}: {e}")
                finally:
                    cursor.close()
                    conn.close()

        return {
            "boosted_count": len(boosted_list),
            "boosted_patients": boosted_list,
        }

    # -------------------------------------------------------------------------
    # History & Analytics
    # -------------------------------------------------------------------------

    def get_patient_history(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Returns the linear treatment timeline for a patient directly from their LinkedList.
        """
        if self.history.contains(patient_id):
            return self.history[patient_id].to_list()
        return []

    def get_report(self) -> Dict[str, Any]:
        """
        Generates comprehensive hospital KPI and DSA queue metrics.
        """
        total_patients = self.patients.size()
        now = datetime.now()

        priority_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        status_counts = {"WAITING": 0, "IN_TREATMENT": 0, "DISCHARGED": 0}

        wait_times_by_priority = {1: [], 2: [], 3: [], 4: []}

        for p in self.patients.values():
            prio = p.get("priority", 3)
            status = p.get("status", "WAITING")

            if prio in priority_counts:
                priority_counts[prio] += 1
            if status in status_counts:
                status_counts[status] += 1

            # Waiting time calculation
            arr = p.get("arrival_time")
            arr_dt = arr if isinstance(arr, datetime) else (datetime.fromisoformat(str(arr)) if arr else None)

            if arr_dt:
                t_start = p.get("treatment_start")
                if t_start:
                    start_dt = t_start if isinstance(t_start, datetime) else datetime.fromisoformat(str(t_start))
                    minutes = (start_dt - arr_dt).total_seconds() / 60.0
                elif status == "WAITING":
                    minutes = (now - arr_dt).total_seconds() / 60.0
                else:
                    minutes = 0.0

                if prio in wait_times_by_priority:
                    wait_times_by_priority[prio].append(max(0.0, minutes))

        # Compute averages
        avg_wait_times = {}
        for prio, times in wait_times_by_priority.items():
            avg_wait_times[prio] = round(sum(times) / len(times), 1) if times else 0.0

        # Doctors
        total_doctors = self.doctors.size()
        busy_doctors = sum(
            1 for d in self.doctors.values() 
            if not d.get("is_available") or d.get("current_patient_id") is not None
        )
        utilization_pct = round((busy_doctors / total_doctors * 100.0), 1) if total_doctors > 0 else 0.0

        return {
            "total_patients": total_patients,
            "currently_waiting": self.waiting_heap.size(),
            "in_treatment": status_counts["IN_TREATMENT"],
            "discharged": status_counts["DISCHARGED"],
            "priority_breakdown": {
                "1_critical": priority_counts[1],
                "2_urgent": priority_counts[2],
                "3_moderate": priority_counts[3],
                "4_minor": priority_counts[4],
            },
            "avg_wait_minutes_by_priority": {
                "1_critical": avg_wait_times[1],
                "2_urgent": avg_wait_times[2],
                "3_moderate": avg_wait_times[3],
                "4_minor": avg_wait_times[4],
            },
            "doctors": {
                "total": total_doctors,
                "busy": busy_doctors,
                "available_in_queue": self.available_doctors.size(),
                "utilization_percentage": utilization_pct,
            },
        }

    # -------------------------------------------------------------------------
    # Doctor Management
    # -------------------------------------------------------------------------

    def add_doctor(self, name: str, specialization: str) -> Dict[str, Any]:
        """
        Adds a new doctor, inserts into MySQL, updates doctors HashMap, and enqueues into FIFO Queue.
        """
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                INSERT INTO doctors (name, specialization, is_available, current_patient_id)
                VALUES (%s, %s, TRUE, NULL)
            """, (name.strip(), specialization.strip()))
            doc_id = cursor.lastrowid
            conn.commit()

            doc_record = {
                "id": doc_id,
                "name": name.strip(),
                "specialization": specialization.strip(),
                "is_available": True,
                "current_patient_id": None,
            }

            self.doctors[doc_id] = doc_record
            self.available_doctors.enqueue(doc_id)

            return doc_record

        finally:
            cursor.close()
            conn.close()

    def set_doctor_availability(self, doctor_id: int, is_available: bool) -> Dict[str, Any]:
        """
        Sets a doctor's availability status.
        Synchronizes MySQL and adds/removes from available_doctors FIFO Queue.
        """
        if not self.doctors.contains(doctor_id):
            raise KeyError(f"Doctor with ID {doctor_id} not found.")

        doc = self.doctors[doctor_id]
        if not is_available and doc.get("current_patient_id") is not None:
            raise ValueError(f"Cannot set doctor #{doctor_id} unavailable; doctor is actively treating patient #{doc['current_patient_id']}.")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("UPDATE doctors SET is_available = %s WHERE id = %s", (is_available, doctor_id))
            conn.commit()

            doc["is_available"] = is_available
            if is_available:
                if not self.available_doctors.contains(doctor_id) and doc.get("current_patient_id") is None:
                    self.available_doctors.enqueue(doctor_id)
            else:
                self.available_doctors.remove(doctor_id)

            return doc

        finally:
            cursor.close()
            conn.close()

    def list_doctors(self) -> List[Dict[str, Any]]:
        """
        Returns all doctors with their current availability and assigned patient.
        """
        return sorted(self.doctors.values(), key=lambda d: d["id"])

    def list_patients(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns all registered patients, optionally filtered by status (WAITING, IN_TREATMENT, DISCHARGED).
        """
        patients_list = self.patients.values()
        if status_filter:
            sf = status_filter.strip().upper()
            patients_list = [p for p in patients_list if p.get("status") == sf]

        return sorted(patients_list, key=lambda p: p["id"])


# Global singleton instance
hospital_service = HospitalService()
