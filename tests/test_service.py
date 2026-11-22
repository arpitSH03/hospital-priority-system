"""
Comprehensive Unit Tests for HospitalService.

Covers:
1. Registration priority mapping (category heuristics & explicit overrides).
2. Allocation order (priority ordering and arrival timestamp tie-breaking).
3. No allocation when no doctor is free (returns graceful message).
4. No allocation when queue is empty (returns graceful message).
5. Duplicate allocate calls handling without state corruption.
6. Discharge frees doctor and triggers auto-allocation of next waiting patient.
7. Priority update reordering within the Indexed Min-Heap.
8. Aging boost escalation and boundary checks (ceiling at Priority 1).
9. Invalid state transitions (discharged patients, non-waiting priority updates, invalid statuses).
10. Server restart state rebuild from MySQL (doctors, waiting heap, treatment logs).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

from backend.services.hospital_service import HospitalService


@pytest.fixture
def mock_db():
    """Provides a mocked MySQL connection and cursor."""
    with patch("backend.services.hospital_service.get_db_connection") as mock_conn_fn:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_fn.return_value = conn
        yield {"conn": conn, "cursor": cursor}


@pytest.fixture
def service(mock_db):
    """Provides a fresh, isolated HospitalService instance."""
    # Reset singleton state
    srv = HospitalService()
    srv._initialized = False
    srv.__init__()
    return srv


# ============================================================================
# 1. Registration Priority Mapping
# ============================================================================

def test_registration_priority_mapping(service, mock_db):
    """Verify that triage categories correctly map to medical priorities 1 to 4."""
    cursor = mock_db["cursor"]

    categories = [
        ("Critical Cardiac Arrest", 1),
        ("Severe Trauma Injury", 2),
        ("Orthopedic Arm Fracture", 3),
        ("Minor Ankle Sprain", 4),
        ("Unknown Symptom", 3),  # Default fallback
    ]

    for idx, (cat, expected_prio) in enumerate(categories, start=1):
        cursor.lastrowid = idx
        p = service.register_patient({
            "name": f"Patient_{idx}",
            "age": 30,
            "gender": "Male",
            "complaint": "Testing triage",
            "category": cat,
        })
        assert p["priority"] == expected_prio
        assert service.waiting_heap.contains(idx)

    # Test explicit priority override
    cursor.lastrowid = 99
    explicit_p = service.register_patient({
        "name": "Patient_Explicit",
        "age": 45,
        "complaint": "Explicit Priority Test",
        "category": "Minor",
        "priority": 1,  # Override Minor to Critical
    })
    assert explicit_p["priority"] == 1


# ============================================================================
# 2. Allocation Order (Priority & Timestamp FIFO Tie-Break)
# ============================================================================

def test_allocation_order(service, mock_db):
    """Verify that patients are allocated strictly by urgency, with arrival time tie-breaking."""
    # Add two doctors to roster
    service.doctors[1] = {"id": 1, "name": "Dr. House", "specialization": "Diagnostics", "is_available": True, "current_patient_id": None}
    service.available_doctors.enqueue(1)
    service.doctors[2] = {"id": 2, "name": "Dr. Chase", "specialization": "ER", "is_available": True, "current_patient_id": None}
    service.available_doctors.enqueue(2)

    now = datetime.now()
    # P1: Urgent (Priority 2, arrived earliest)
    # P2: Critical (Priority 1, arrived later)
    # P3: Critical (Priority 1, arrived earlier than P2)
    p_data = [
        (101, "P_Urgent", 2, now - timedelta(minutes=30)),
        (102, "P_Crit_Late", 1, now - timedelta(minutes=10)),
        (103, "P_Crit_Early", 1, now - timedelta(minutes=20)),
    ]

    for pid, name, prio, arr in p_data:
        service.patients[pid] = {
            "id": pid, "name": name, "priority": prio, "status": "WAITING",
            "arrival_time": arr, "assigned_doctor_id": None, "treatment_start": None,
        }
        service.waiting_heap.insert(prio, arr.timestamp(), pid)

    # Allocation 1: Must pick P_Crit_Early (Priority 1, earlier arrival) -> Dr. House
    alloc1 = service.allocate_doctor()
    assert alloc1["success"] is True
    assert alloc1["patient"]["id"] == 103
    assert alloc1["doctor"]["id"] == 1

    # Allocation 2: Must pick P_Crit_Late (Priority 1, later arrival) -> Dr. Chase
    alloc2 = service.allocate_doctor()
    assert alloc2["success"] is True
    assert alloc2["patient"]["id"] == 102
    assert alloc2["doctor"]["id"] == 2


# ============================================================================
# 3. No Allocation When No Doctor Is Free
# ============================================================================

def test_no_allocation_when_no_doctor_is_free(service):
    """Verify allocate_doctor returns success=False without error when all doctors are busy."""
    service.doctors[1] = {"id": 1, "name": "Dr. Busy", "specialization": "Surgery", "is_available": False, "current_patient_id": 99}
    # available_doctors queue is empty

    service.patients[101] = {"id": 101, "name": "Waiting Patient", "priority": 1, "status": "WAITING", "arrival_time": datetime.now()}
    service.waiting_heap.insert(1, datetime.now().timestamp(), 101)

    result = service.allocate_doctor()
    assert result["success"] is False
    assert "No doctors are currently available" in result["message"]
    # Verify patient remains untouched in the waiting heap
    assert service.waiting_heap.size() == 1


# ============================================================================
# 4. No Allocation When Queue Is Empty
# ============================================================================

def test_no_allocation_when_queue_is_empty(service):
    """Verify allocate_doctor returns success=False when no patients are waiting."""
    service.doctors[1] = {"id": 1, "name": "Dr. Free", "specialization": "ER", "is_available": True, "current_patient_id": None}
    service.available_doctors.enqueue(1)

    result = service.allocate_doctor()
    assert result["success"] is False
    assert "No patients currently waiting" in result["message"]
    # Doctor remains available in queue
    assert service.available_doctors.size() == 1


# ============================================================================
# 5. Duplicate / Concurrent Allocation Calls
# ============================================================================

def test_duplicate_allocate_calls(service, mock_db):
    """Verify rapid consecutive allocate calls handle running out of resources safely."""
    # 1 doctor, 1 patient
    service.doctors[1] = {"id": 1, "name": "Dr. Solo", "specialization": "ER", "is_available": True, "current_patient_id": None}
    service.available_doctors.enqueue(1)

    service.patients[101] = {"id": 101, "name": "Solo Patient", "priority": 1, "status": "WAITING", "arrival_time": datetime.now()}
    service.waiting_heap.insert(1, datetime.now().timestamp(), 101)

    # First call succeeds
    res1 = service.allocate_doctor()
    assert res1["success"] is True

    # Immediate duplicate call fails gracefully
    res2 = service.allocate_doctor()
    assert res2["success"] is False


# ============================================================================
# 6. Discharge Frees Doctor and Auto-Allocates Next Patient
# ============================================================================

def test_discharge_frees_doctor_and_auto_allocates(service, mock_db):
    """Verify discharging frees the assigned doctor and auto-allocates the next waiting patient."""
    service.doctors[1] = {"id": 1, "name": "Dr. Cuddy", "specialization": "Internal", "is_available": False, "current_patient_id": 101}
    # No available doctors initially

    service.patients[101] = {
        "id": 101, "name": "Patient In Treatment", "priority": 1, "status": "IN_TREATMENT",
        "assigned_doctor_id": 1, "arrival_time": datetime.now(),
    }
    service.patients[102] = {
        "id": 102, "name": "Next In Line", "priority": 2, "status": "WAITING",
        "assigned_doctor_id": None, "arrival_time": datetime.now(),
    }
    service.waiting_heap.insert(2, datetime.now().timestamp(), 102)

    # Discharge patient 101
    discharge_res = service.discharge_patient(101)
    assert discharge_res["patient"]["status"] == "DISCHARGED"

    # Doctor 1 must have been freed and auto-assigned to patient 102!
    auto_alloc = discharge_res["auto_allocation"]
    assert auto_alloc is not None
    assert auto_alloc["success"] is True
    assert auto_alloc["patient"]["id"] == 102
    assert auto_alloc["doctor"]["id"] == 1
    assert service.patients[102]["status"] == "IN_TREATMENT"
    assert service.doctors[1]["current_patient_id"] == 102


# ============================================================================
# 7. Priority Update Reordering
# ============================================================================

def test_priority_update_reordering(service, mock_db):
    """Verify updating priority re-orders the Min-Heap in O(log n)."""
    now = datetime.now()
    service.patients[101] = {"id": 101, "name": "P1", "priority": 3, "status": "WAITING", "arrival_time": now}
    service.waiting_heap.insert(3, now.timestamp(), 101)

    service.patients[102] = {"id": 102, "name": "P2", "priority": 2, "status": "WAITING", "arrival_time": now}
    service.waiting_heap.insert(2, now.timestamp(), 102)

    # Current top is P2 (priority 2)
    assert service.waiting_heap.peek()[2] == 102

    # Escalate P1 from Priority 3 to Priority 1 (Critical)
    updated = service.update_priority(101, 1)
    assert updated["priority"] == 1

    # New top must be P1
    assert service.waiting_heap.peek()[2] == 101
    assert service.waiting_heap.peek()[0] == 1


# ============================================================================
# 8. Aging Boost Logic
# ============================================================================

def test_aging_boost(service, mock_db):
    """Verify patients waiting longer than threshold receive priority boost, capped at Priority 1."""
    now = datetime.now()
    # Arrived 45 mins ago with Priority 3 (Moderate)
    service.patients[101] = {
        "id": 101, "name": "Patient Long Wait", "priority": 3, "status": "WAITING",
        "arrival_time": now - timedelta(minutes=45)
    }
    service.waiting_heap.insert(3, (now - timedelta(minutes=45)).timestamp(), 101)

    # First boost: 3 -> 2
    res1 = service.apply_aging(minutes_threshold=30)
    assert res1["boosted_count"] == 1
    assert service.patients[101]["priority"] == 2
    assert service.waiting_heap.peek()[0] == 2

    # Second boost: 2 -> 1
    res2 = service.apply_aging(minutes_threshold=30)
    assert res2["boosted_count"] == 1
    assert service.patients[101]["priority"] == 1
    assert service.waiting_heap.peek()[0] == 1

    # Third boost attempt: Already Priority 1 (Critical), must not boost further
    res3 = service.apply_aging(minutes_threshold=30)
    assert res3["boosted_count"] == 0
    assert service.patients[101]["priority"] == 1


# ============================================================================
# 9. Invalid State Transitions & Edge Cases
# ============================================================================

def test_invalid_transitions_and_edge_cases(service, mock_db):
    """Verify that invalid status transitions, non-waiting priority updates, and duplicates fail."""
    # 1. Update priority of patient in IN_TREATMENT raises ValueError
    service.patients[101] = {"id": 101, "name": "Active Patient", "priority": 2, "status": "IN_TREATMENT"}
    with pytest.raises(ValueError, match="Cannot update priority"):
        service.update_priority(101, 1)

    # 2. Update priority of DISCHARGED patient raises ValueError
    service.patients[102] = {"id": 102, "name": "Discharged Patient", "priority": 2, "status": "DISCHARGED"}
    with pytest.raises(ValueError, match="Cannot update priority"):
        service.update_priority(102, 1)

    # 3. Update priority of non-existent patient raises KeyError
    with pytest.raises(KeyError):
        service.update_priority(999, 1)

    # 4. Discharge already discharged patient raises ValueError
    with pytest.raises(ValueError, match="already discharged"):
        service.discharge_patient(102)

    # 5. Invalid status string raises ValueError
    service.patients[103] = {"id": 103, "name": "Waiting Patient", "priority": 3, "status": "WAITING"}
    with pytest.raises(ValueError, match="Invalid status"):
        service.update_status(103, "RECOVERED", "Should fail")

    # 6. Reverting IN_TREATMENT to WAITING raises ValueError
    with pytest.raises(ValueError, match="Cannot revert"):
        service.update_status(101, "WAITING", "Illegal revert")

    # 7. Setting status to IN_TREATMENT without doctor assignment raises ValueError
    with pytest.raises(ValueError, match="without an assigned doctor"):
        service.update_status(103, "IN_TREATMENT", "Illegal transition without doctor")


# ============================================================================
# 10. Server Restart State Rebuild from MySQL
# ============================================================================

def test_server_restart_state_rebuild(service, mock_db):
    """Verify that calling load_from_db accurately rebuilds all custom DSA state from MySQL."""
    cursor = mock_db["cursor"]
    now = datetime.now()

    # Seed mock data simulating database rows after a server restart
    cursor.fetchall.side_effect = [
        # Doctors table
        [
            {"id": 1, "name": "Dr. Free", "specialization": "ER", "is_available": 1, "current_patient_id": None},
            {"id": 2, "name": "Dr. Busy", "specialization": "Trauma", "is_available": 0, "current_patient_id": 201},
        ],
        # Patients table
        [
            {"id": 201, "name": "In Treatment", "age": 40, "gender": "M", "contact": "1", "complaint": "Pain",
             "category": "Cardiac", "priority": 1, "status": "IN_TREATMENT", "arrival_time": now,
             "treatment_start": now, "discharge_time": None, "assigned_doctor_id": 2},
            {"id": 202, "name": "Waiting Case", "age": 25, "gender": "F", "contact": "2", "complaint": "Cut",
             "category": "Minor", "priority": 4, "status": "WAITING", "arrival_time": now,
             "treatment_start": None, "discharge_time": None, "assigned_doctor_id": None},
            {"id": 203, "name": "Discharged Case", "age": 60, "gender": "M", "contact": "3", "complaint": "Old",
             "category": "Moderate", "priority": 3, "status": "DISCHARGED", "arrival_time": now,
             "treatment_start": now, "discharge_time": now, "assigned_doctor_id": None},
        ],
        # Treatment log table
        [
            {"id": 1, "patient_id": 201, "status": "WAITING", "note": "Checked in", "created_at": now},
            {"id": 2, "patient_id": 201, "status": "IN_TREATMENT", "note": "Assigned to Dr. Busy", "created_at": now},
            {"id": 3, "patient_id": 202, "status": "WAITING", "note": "Triage Minor", "created_at": now},
            {"id": 4, "patient_id": 203, "status": "DISCHARGED", "note": "Treated and sent home", "created_at": now},
        ],
    ]

    service.load_from_db()
    cursor.fetchall.side_effect = None

    # Verification:
    # 1. Doctors HashMap has 2 doctors
    assert service.doctors.size() == 2
    # 2. Available Doctors Queue has ONLY 1 doctor (Dr. Free)
    assert service.available_doctors.size() == 1
    assert service.available_doctors.peek() == 1
    # 3. Patients HashMap has 3 patients
    assert service.patients.size() == 3
    # 4. Waiting Heap has ONLY 1 patient (Patient 202)
    assert service.waiting_heap.size() == 1
    assert service.waiting_heap.peek()[2] == 202
    # 5. History LinkedLists populated
    assert service.history[201].size() == 2
    assert service.history[202].size() == 1
    assert service.history[203].size() == 1
