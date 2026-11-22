"""
Emergency Queue & Priority Allocation API Routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from backend.models import AgingRequest, ApiResponse
from backend.services.hospital_service import hospital_service

router = APIRouter(prefix="/api/queue", tags=["Queue"])


@router.get("", response_model=ApiResponse)
def get_waiting_queue():
    """
    Returns the sorted list of currently waiting emergency patients
    in order of priority (1=Critical ... 4=Minor), breaking ties by arrival time (FIFO).
    Includes live waiting duration in minutes.
    """
    waiting_list = hospital_service.get_waiting_list()
    return ApiResponse(
        success=True,
        data=waiting_list,
        message=f"Current waiting queue contains {len(waiting_list)} patients."
    )


@router.post("/allocate", response_model=ApiResponse)
def allocate_doctor():
    """
    Allocates the highest-priority patient in the MinHeap to the next available doctor in the FIFO Queue.
    Returns doctor-patient pairing or an explanatory message if queue/doctors are empty.
    """
    try:
        result = hospital_service.allocate_doctor()
        return ApiResponse(
            success=result["success"],
            data=result,
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Allocation failed: {str(e)}"
        )


@router.post("/apply-aging", response_model=ApiResponse)
def apply_aging(payload: Optional[AgingRequest] = None):
    """
    Checks all waiting patients. Any patient with priority > 1 who has waited
    longer than threshold_minutes receives an aging boost (priority decreased by 1).
    """
    threshold = payload.threshold_minutes if payload else 30
    try:
        result = hospital_service.apply_aging(minutes_threshold=threshold)
        return ApiResponse(
            success=True,
            data=result,
            message=f"Aging check complete. {result['boosted_count']} patients received priority boost."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Aging operation failed: {str(e)}"
        )
