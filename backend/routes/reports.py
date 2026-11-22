"""
Analytics & Operational Reports API Routes.
"""

from fastapi import APIRouter
from backend.models import ApiResponse
from backend.services.hospital_service import hospital_service

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/summary", response_model=ApiResponse)
def get_report_summary():
    """
    Returns comprehensive hospital KPIs:
    - Total, waiting, in-treatment, and discharged patient counts.
    - Distribution per priority level (1=Critical to 4=Minor).
    - Average waiting time per priority level.
    - Doctor roster utilization metrics (busy vs available).
    """
    report = hospital_service.get_report()
    return ApiResponse(
        success=True,
        data=report,
        message="Hospital operational summary report generated successfully."
    )
