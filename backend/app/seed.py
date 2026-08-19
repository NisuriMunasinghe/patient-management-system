from datetime import datetime, time, timedelta, timezone

from pwdlib import PasswordHash
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AvailabilitySlot, Doctor, User, UserRole


password_hash = PasswordHash.recommended()

DOCTORS = [
    {
        "email": "maya.fernando@clinicflow.com",
        "full_name": "Dr. Maya Fernando",
        "specialty": "Cardiology",
    },
    {
        "email": "arun.perera@clinicflow.com",
        "full_name": "Dr. Arun Perera",
        "specialty": "Dermatology",
    },
    {
        "email": "sara.silva@clinicflow.com",
        "full_name": "Dr. Sara Silva",
        "specialty": "General Medicine",
    },
]

def seed_database() -> None:
    with SessionLocal() as db:
        existing_doctor = db.scalar(select(Doctor.id).limit(1))

        if existing_doctor is not None:
            print("Seed data already exists. Nothing changed.")
            return

        doctors: list[Doctor] = []

        for doctor_data in DOCTORS:
            user = User(
                email=doctor_data["email"],
                password_hash=password_hash.hash("Doctor123!"),
                role=UserRole.DOCTOR,
            )
            db.add(user)
            db.flush()

            doctor = Doctor(
                user_id=user.id,
                full_name=doctor_data["full_name"],
                specialty=doctor_data["specialty"],
            )
            db.add(doctor)
            doctors.append(doctor)

        db.flush()

        first_day = datetime.now(timezone.utc).date() + timedelta(days=1)
        appointment_hours = (9, 10, 11, 14, 15)

        for doctor in doctors:
            for day_offset in range(7):
                slot_date = first_day + timedelta(days=day_offset)

                for hour in appointment_hours:
                    starts_at = datetime.combine(
                        slot_date,
                        time(hour=hour),
                        tzinfo=timezone.utc,
                    )

                    db.add(
                        AvailabilitySlot(
                            doctor_id=doctor.id,
                            starts_at=starts_at,
                            ends_at=starts_at + timedelta(minutes=30),
                        )
                    )

        db.commit()

    print("Created 3 doctors and 105 future appointment slots.")
    print("Doctor password: Doctor123!")


if __name__ == "__main__":
    seed_database()