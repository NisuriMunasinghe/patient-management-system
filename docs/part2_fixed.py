"""
Part 2: Corrected version ofthe original code.

"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import AwareDatetime
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.auth import (
    get_current_doctor_id,
    get_current_patient_id,
)
from app.db import engine


router = APIRouter()

# Fixed: added authenticated identities, validated datetimes, parameterized SQL, managed connections, transactions, database conflict handling and correct HTTP statuses.


@router.post(
    "/appointments",
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    doctor_id: int,
    slot_time: AwareDatetime,
    patient_id: Annotated[
        int,
        Depends(get_current_patient_id),
    ],
):
    if slot_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Past appointment slots cannot be booked.",
        )

    try:
        # engine.begin() commits on success, rolls back on failure and
        # closes the connection automatically.
        with engine.begin() as conn:
            doctor_exists = conn.execute(
                text(
                    """
                    SELECT id
                    FROM doctors
                    WHERE id = :doctor_id
                    """
                ),
                {"doctor_id": doctor_id},
            ).fetchone()

            if doctor_exists is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Doctor not found.",
                )

            existing = conn.execute(
                text(
                    """
                    SELECT id
                    FROM appointments
                    WHERE doctor_id = :doctor_id
                      AND slot_time = :slot_time
                      AND status = 'booked'
                    """
                ),
                {
                    "doctor_id": doctor_id,
                    "slot_time": slot_time,
                },
            ).fetchone()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Slot already booked.",
                )

            appointment_id = conn.execute(
                text(
                    """
                    INSERT INTO appointments (
                        patient_id,
                        doctor_id,
                        slot_time,
                        status
                    )
                    VALUES (
                        :patient_id,
                        :doctor_id,
                        :slot_time,
                        'booked'
                    )
                    RETURNING id
                    """
                ),
                {
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "slot_time": slot_time,
                },
            ).scalar_one()

    except IntegrityError:
        # A database unique constraint provides the final protection
        # against concurrent booking requests.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot already booked.",
        ) from None

    return {
        "id": appointment_id,
        "status": "booked",
    }


@router.get("/doctors/{doctor_id}/schedule")
def get_schedule(
    doctor_id: int,
    date: date,
    current_doctor_id: Annotated[
        int,
        Depends(get_current_doctor_id),
    ],
):
    if doctor_id != current_doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view another doctor's schedule.",
        )

    start_time = datetime.combine(
        date,
        time.min,
        tzinfo=timezone.utc,
    )
    end_time = start_time + timedelta(days=1)

    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT id, patient_id, slot_time, status
                FROM appointments
                WHERE doctor_id = :doctor_id
                  AND slot_time >= :start_time
                  AND slot_time < :end_time
                ORDER BY slot_time
                """
            ),
            {
                "doctor_id": doctor_id,
                "start_time": start_time,
                "end_time": end_time,
            },
        ).mappings().all()

    return [dict(row) for row in result]