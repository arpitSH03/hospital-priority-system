"""
End-to-End API Integration Test: Main Hospital Flow.

Simulates the complete user workflow:
1. Register 5 patients with mixed priorities.
2. Verify /api/queue priority sorting and timestamp tie-breaking.
3. Allocate available doctor to highest-priority patient.
4. Discharge treated patient and verify doctor re-enqueue and auto-allocation.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.hospital_service import hospital_service


@pytest.fixture(autouse=True)
def mock_db_and_clean_state():
    """Mocks database connections and resets HospitalService for clean tests."""
    with patch("backend.services.hospital_service.get_db_connection") as mock_conn_fn, \
         patch("backend.database.get_db_connection") as mock_db_conn_fn:

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn_fn.return_value = conn
        mock_db_conn_fn.return_value = conn

        # Reset singleton state
        hospital_service._initialized = False
        hospital_service.__init__()

        # Seed two available doctors directly into service
        hospital_service.doctors[1] = {
            "id": 1, "name": "Dr. House", "specialization": "Diagnostic Medicine",
            "is_available": True, "current_patient_id": None
        }
        hospital_service.available_doctors.enqueue(1)

        hospital_service.doctors[2] = {
            "id": 2, "name": "Dr. Chase", "specialization": "Emergency Medicine",
            "is_available": True, "current_patient_id": None
        }
        hospital_service.available_doctors.enqueue(2)

        yield {"cursor": cursor, "conn": conn}


def test_main_emergency_flow():
    """
    Executes the full flow:
    - Register 5 patients with mixed priorities (P3, P1, P4, P2, P1)
    - Verify /api/queue sorts them as [P1_first, P1_second, P2, P3, P4]
    - Allocate next doctor via /api/queue/allocate
    - Discharge patient via /api/patients/{id}/discharge
    """
    client = TestClient(app)

    # 1. Register 5 patients
    patients_to_register = [
        {"name": "Pat_Moderate", "age": 40, "gender": "M", "contact": "111", "complaint": "Sprain", "category": "Moderate", "priority": 3},
        {"name": "Pat_Critical_Early", "age": 55, "gender": "F", "contact": "222", "complaint": "Cardiac Arrest", "category": "Critical", "priority": 1},
        {"name": "Pat_Minor", "age": 20, "gender": "M", "contact": "333", "complaint": "Rash", "category": "Minor", "priority": 4},
        {"name": "Pat_Urgent", "age": 32, "gender": "F", "contact": "444", "complaint": "Appendicitis", "category": "Urgent", "priority": 2},
        {"name": "Pat_Critical_Late", "age": 60, "gender": "M", "contact": "555", "complaint": "Polytrauma", "category": "Critical", "priority": 1},
    ]

    registered_ids = []
    # Mock row IDs for registration
    with patch("backend.services.hospital_service.get_db_connection") as mock_conn:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn.return_value = conn

        current_id = 100
        for p_data in patients_to_register:
            current_id += 1
            cursor.lastrowid = current_id
            resp = client.post("/api/patients", json=p_data)
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["success"] is True
            registered_ids.append(data["data"]["id"])

    assert len(registered_ids) == 5

    # 2. Check /api/queue order
    # Expected order:
    # 1. Pat_Critical_Early (id 102, Priority 1, arrived first)
    # 2. Pat_Critical_Late  (id 105, Priority 1, arrived second)
    # 3. Pat_Urgent         (id 104, Priority 2)
    # 4. Pat_Moderate       (id 101, Priority 3)
    # 5. Pat_Minor          (id 103, Priority 4)
    queue_resp = client.get("/api/queue")
    assert queue_resp.status_code == 200
    queue_data = queue_resp.json()
    assert queue_data["success"] is True

    waiting_list = queue_data["data"]
    assert len(waiting_list) == 5
    queue_names = [p["name"] for p in waiting_list]
    assert queue_names == [
        "Pat_Critical_Early",
        "Pat_Critical_Late",
        "Pat_Urgent",
        "Pat_Moderate",
        "Pat_Minor",
    ]

    # Verify ranks and priorities
    assert [p["priority"] for p in waiting_list] == [1, 1, 2, 3, 4]
    assert [p["queue_rank"] for p in waiting_list] == [1, 2, 3, 4, 5]

    # 3. Allocate next patient
    alloc_resp = client.post("/api/queue/allocate")
    assert alloc_resp.status_code == 200
    alloc_data = alloc_resp.json()
    assert alloc_data["success"] is True
    # Highest priority patient Pat_Critical_Early must be assigned to Dr. House
    assert alloc_data["data"]["patient"]["id"] == 102
    assert alloc_data["data"]["doctor"]["name"] == "Dr. House"

    # Queue should now have 4 patients
    queue_after_alloc = client.get("/api/queue").json()["data"]
    assert len(queue_after_alloc) == 4
    assert queue_after_alloc[0]["name"] == "Pat_Critical_Late"

    # 4. Discharge patient (id 102)
    discharge_resp = client.post("/api/patients/102/discharge")
    assert discharge_resp.status_code == 200
    discharge_data = discharge_resp.json()
    assert discharge_data["success"] is True
    assert discharge_data["data"]["patient"]["status"] == "DISCHARGED"

    # Auto-allocation check: Dr. House is freed and auto-assigned to Pat_Critical_Late!
    auto_alloc = discharge_data["data"]["auto_allocation"]
    assert auto_alloc is not None
    assert auto_alloc["success"] is True
    assert auto_alloc["patient"]["id"] == 105

    # Queue should now have 3 patients
    queue_after_discharge = client.get("/api/queue").json()["data"]
    assert len(queue_after_discharge) == 3
    assert [p["name"] for p in queue_after_discharge] == ["Pat_Urgent", "Pat_Moderate", "Pat_Minor"]

    # 5. Check patient history linked list
    history_resp = client.get("/api/patients/102/history")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert history_data["success"] is True
    # Should have at least 3 stages: WAITING -> IN_TREATMENT -> DISCHARGED
    statuses = [entry["status"] for entry in history_data["data"]]
    assert "WAITING" in statuses
    assert "IN_TREATMENT" in statuses
    assert "DISCHARGED" in statuses

    # 6. Check reports summary
    report_resp = client.get("/api/reports/summary")
    assert report_resp.status_code == 200
    report_data = report_resp.json()["data"]
    assert report_data["total_patients"] == 5
    assert report_data["currently_waiting"] == 3
    assert report_data["discharged"] == 1
    assert report_data["in_treatment"] == 1
