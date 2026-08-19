from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AppointmentStatus, UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    specialty: str


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    starts_at: datetime
    ends_at: datetime


class AppointmentCreate(BaseModel):
    slot_id: int = Field(gt=0)


class AppointmentResponse(BaseModel):
    id: int
    slot_id: int
    status: AppointmentStatus
    doctor_id: int
    doctor_name: str
    specialty: str
    starts_at: datetime
    ends_at: datetime


class DoctorScheduleItem(BaseModel):
    appointment_id: int
    patient_email: EmailStr
    status: AppointmentStatus
    starts_at: datetime
    ends_at: datetime