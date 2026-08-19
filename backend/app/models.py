from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"

class AppointmentStatus(str, Enum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

def enum_values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(320), 
        unique=True,
        index=True, 
        nullable=False
        )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    doctor_profile: Mapped[Doctor | None] = relationship(
        back_populates="user",
        uselist=False,
    )
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="patient",
    )

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(
        String(120),
        index=True,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="doctor_profile")
    slots: Mapped[list[AvailabilitySlot]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    __table_args__ = (
        CheckConstraint(
            "ends_at > starts_at",
            name="ck_slot_ends_after_start",
        ),
        UniqueConstraint(
            "doctor_id",
            "starts_at",
            name="uq_doctor_slot_start",
        ),
        Index(
            "ix_slots_doctor_start",
            "doctor_id",
            "starts_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    doctor: Mapped[Doctor] = relationship(back_populates="slots")
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="slot",
    )

class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_booked_appointment_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'booked'"),
        ),
        Index(
            "ix_appointments_patient_status",
            "patient_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("availability_slots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        SqlEnum(
            AppointmentStatus,
            name="appointment_status",
            values_callable=enum_values,
        ),
        default=AppointmentStatus.BOOKED,
        server_default=AppointmentStatus.BOOKED.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    patient: Mapped[User] = relationship(back_populates="appointments")
    slot: Mapped[AvailabilitySlot] = relationship(
        back_populates="appointments",
    )

    