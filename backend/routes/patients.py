"""
Patient Management API Routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.models import ApiResponse, PatientCreate, PriorityUpdate, StatusUpdate
from backend.services.hospital_service import hospital_service

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def register_patient(payload: PatientCreate):
    """
    Registers a new patient into the hospital emergency triage system.
    Determines triage priority, persists to database, and places in MinHeap.
    """
    try:
        data = payload.model_dump()
        patient = hospital_service.register_patient(data)
        return ApiResponse(
            success=True,
            data=patient,
            message=f"Patient '{patient['name']}' registered successfully with Priority {patient['priority']}."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("", response_model=ApiResponse)
def list_patients(status_filter: Optional[str] = Query(None, alias="status", description="Filter by WAITING, IN_TREATMENT, or DISCHARGED")):
    """
    Retrieves all registered patients, optionally filtered by status.
    """
    patients = hospital_service.list_patients(status_filter=status_filter)
    return ApiResponse(
        success=True,
        data=patients,
        message=f"Retrieved {len(patients)} patients."
    )


@router.get("/{patient_id}", response_model=ApiResponse)
def get_patient(patient_id: int):
    """
    Retrieves single patient details by patient_id from O(1) HashMap lookup.
    """
    if not hospital_service.patients.contains(patient_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found."
        )
    patient = hospital_service.patients[patient_id]
    return ApiResponse(
        success=True,
        data=patient,
        message=f"Patient #{patient_id} retrieved successfully."
    )


@router.put("/{patient_id}/priority", response_model=ApiResponse)
def update_patient_priority(patient_id: int, payload: PriorityUpdate):
    """
    Updates the medical priority of a WAITING patient.
    Restores MinHeap ordering in O(log n) time.
    """
    try:
        updated_patient = hospital_service.update_priority(patient_id, payload.priority)
        return ApiResponse(
            success=True,
            data=updated_patient,
            message=f"Priority for Patient #{patient_id} updated to {payload.priority}."
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{patient_id}/status", response_model=ApiResponse)
def update_patient_status(patient_id: int, payload: StatusUpdate):
    """
    Updates patient status and logs a clinical note into their treatment history.
    """
    try:
        updated_patient = hospital_service.update_status(patient_id, payload.status, payload.note)
        return ApiResponse(
            success=True,
            data=updated_patient,
            message=f"Status for Patient #{patient_id} updated to '{payload.status}'."
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{patient_id}/discharge", response_model=ApiResponse)
def discharge_patient(patient_id: int):
    """
    Discharges a patient, frees their attending doctor (enqueuing back into FIFO queue),
    and automatically triggers allocation for the next waiting patient.
    """
    try:
        result = hospital_service.discharge_patient(patient_id)
        return ApiResponse(
            success=True,
            data=result,
            message=result.get("message", f"Patient #{patient_id} discharged successfully.")
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{patient_id}/history", response_model=ApiResponse)
def get_patient_history(patient_id: int):
    """
    Retrieves the complete linear treatment history for a patient from their custom LinkedList.
    """
    if not hospital_service.patients.contains(patient_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found."
        )
    history = hospital_service.get_patient_history(patient_id)
    return ApiResponse(
        success=True,
        data=history,
        message=f"Retrieved {len(history)} treatment log entries for Patient #{patient_id}."
    )
