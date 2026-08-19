from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_patient
from app.models import (
    Appointment,
    AppointmentStatus,
    AvailabilitySlot,
    User,
)
from app.schemas import AppointmentCreate, AppointmentResponse


router = APIRouter(prefix="/appointments", tags=["appointments"])


def serialize_appointment(
    appointment: Appointment,
) -> AppointmentResponse:
    slot = appointment.slot

    return AppointmentResponse(
        id=appointment.id,
        slot_id=slot.id,
        status=appointment.status,
        doctor_id=slot.doctor.id,
        doctor_name=slot.doctor.full_name,
        specialty=slot.doctor.specialty,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
    )


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    payload: AppointmentCreate,
    current_patient: Annotated[User, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    slot = db.scalar(
        select(AvailabilitySlot)
        .options(joinedload(AvailabilitySlot.doctor))
        .where(AvailabilitySlot.id == payload.slot_id)
    )

    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "slot_not_found",
                "message": "Appointment slot was not found.",
            },
        )

    if slot.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "past_slot",
                "message": "Past appointment slots cannot be booked.",
            },
        )

    appointment = Appointment(
        patient_id=current_patient.id,
        slot=slot,
        status=AppointmentStatus.BOOKED,
    )
    db.add(appointment)

    try:
        db.commit()
        db.refresh(appointment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "slot_already_booked",
                "message": "This appointment slot is already booked.",
            },
        ) from None

    return serialize_appointment(appointment)


@router.get("/me", response_model=list[AppointmentResponse])
def list_my_appointments(
    current_patient: Annotated[User, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AppointmentResponse]:
    statement = (
        select(Appointment)
        .join(Appointment.slot)
        .options(
            joinedload(Appointment.slot).joinedload(
                AvailabilitySlot.doctor
            )
        )
        .where(
            Appointment.patient_id == current_patient.id,
            Appointment.status == AppointmentStatus.BOOKED,
            AvailabilitySlot.starts_at >= datetime.now(timezone.utc),
        )
        .order_by(AvailabilitySlot.starts_at)
    )

    appointments = db.scalars(statement).all()

    return [
        serialize_appointment(appointment)
        for appointment in appointments
    ]


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_appointment(
    appointment_id: int,
    current_patient: Annotated[User, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    appointment = db.scalar(
        select(Appointment)
        .where(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_patient.id,
        )
        .with_for_update()
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "appointment_not_found",
                "message": "Appointment was not found.",
            },
        )

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)