from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import uuid

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date_time: datetime
    purpose: str
    status: str = "scheduled"
    email: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date_time": self.date_time,
            "purpose": self.purpose,
            "status": self.status,
            "email": self.email
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            date_time=data["date_time"],
            purpose=data["purpose"],
            status=data["status"],
            email=data.get("email")
        )

class HealthAssistant:
    def __init__(self):
        self.appointments = {}
        self.conversation_history = {}  # Changed to dictionary: user_id -> list of (role, content)
        self.cancellations = {}
    
    def save_conversation(self, user_id: str, role: str, content: str):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append((role, content))
        
    def create_appointment(self, user_id: str, date_time: datetime, purpose: str, email: str = None) -> Appointment:
        appointment = Appointment(user_id=user_id, date_time=date_time, purpose=purpose, email=email)
        self.appointments[appointment.id] = appointment
        return appointment

    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        return self.appointments.get(appointment_id)

    def update_appointment(self, appointment_id: str, **kwargs) -> Optional[Appointment]:
        appointment = self.appointments.get(appointment_id)
        if not appointment:
            return None
        for key, value in kwargs.items():
            setattr(appointment, key, value)
        return appointment

    def log_cancellation_reason(self, appointment_id: str, reason: str) -> bool:
        self.cancellations[appointment_id] = {
            "reason": reason,
            "timestamp": datetime.now()
        }
        return True

    def delete_appointment(self, appointment_id: str) -> bool:
        if appointment_id not in self.appointments:
            return False
        del self.appointments[appointment_id]
        return True
        
    def get_appointments(self, user_id: str) -> List[Appointment]:
        return [appt for appt in self.appointments.values() if appt.user_id == user_id]