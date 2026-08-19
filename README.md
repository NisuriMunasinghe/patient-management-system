# ClinicFlow Patient Management System

ClinicFlow is a full-stack patient appointment management application developed for the Software Engineer candidate assignment.

Patients can register and log in, find doctors by specialty, view available time slots, book appointments, view upcoming appointments and cancel their own bookings. Doctors can log in and view their upcoming schedule.

## Technology stack

- **Backend:** Python, FastAPI and SQLAlchemy 2
- **Frontend:** React with hooks and Vite
- **Database:** PostgreSQL 17
- **Migrations:** Alembic
- **Authentication:** JWT bearer tokens and Argon2 password hashing
- **Testing:** Pytest and FastAPI TestClient
- **Infrastructure:** Docker Compose for PostgreSQL

## Implemented features

### Patient features

- Patient registration and login
- Search doctors by specialty
- View a doctor’s future available slots
- Book an appointment
- View upcoming appointments
- Cancel an owned appointment
- Rebook a slot after cancellation

### Doctor features

- Doctor login using seeded accounts
- View the authenticated doctor’s seven-day schedule
- Role-based protection of doctor endpoints

### Correctness and security

- PostgreSQL-enforced double-booking prevention
- Past appointment validation
- Timezone-aware timestamps
- Patient identity obtained from authentication
- Cancellation ownership validation
- Role-based authorization
- Parameterized database operations through SQLAlchemy
- Managed database sessions
- Appropriate HTTP status codes such as `201`, `401`, `403`, `404`, `409` and `422`

## Project structure

```text
patient-management-system/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── appointments.py
│   │   │   ├── auth.py
│   │   │   └── doctors.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   └── seed.py
│   ├── tests/
│   │   └── test_appointments.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/
│   ├── part2_analysis.py
│   └── part2_fixed.py
├── frontend/
│   ├── src/
│   └── package.json
├── .env.example
├── compose.yaml
└── README.md
```

## Architecture

The backend separates responsibilities into the following components:

- **Routers:** HTTP endpoint handling
- **Schemas:** Request validation and response serialization
- **Models:** SQLAlchemy entities and database constraints
- **Dependencies:** Authentication and role authorization
- **Security:** Password hashing and JWT operations
- **Database:** Engine and session lifecycle
- **Migrations:** Version-controlled database changes

The React application uses a small API helper and renders either the patient dashboard or doctor dashboard according to the authenticated user’s role.

## Data model

### Users

Stores authentication information and identifies each user as either a patient or doctor.

### Doctors

Stores a doctor’s name and specialty and connects the doctor profile to a user account.

### Availability slots

Stores predefined start and end times offered by a doctor.

### Appointments

Connects a patient to an availability slot and records whether the appointment is booked, cancelled or completed.

Appointments reference predefined availability slots instead of accepting an arbitrary doctor and timestamp. This ensures that patients can book only times that were offered by the doctor.

## Double-booking prevention

Checking whether a slot is available before inserting an appointment is not sufficient. Two concurrent requests could both observe that the slot is available before either request performs its insert.

The database therefore contains a PostgreSQL partial unique index:

```sql
CREATE UNIQUE INDEX uq_booked_appointment_per_slot
ON appointments (slot_id)
WHERE status = 'booked';
```

The API attempts to insert the appointment and handles a uniqueness violation as `409 Conflict`.

Because the index applies only to appointments with a `booked` status, a cancelled slot can be booked again while the cancelled appointment remains available as historical data.

## Prerequisites

Install the following:

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Docker Desktop
- Docker Compose
- Git

## Setup instructions

### 1. Clone the repository

```bash
git clone https://github.com/NisuriMunasinghe/patient-management-system.git
cd patient-management-system
```

### 2. Configure environment variables

Create the local environment file:

```bash
cp .env.example .env
```

The default development database runs on port `5434`.

Example configuration:

```dotenv
DATABASE_URL=postgresql+psycopg://clinicflow:clinicflow@localhost:5434/clinicflow
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FRONTEND_URL=http://localhost:5173
```

For any non-local environment, replace `JWT_SECRET_KEY` with a strong secret value.

### 3. Start PostgreSQL

Make sure Docker Desktop is running:

```bash
docker compose up -d db
docker compose ps
```

The `clinicflow-db` service should report a `healthy` status.

### 4. Configure the backend

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Apply the database migration:

```bash
python -m alembic upgrade head
```

Create the development doctors and availability slots:

```bash
python -m app.seed
```

Start FastAPI:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The backend is available at:

- API: `http://127.0.0.1:8000`
- Swagger documentation: `http://127.0.0.1:8000/docs`
- Health endpoint: `http://127.0.0.1:8000/api/health`

### 5. Configure the frontend

Open another terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Demo accounts

Patients can register through the application.

The seeded doctors use the development password:

```text
Doctor123!
```

Available doctor accounts:

```text
maya.fernando@clinicflow.com
arun.perera@clinicflow.com
sara.silva@clinicflow.com
```

These credentials are for local demonstration only.

## API endpoints

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | Check API health |
| `POST` | `/api/auth/register` | Public | Register a patient |
| `POST` | `/api/auth/login` | Public | Log in and obtain a JWT |
| `GET` | `/api/auth/me` | Authenticated | Get the current user |
| `GET` | `/api/doctors` | Patient | List or search doctors |
| `GET` | `/api/doctors/{doctor_id}/slots` | Patient | View available slots |
| `POST` | `/api/appointments` | Patient | Book a slot |
| `GET` | `/api/appointments/me` | Patient | View upcoming appointments |
| `DELETE` | `/api/appointments/{appointment_id}` | Patient owner | Cancel an appointment |
| `GET` | `/api/doctors/me/schedule` | Doctor | View the doctor’s schedule |

## Running tests

Make sure PostgreSQL is running and the migration has been applied:

```bash
docker compose up -d db

cd backend
source .venv/bin/activate
python -m pytest -q
```

The appointment integration test verifies:

- Successful future booking
- Prevention of double-booking
- Rejection of past slots
- Prevention of cancelling another patient’s appointment
- Successful owner cancellation
- Rebooking after cancellation
- Retrieval of upcoming patient appointments

The test creates uniquely named records and removes them after execution. In a production CI pipeline, tests should run against a dedicated test database supplied through `DATABASE_URL`.

## Building the frontend

Create a production frontend build with:

```bash
cd frontend
npm run build
```

The generated build is placed in `frontend/dist`.

## Part 2: debugging exercise

The debugging exercise is provided in two files:

- [`docs/part2_analysis.py`](docs/part2_analysis.py) contains the original code with comments identifying the problems.
- [`docs/part2_fixed.py`](docs/part2_fixed.py) contains a minimally corrected version that preserves the original structure.

The Part 2 files are independent examples based on the fictional codebase from the assignment. They are not imported by the ClinicFlow application.

### Problems identified

1. SQL injection caused by f-string SQL construction
2. Race condition between the availability check and insert
3. Missing database uniqueness protection
4. Patient identity accepted directly from request input
5. Missing authentication and schedule authorization
6. Appointment time accepted as an unvalidated string
7. Past appointments accepted
8. Doctor and referenced-entity existence not checked
9. Connections opened without guaranteed cleanup
10. Insert transaction not explicitly committed
11. Database exceptions not handled or rolled back
12. Booking conflicts returned as HTTP 200
13. Date filtering performed with unsafe and inefficient `LIKE`
14. SQLAlchemy 2 rows converted without requesting mapping results
15. Potentially unbounded schedule responses

### Corrections made

- Replaced SQL interpolation with bound parameters
- Used authenticated patient and doctor identities
- Added typed, timezone-aware datetime validation
- Rejected past appointment times
- Added managed connections and transactions
- Added rollback and integrity-error handling
- Returned appropriate HTTP statuses
- Used typed date ranges instead of string prefix matching
- Used SQLAlchemy mapping results
- Required a database uniqueness constraint for concurrency safety

## Assumptions and time-box decisions

- Doctors and their availability are seeded because doctor administration was outside the required booking flow.
- Public registration creates patient accounts only.
- Appointment slots are 30 minutes long.
- All appointment timestamps are stored as timezone-aware values.
- Cancellation changes the appointment status instead of deleting the record.
- The doctor schedule displays booked appointments for the next seven days.
- The frontend intentionally prioritizes a complete workflow and clear feedback over extensive visual design.
- JWTs are stored in browser local storage for assignment simplicity. A production system should use short-lived tokens with secure HTTP-only refresh cookies.
- PostgreSQL was containerized, while backend and frontend Dockerfiles were not prioritized over correctness, testing, migrations and documentation.

## Improvements with more time

- Use a dedicated PostgreSQL test database and automated fixtures
- Add broader authentication and authorization tests
- Add doctor availability management
- Add appointment rescheduling and completion workflows
- Prevent patients from booking overlapping times with different doctors
- Add pagination and configurable schedule ranges
- Use secure refresh-token cookies
- Add structured logging and monitoring
- Add backend and frontend Dockerfiles
- Add a CI pipeline for tests, linting and frontend builds
- Add end-to-end browser tests
- Improve accessibility and mobile interaction