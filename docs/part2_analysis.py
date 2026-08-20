"""
Part 2: Reviwing the original code.
This has original code with added comments about issues
"""
from fastapi import APIRouter
from sqlalchemy import text
from app.db import engine

router = APIRouter()

@router.post("/appointments")
def book_appointment(patient_id: int, doctor_id: int, slot_time: str):
    # Problem1 : The patient ID is accepted directly from the request
    # A patient can provide another patient's ID and book an appointment for them
    # As correction we should get the patient ID from the authenticated user instead of accepting it from the request
    # 
    # Problem2 : slot_time as string. Not validated as datetime
    # Invalid values or past times can reach database.
    # Correction: Use Pydantic model with AwareDatetime. Reject past times.
    #
    # Problem3: No checking of patients, doctors or availability.
    # IDs might not exist. time might not be available timeslot of doctor.
    # Correction: Verify the referenced entities. and requre a predefined availability timeslot.
conn = engine.connect()
    # Opened without a context manager. Not explicitly closed after.
existing = conn.execute(
text(f"""
SELECT id FROM appointments
WHERE doctor_id = {doctor_id} AND slot_time = '{slot_time}'
AND status = 'booked'
""")
).fetchone()
# slot_time can contain malicious SQL since f-string is used. can use parameterized SQL instead.
# Two concurrent requests can both execute SELECT before INSERT
if existing:
    #Returning an error dictionary does not set an error status.
    #FastAPI returns 200 OK even though request failed.
    # Correction: Raise HTTPException with 409 status code and a consistent error body
return {"error": "Slot already booked"}
conn.execute(
text(f"""
INSERT INTO appointments (patient_id, doctor_id, slot_time, status)
VALUES ({patient_id}, {doctor_id}, '{slot_time}', 'booked')
""")
)
#Insert uses direct string
#transaction is not commited
#Exceptions are not handled
return {"status": "booked"}


@router.get("/doctors/{doctor_id}/schedule")
def get_schedule(doctor_id: int, date: str = ""):
    # Any caller can request another doctor's schedule. Should require authentication and authorization.
    #date is an unvalidated string.
query = f"""
SELECT id, patient_id, slot_time, status
FROM appointments
WHERE doctor_id = {doctor_id} AND slot_time LIKE '{date}%'
ORDER BY slot_time
"""
#Uses direct string interpolation. 
# LIKE is not a reliable filter.
conn = engine.connect()
#Never closes
result = conn.execute(text(query))
#Returns a list of dictionaries. No Pydantic model is used. No validation or serialization.
return [dict(row) for row in result]