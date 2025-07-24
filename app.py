from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn
import json
import tempfile
import os
import subprocess
from fastapi import File, UploadFile
from pydub import AudioSegment
import openai
import base64
import io

from assistant import AIAssistant
from models import Appointment

AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"

# Initialize the app
app = FastAPI(
    title="Health Assistant API",
    description="API for interacting with the AI Health Assistant",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the AI assistant
assistant = AIAssistant()

# Initialize OpenAI client
# Note: Set your API key as an environment variable or replace with your actual key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your_api_key_here")
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    transcribed_text: Optional[str] = None

class AppointmentCreate(BaseModel):
    user_id: str
    date_time: str  # ISO format
    purpose: str
    email: Optional[str] = None

class AppointmentUpdate(BaseModel):
    date_time: Optional[str] = None
    purpose: Optional[str] = None
    email: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: str
    user_id: str
    date_time: str
    purpose: str
    status: str
    email: Optional[str] = None

class VoiceRequest(BaseModel):
    user_id: str


# API endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message using the AI assistant"""
    try:
        response = assistant.process_query(request.message, request.user_id)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(appointment: AppointmentCreate):
    """Create a new appointment"""
    try:
        date_time = datetime.fromisoformat(appointment.date_time)
        new_appointment = assistant.health_assistant.create_appointment(
            user_id=appointment.user_id,
            date_time=date_time,
            purpose=appointment.purpose,
            email=appointment.email
        )
        return AppointmentResponse(
            id=new_appointment.id,
            user_id=new_appointment.user_id,
            date_time=new_appointment.date_time.isoformat(),
            purpose=new_appointment.purpose,
            status=new_appointment.status,
            email=new_appointment.email
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating appointment: {str(e)}")

@app.get("/appointments/{user_id}", response_model=List[AppointmentResponse])
async def get_appointments(user_id: str):
    """Get all appointments for a user"""
    try:
        appointments = assistant.health_assistant.get_appointments(user_id)
        return [
            AppointmentResponse(
                id=appt.id,
                user_id=appt.user_id,
                date_time=appt.date_time.isoformat(),
                purpose=appt.purpose,
                status=appt.status,
                email=appt.email
            ) for appt in appointments
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving appointments: {str(e)}")

@app.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(appointment_id: str, update_data: AppointmentUpdate):
    """Update an existing appointment"""
    try:
        update_dict = {}
        if update_data.date_time:
            update_dict["date_time"] = datetime.fromisoformat(update_data.date_time)
        if update_data.purpose:
            update_dict["purpose"] = update_data.purpose
        if update_data.email:
            update_dict["email"] = update_data.email
        
        updated = assistant.health_assistant.update_appointment(appointment_id, **update_dict)
        if not updated:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        return AppointmentResponse(
            id=updated.id,
            user_id=updated.user_id,
            date_time=updated.date_time.isoformat(),
            purpose=updated.purpose,
            status=updated.status,
            email=updated.email
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating appointment: {str(e)}")

@app.delete("/appointments/{appointment_id}", response_model=dict)
async def delete_appointment(appointment_id: str, reason: str = "User requested cancellation"):
    """Delete an appointment"""
    try:
        # First get the appointment to ensure it exists
        appointment = assistant.health_assistant.get_appointment(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        # Log cancellation reason
        assistant.health_assistant.log_cancellation_reason(appointment_id, reason)
        
        # Delete appointment
        success = assistant.health_assistant.delete_appointment(appointment_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete appointment")
            
        return {"message": "Appointment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting appointment: {str(e)}")
    
@app.post("/voice-to-text", response_model=ChatResponse)
async def voice_to_text(
    user_id: str, 
    audio_file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = None
):
    """Process voice input using OpenAI and convert to text for chat processing"""
    temp_input_path = None
    temp_path = None
    try:
        # Read the uploaded file content
        file_content = await audio_file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # Determine the input format from the filename
        input_format = audio_file.filename.split(".")[-1].lower()

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_input_path = os.path.join(tmp_dir, f"input.{input_format}")
            temp_path = os.path.join(tmp_dir, "audio.mp3")  # OpenAI prefers mp3

            # Save the uploaded content to the temporary input file
            with open(temp_input_path, "wb") as f:
                f.write(file_content)

            # Convert the audio to mp3 format for OpenAI
            try:
                ffmpeg_command = [
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-i", temp_input_path,
                    "-ac", "1",  # Mono channel
                    "-ar", "44100",  # 44.1kHz sample rate (good for OpenAI)
                    "-hide_banner",
                    "-loglevel", "error",
                    temp_path
                ]
                
                result = subprocess.run(
                    ffmpeg_command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"FFmpeg conversion failed: {result.stderr}"
                    )
                    
            except subprocess.CalledProcessError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio conversion failed: {e.stderr}"
                )

            # Verify the converted file exists
            if not os.path.exists(temp_path):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create converted audio file"
                )

            # Use OpenAI to transcribe the audio
            try:
                with open(temp_path, "rb") as audio_file:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                text = transcript.text
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"OpenAI transcription error: {str(e)}"
                )

        # Process the transcribed text through the AI assistant
        response = assistant.process_query(text, user_id)
        return ChatResponse(
            response=response,
            transcribed_text=text
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        # Cleanup temporary files
        for path in [temp_input_path, temp_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass


class ImageAnalysisRequest(BaseModel):
    user_id: str
    prompt: Optional[str] = "What do you see in this image?"

class ImageAnalysisResponse(BaseModel):
    analysis: str

class ImageAnalysisRequest(BaseModel):
    user_id: str
    prompt: Optional[str] = "What do you see in this image?"

class ImageAnalysisResponse(BaseModel):
    analysis: str

@app.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(
    user_id: str,
    prompt: str = "What do you see in this medical image?",
    image_file: UploadFile = File(...)
):
    """Analyze a medical image using OpenAI's vision capabilities"""
    try:
        # Read the uploaded file content
        file_content = await image_file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
        # Encode image to base64
        encoded_image = base64.b64encode(file_content).decode("utf-8")
        
        # Determine mime type based on file extension
        file_extension = image_file.filename.split(".")[-1].lower()
        mime_type = f"image/{file_extension}"
        if file_extension == "jpg" or file_extension == "jpeg":
            mime_type = "image/jpeg"
        elif file_extension == "png":
            mime_type = "image/png"
        elif file_extension == "webp":
            mime_type = "image/webp"
        
        # Create message payload with system prompt, user text, and image
        messages = [
            {
                "role": "system", 
                "content": "You are a medical assistant who can analyze medical images. "
                           "Provide accurate, professional analysis of medical imagery. "
                           "Always note when findings are uncertain and recommend professional "
                           "medical consultation for definitive diagnosis."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"}}
                ],
            }
        ]
        
        # Make API request to OpenAI
        completion = openai_client.chat.completions.create(
            model="gpt-4-turbo",  # Use the vision-enabled model
            messages=messages,
            max_tokens=500
        )
        
        # Extract analysis from response
        analysis = completion.choices[0].message.content

        
        # Save the conversation with context about the image
        assistant.health_assistant.save_conversation(
            user_id, 
            "user", 
            f"[Uploaded an image with prompt: {prompt}]"
        )
        assistant.health_assistant.save_conversation(
            user_id, 
            "assistant", 
            f"[Image analysis]: {analysis}"
        )
        
        return ImageAnalysisResponse(analysis=analysis)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis error: {str(e)}")

# Run the application
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)