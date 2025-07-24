from langchain.agents import AgentExecutor
from langchain.tools import StructuredTool
from langchain.agents import create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage  # Import message classes
from models import HealthAssistant, Appointment
from datetime import datetime
import os
from dotenv import load_dotenv
from utils import parse_natural_date, send_email
from pydantic import BaseModel, Field
import re

load_dotenv()

class CreateAppointmentInput(BaseModel):
    date_time: str = Field(..., description="Appointment datetime in ISO format")
    purpose: str = Field(..., description="Purpose of the appointment")
    email: str = Field(..., description="Email address for confirmation")

class UpdateAppointmentInput(BaseModel):
    appointment_id: str = Field(..., description="ID of the appointment to update")
    date_time: str = Field(None, description="New datetime in ISO format")
    purpose: str = Field(None, description="New purpose for appointment")
    email: str = Field(None, description="New email address for notifications")

class DeleteAppointmentInput(BaseModel):
    appointment_id: str = Field(..., description="ID of the appointment to delete")
    confirmation: bool = Field(..., description="Confirmation to delete (true/false)")
    reason: str = Field(..., description="Reason for cancellation")

class ListAppointmentsInput(BaseModel):
    user_id: str = Field(..., description="User ID to list appointments for")

class AIAssistant:
    def __init__(self):
        self.health_assistant = HealthAssistant()
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
        self.current_user_id = None  # Kept for compatibility, but we'll use self.user_id
        self.tools = self._setup_tools()
        self.agent = self._setup_agent()
    
    def _setup_tools(self):
        return [
            StructuredTool.from_function(
                name="update_appointment",
                func=self._update_appointment_wrapper,
                description="Update existing appointment. Parameters: appointment_id, date_time (optional ISO), purpose (optional), email (optional)",
                args_schema=UpdateAppointmentInput
            ),
            StructuredTool.from_function(
                name="delete_appointment",
                func=self._delete_appointment_wrapper,
                description="Delete appointment. Parameters: appointment_id, confirmation (true/false), reason",
                args_schema=DeleteAppointmentInput
            ),
            StructuredTool.from_function(
                name="list_appointments",
                func=self._list_appointments_wrapper,
                description="List all appointments for a user. Requires: user_id",
                args_schema=ListAppointmentsInput
            ),
            StructuredTool.from_function(
                name="create_appointment",
                func=self._create_appointment_wrapper,
                description="Create new appointment. Parameters: date_time (ISO format), purpose, email",
                args_schema=CreateAppointmentInput
            ),
        ]
    
    def _setup_agent(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional medical assistant. Help users with medical queries and appointment management.
            Current user ID: {user_id}
            Current date: {current_date}
            Follow these rules:
            1. For appointment listing requests, ALWAYS use the list_appointments tool
            2. When showing appointments, include dates/times in user's local format
            3. Maintain conversational tone
            4. For appointment cancellations, ALWAYS:
               - Ask for confirmation before proceeding
               - Only proceed with deletion when confirmation is true
            5. For appointment bookings, ALWAYS:
               - Ask for the user's email address
               - Inform them they will receive a confirmation email
               - Verify the email format looks valid
            6. Only give responses to medical related queries"""),
            
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ]) 
        return AgentExecutor(agent=create_openai_tools_agent(self.llm, self.tools, prompt), tools=self.tools)

    def _validate_email(self, email: str) -> bool:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    def _create_appointment_wrapper(self, date_time: str, purpose: str, email: str) -> str:
        try:
            if not self._validate_email(email):
                return "Invalid email format. Please provide a valid email address."
            user_id = self.user_id  # Changed from self.current_user_id
            dt = datetime.fromisoformat(date_time)
            appointment = self.health_assistant.create_appointment(
                user_id=user_id, 
                date_time=dt, 
                purpose=purpose,
                email=email
            )
            email_subject = "Appointment Confirmation"
            email_body = f"""
            Dear Patient,
            Your appointment has been confirmed:
            Date: {dt.strftime('%A, %B %d, %Y')}
            Time: {dt.strftime('%I:%M %p')}
            Purpose: {purpose}
            Appointment ID: {appointment.id}
            If you need to reschedule or cancel, please contact us with your appointment ID.
            Thank you,
            Health Assistant Team
            """
            send_email(to_email=email, subject=email_subject, body=email_body)
            return f"Appointment created: {dt.strftime('%Y-%m-%d %H:%M')} - {purpose} (ID: {appointment.id}). Confirmation email sent to {email}."
        except Exception as e:
            return f"Error creating appointment: {str(e)}"

    def _update_appointment_wrapper(self, appointment_id: str, date_time: str = None, purpose: str = None, email: str = None) -> str:
        try:
            existing_appointment = self.health_assistant.get_appointment(appointment_id)
            if not existing_appointment:
                return "Appointment not found"
            # Optional: Check ownership
            if existing_appointment.user_id != self.user_id:
                return "You don't have permission to update this appointment."
            update_data = {}
            if date_time:
                update_data["date_time"] = datetime.fromisoformat(date_time)
            if purpose:
                update_data["purpose"] = purpose
            if email:
                if not self._validate_email(email):
                    return "Invalid email format. Please provide a valid email address."
                update_data["email"] = email
            updated = self.health_assistant.update_appointment(appointment_id, **update_data)
            if updated:
                notification_email = email or getattr(existing_appointment, 'email', None)
                if notification_email:
                    updated_appointment = self.health_assistant.get_appointment(appointment_id)
                    email_subject = "Appointment Update Notification"
                    email_body = f"""
                    Dear Patient,
                    Your appointment has been updated:
                    Date: {updated_appointment.date_time.strftime('%A, %B %d, %Y')}
                    Time: {updated_appointment.date_time.strftime('%I:%M %p')}
                    Purpose: {updated_appointment.purpose}
                    Appointment ID: {appointment_id}
                    If you need to make further changes, please contact us with your appointment ID.
                    Thank you,
                    Health Assistant Team
                    """
                    send_email(to_email=notification_email, subject=email_subject, body=email_body)
                    return f"Updated appointment {appointment_id}. Update notification sent to {notification_email}."
                return f"Updated appointment {appointment_id}"
            else:
                return "Appointment not found or no changes were made"
        except Exception as e:
            return f"Error updating appointment: {str(e)}"

    def _delete_appointment_wrapper(self, appointment_id: str, confirmation: bool, reason: str) -> str:
        try:
            appointment = self.health_assistant.get_appointment(appointment_id)
            if not appointment:
                return "Appointment not found"
            # Optional: Check ownership
            if appointment.user_id != self.user_id:
                return "You don't have permission to delete this appointment."
            if not confirmation:
                return "Cancellation aborted: Confirmation was negative"
            if not reason or reason.strip() == "":
                return "Cancellation requires a reason. Please provide a reason for cancelling this appointment."
            email = getattr(appointment, 'email', None)
            self.health_assistant.log_cancellation_reason(appointment_id, reason)
            success = self.health_assistant.delete_appointment(appointment_id)
            if success:
                appt_date = appointment.date_time.strftime('%Y-%m-%d %H:%M')
                if email:
                    email_subject = "Appointment Cancellation Confirmation"
                    email_body = f"""
                    Dear Patient,
                    Your appointment has been cancelled:
                    Date: {appointment.date_time.strftime('%A, %B %d, %Y')}
                    Time: {appointment.date_time.strftime('%I:%M %p')}
                    Purpose: {appointment.purpose}
                    Reason for cancellation: {reason}
                    If you wish to reschedule, please contact us.
                    Thank you,
                    Health Assistant Team
                    """
                    send_email(to_email=email, subject=email_subject, body=email_body)
                    return f"Appointment cancelled: {appt_date} - {appointment.purpose}\nReason: {reason}\nCancellation notification sent to {email}."
                return f"Appointment cancelled: {appt_date} - {appointment.purpose}\nReason: {reason}"
            else:
                return "Error occurred during cancellation"
        except Exception as e:
            return f"Error deleting appointment: {str(e)}"

    def process_query(self, user_input: str, user_id: str) -> str:
        user_id = self.current_user_id or user_id
        parsed_date = None
        if any(keyword in user_input.lower() for keyword in ["appointment", "schedule", "book"]):
            try:
                parsed_date = parse_natural_date(user_input)
            except:
                pass
        self.user_id = user_id  # Set user_id for tools to access
        # Convert conversation history to message objects
        chat_history = self.health_assistant.conversation_history.get(user_id, [])
        chat_history_messages = [
            HumanMessage(content=msg) if role == "user" else AIMessage(content=msg)
            for role, msg in chat_history
        ]
        context = {
            "input": user_input,
            "user_id": user_id,
            "current_date": datetime.now().isoformat(),
            "chat_history": chat_history_messages  # Pass formatted messages
        }
        if parsed_date:
            context["detected_date"] = parsed_date.isoformat()
        response = self.agent.invoke(context)
        self.health_assistant.save_conversation(user_id, "user", user_input)
        self.health_assistant.save_conversation(user_id, "assistant", response["output"])
        return response["output"]
        
    def _list_appointments_wrapper(self, user_id: str) -> str:
        try:
            user_id = self.user_id or user_id  # Use self.user_id if set
            appointments = self.health_assistant.get_appointments(user_id)
            if not appointments:
                return "No appointments found"
            formatted = []
            for appt in appointments:
                formatted.append(
                    f"- {appt.date_time.strftime('%Y-%m-%d %H:%M')}: "
                    f"{appt.purpose} (ID: {appt.id})"
                )
            return "Your appointments:\n" + "\n".join(formatted)
        except Exception as e:
            return f"Error retrieving appointments: {str(e)}"
