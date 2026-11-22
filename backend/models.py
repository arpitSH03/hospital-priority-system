"""
Pydantic Request & Response Models for the Hospital Emergency API.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Patient Models
# -----------------------------------------------------------------------------

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Full name of the patient")
    age: int = Field(..., ge=0, le=130, description="Age in years")
    gender: str = Field("Other", description="Gender (e.g. Male, Female, Other)")
    contact: str = Field("", description="Phone number or emergency contact")
    complaint: str = Field(..., min_length=1, description="Primary medical complaint / symptoms")
    category: str = Field("General", description="Triage category (Critical, Urgent, Moderate, Minor, Cardiac, Trauma, etc.)")
    priority: Optional[int] = Field(None, ge=1, le=4, description="Optional explicit priority (1=Critical, 4=Minor)")


class PriorityUpdate(BaseModel):
    priority: int = Field(..., ge=1, le=4, description="New priority (1=Critical, 2=Urgent, 3=Moderate, 4=Minor)")


class StatusUpdate(BaseModel):
    status: str = Field(..., description="Target status ('WAITING', 'IN_TREATMENT', 'DISCHARGED')")
    note: str = Field(..., min_length=1, description="Clinical or administrative reason for status change")


# -----------------------------------------------------------------------------
# Doctor Models
# -----------------------------------------------------------------------------

class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Full name of the physician (e.g. Dr. John Watson)")
    specialization: str = Field(..., min_length=1, description="Medical specialization (e.g. Trauma Surgery, Cardiology)")


class DoctorAvailabilityUpdate(BaseModel):
    is_available: bool = Field(..., description="Whether the doctor is currently on duty and available for allocation")


# -----------------------------------------------------------------------------
# Queue & Aging Models
# -----------------------------------------------------------------------------

class AgingRequest(BaseModel):
    threshold_minutes: int = Field(30, ge=1, description="Waiting duration in minutes after which priority is bumped")


# -----------------------------------------------------------------------------
# Standard API Response Envelope
# -----------------------------------------------------------------------------

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str = ""
