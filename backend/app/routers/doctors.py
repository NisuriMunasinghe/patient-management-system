from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_doctor, get_current_patient
from app.models import (
    Appointment,
    AppointmentStatus,
    AvailabilitySlot,
    Doctor,
    User,
)
from app.schemas import (
    DoctorResponse,
    DoctorScheduleItem,
    SlotResponse,
)


router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorResponse])
def list_doctors(
    current_patient: Annotated[User, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
    specialty: str | None = Query(default=None, max_length=120),
) -> list[Doctor]:
    statement = select(Doctor).order_by(
        Doctor.specialty,
        Doctor.full_name,
    )

    if specialty and specialty.strip():
        statement = statement.where(
            Doctor.specialty.ilike(f"%{specialty.strip()}%")
        )

    return list(db.scalars(statement).all())


# Keep this route above /{doctor_id}/slots.
@router.get("/me/schedule", response_model=list[DoctorScheduleItem])
def get_my_schedule(
    current_user: Annotated[User, Depends(get_current_doctor)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=30),
) -> list[DoctorScheduleItem]:
    doctor = current_user.doctor_profile

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "doctor_profile_not_found",
                "message": "Doctor profile was not found.",
            },
        )

    starts_at = datetime.now(timezone.utc)
    ends_at = starts_at + timedelta(days=days)

    statement = (
        select(Appointment)
        .join(Appointment.slot)
        .options(
            joinedload(Appointment.slot),
            joinedload(Appointment.patient),
        )
        .where(
            AvailabilitySlot.doctor_id == doctor.id,
            AvailabilitySlot.starts_at >= starts_at,
            AvailabilitySlot.starts_at < ends_at,
            Appointment.status == AppointmentStatus.BOOKED,
        )
        .order_by(AvailabilitySlot.starts_at)
    )

    appointments = db.scalars(statement).all()

    return [
        DoctorScheduleItem(
            appointment_id=appointment.id,
            patient_email=appointment.patient.email,
            status=appointment.status,
            starts_at=appointment.slot.starts_at,
            ends_at=appointment.slot.ends_at,
        )
        for appointment in appointments
    ]


@router.get(
    "/{doctor_id}/slots",
    response_model=list[SlotResponse],
)
def list_available_slots(
    doctor_id: int,
    current_patient: Annotated[User, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=30),
) -> list[AvailabilitySlot]:
    doctor = db.get(Doctor, doctor_id)

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "doctor_not_found",
                "message": "Doctor was not found.",
            },
        )

    starts_at = datetime.now(timezone.utc)
    ends_at = starts_at + timedelta(days=days)

    statement = (
        select(AvailabilitySlot)
        .where(
            AvailabilitySlot.doctor_id == doctor_id,
            AvailabilitySlot.starts_at >= starts_at,
            AvailabilitySlot.starts_at < ends_at,
            ~AvailabilitySlot.appointments.any(
                Appointment.status == AppointmentStatus.BOOKED
            ),
        )
        .order_by(AvailabilitySlot.starts_at)
    )

    return list(db.scalars(statement).all())