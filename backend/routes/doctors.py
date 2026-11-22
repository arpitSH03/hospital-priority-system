"""
Doctor Management API Routes.
"""

from fastapi import APIRouter, HTTPException, status
from backend.models import ApiResponse, DoctorAvailabilityUpdate, DoctorCreate
from backend.services.hospital_service import hospital_service

router = APIRouter(prefix="/api/doctors", tags=["Doctors"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def add_doctor(payload: DoctorCreate):
    """
    Registers a new doctor into the hospital roster and adds them to the available doctor FIFO queue.
    """
    try:
        doctor = hospital_service.add_doctor(name=payload.name, specialization=payload.specialization)
        return ApiResponse(
            success=True,
            data=doctor,
            message=f"Doctor '{doctor['name']}' added successfully."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add doctor: {str(e)}"
        )


@router.get("", response_model=ApiResponse)
def list_doctors():
    """
    Lists all doctors, their current availability status, and currently assigned patient.
    """
    doctors = hospital_service.list_doctors()
    return ApiResponse(
        success=True,
        data=doctors,
        message=f"Retrieved {len(doctors)} doctors."
    )


@router.put("/{doctor_id}/availability", response_model=ApiResponse)
def update_doctor_availability(doctor_id: int, payload: DoctorAvailabilityUpdate):
    """
    Updates a doctor's availability status.
    If set to available, enqueues them into the available FIFO Queue;
    if set to unavailable, removes them from the queue.
    """
    try:
        updated_doc = hospital_service.set_doctor_availability(
            doctor_id=doctor_id,
            is_available=payload.is_available
        )
        return ApiResponse(
            success=True,
            data=updated_doc,
            message=f"Doctor #{doctor_id} availability set to {payload.is_available}."
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
