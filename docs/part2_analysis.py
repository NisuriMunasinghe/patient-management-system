from fastapi import APIRouter
from sqlalchemy import text
from app.db import engine
router = APIRouter()
@router.post("/appointments")
def book_appointment(patient_id: int, doctor_id: int, slot_time: str):
conn = engine.connect()
existing = conn.execute(
text(f"""
SELECT id FROM appointments
WHERE doctor_id = {doctor_id} AND slot_time = '{slot_time}'
AND status = 'booked'
""")
).fetchone()
if existing:
return {"error": "Slot already booked"}
conn.execute(
text(f"""
INSERT INTO appointments (patient_id, doctor_id, slot_time, status)
VALUES ({patient_id}, {doctor_id}, '{slot_time}', 'booked')
""")
)
return {"status": "booked"}
@router.get("/doctors/{doctor_id}/schedule")
def get_schedule(doctor_id: int, date: str = ""):
query = f"""
SELECT id, patient_id, slot_time, status
FROM appointments
WHERE doctor_id = {doctor_id} AND slot_time LIKE '{date}%'
ORDER BY slot_time
"""
conn = engine.connect()
result = conn.execute(text(query))
return [dict(row) for row in result]