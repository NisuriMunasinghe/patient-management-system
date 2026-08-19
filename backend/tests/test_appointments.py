from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appointment,
    AvailabilitySlot,
    Doctor,
    User,
    UserRole,
)
from app.security import create_access_token


client = TestClient(app)


def authorization_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


def test_booking_invariants_and_cancellation_ownership() -> None:
    unique_value = uuid4().hex
    db = SessionLocal()

    patient_one = User(
        email=f"patient-one-{unique_value}@clinicflow.com",
        password_hash="unused-in-this-test",
        role=UserRole.PATIENT,
    )
    patient_two = User(
        email=f"patient-two-{unique_value}@clinicflow.com",
        password_hash="unused-in-this-test",
        role=UserRole.PATIENT,
    )
    doctor_user = User(
        email=f"doctor-{unique_value}@clinicflow.com",
        password_hash="unused-in-this-test",
        role=UserRole.DOCTOR,
    )

    db.add_all([patient_one, patient_two, doctor_user])
    db.flush()

    doctor = Doctor(
        user_id=doctor_user.id,
        full_name="Dr. Integration Test",
        specialty="Test Medicine",
    )
    db.add(doctor)
    db.flush()

    future_slot = AvailabilitySlot(
        doctor_id=doctor.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        ends_at=datetime.now(timezone.utc)
        + timedelta(days=2, minutes=30),
    )
    past_slot = AvailabilitySlot(
        doctor_id=doctor.id,
        starts_at=datetime.now(timezone.utc) - timedelta(days=2),
        ends_at=datetime.now(timezone.utc)
        - timedelta(days=2)
        + timedelta(minutes=30),
    )

    db.add_all([future_slot, past_slot])
    db.commit()

    patient_one_id = patient_one.id
    patient_two_id = patient_two.id
    doctor_user_id = doctor_user.id
    doctor_id = doctor.id
    future_slot_id = future_slot.id
    past_slot_id = past_slot.id

    patient_one_headers = authorization_headers(patient_one)
    patient_two_headers = authorization_headers(patient_two)

    try:
        first_booking = client.post(
            "/api/appointments",
            json={"slot_id": future_slot_id},
            headers=patient_one_headers,
        )
        assert first_booking.status_code == 201
        appointment_id = first_booking.json()["id"]

        duplicate_booking = client.post(
            "/api/appointments",
            json={"slot_id": future_slot_id},
            headers=patient_two_headers,
        )
        assert duplicate_booking.status_code == 409
        assert (
            duplicate_booking.json()["detail"]["code"]
            == "slot_already_booked"
        )

        past_booking = client.post(
            "/api/appointments",
            json={"slot_id": past_slot_id},
            headers=patient_one_headers,
        )
        assert past_booking.status_code == 422
        assert past_booking.json()["detail"]["code"] == "past_slot"

        another_patient_cancellation = client.delete(
            f"/api/appointments/{appointment_id}",
            headers=patient_two_headers,
        )
        assert another_patient_cancellation.status_code == 404

        owner_cancellation = client.delete(
            f"/api/appointments/{appointment_id}",
            headers=patient_one_headers,
        )
        assert owner_cancellation.status_code == 204

        rebooking_after_cancellation = client.post(
            "/api/appointments",
            json={"slot_id": future_slot_id},
            headers=patient_two_headers,
        )
        assert rebooking_after_cancellation.status_code == 201

        patient_two_appointments = client.get(
            "/api/appointments/me",
            headers=patient_two_headers,
        )
        assert patient_two_appointments.status_code == 200
        assert len(patient_two_appointments.json()) == 1

    finally:
        db.rollback()

        db.execute(
            delete(Appointment).where(
                Appointment.slot_id.in_(
                    [future_slot_id, past_slot_id]
                )
            )
        )
        db.execute(
            delete(AvailabilitySlot).where(
                AvailabilitySlot.id.in_(
                    [future_slot_id, past_slot_id]
                )
            )
        )
        db.execute(
            delete(Doctor).where(Doctor.id == doctor_id)
        )
        db.execute(
            delete(User).where(
                User.id.in_(
                    [
                        patient_one_id,
                        patient_two_id,
                        doctor_user_id,
                    ]
                )
            )
        )
        db.commit()
        db.close()