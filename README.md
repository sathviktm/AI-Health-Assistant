# AI Health Assistant

The Health Assistant API is a comprehensive web application designed to provide users with a personal AI-powered healthcare companion. It allows users to interact with an AI assistant for medical queries, manage appointments, process voice inputs, and analyze medical images using advanced AI capabilities.

## Features

- **Chat Interface**: Engage in real-time conversations with an AI health assistant for medical queries.
- **Voice-to-Text**: Convert voice inputs to text using OpenAI's Whisper model for seamless interaction.
- **Image Analysis**: Upload and analyze medical images with OpenAI's vision capabilities, providing professional analysis with a recommendation for medical consultation.
- **Appointment Management**: Create, update, delete, and list appointments with email notifications.
- **Responsive UI**: A user-friendly interface built with Tailwind CSS for accessibility across devices.
- **Secure and Scalable**: Built with FastAPI, ensuring high performance and scalability.

## Technologies Used

- **Backend**:
  - FastAPI: High-performance web framework for building APIs.
  - LangChain: For building AI agents and managing conversation flows.
  - OpenAI API: For natural language processing, voice transcription, and image analysis.
  - Pydantic: For data validation and serialization.
  - FFmpeg: For audio file conversion.
  - Pyodub: For audio processing.
- **Frontend**:
  - HTML/CSS/JavaScript: Core web technologies.
  - Tailwind CSS: Utility-first CSS framework for styling.
  - Marked.js: For rendering markdown in chat responses.
  - Font Awesome: For icons.
- **Other**:
  - SMTP: For sending email notifications.
  - UUID: For generating unique appointment IDs.
  - Python-dateutil: For parsing natural language dates.

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/surya7856/AI_Health_Assistant.git
   ```

2. **Install Dependencies**: Ensure you have Python 3.8+ installed. Then, install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**: FFmpeg is required for audio processing. Install it based on your operating system:

   - **MacOS**:

     ```bash
     brew install ffmpeg
     ```

   - **Ubuntu**:

     ```bash
     sudo apt-get install ffmpeg
     ```

   - **Windows**: Download and install from FFmpeg's official site.

4. **Set Up Environment Variables**: Create a `.env` file in the project root and add the following:

   ```env
   OPENAI_API_KEY=your_openai_api_key
   EMAIL_SENDER=your_email@example.com
   SMTP_PASSWORD=your_smtp_password
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

   Replace the placeholders with your actual credentials.

## Configuration

- **OpenAI API Key**: Obtain an API key from OpenAI and set it in the `.env` file.

- **SMTP Credentials**: Configure your email service (e.g., Gmail) credentials for sending appointment notifications.

- **Audio Processing**: Ensure FFmpeg is correctly configured by setting the path in `app.py`:

  ```python
  AudioSegment.converter = "/path/to/ffmpeg"
  ```

## Usage

1. **Run the Backend**: Start the FastAPI server:

   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be accessible at `http://localhost:8000`.

2. **Access the Frontend**: Open `index.html` in a web browser or serve it using a local server (e.g., with `python -m http.server 8001`). The default API URL in `index.html` Update it to `http://localhost:8000` for local development:

   ```javascript
   const API_URL = "http://localhost:8000";
   ```

3. **Interact with the Application**:

   - **Chat**: Type or record messages to interact with the AI assistant.
   - **Appointments**: Schedule, edit, or delete appointments via the appointments tab.
   - **Image Analysis**: Upload medical images for AI-driven analysis.
   - **Voice Input**: Use the microphone to send voice messages, which are transcribed and processed.

## API Endpoints

The API provides the following endpoints:

- **POST /chat**: Process text-based chat messages.

  ```json
  {
    "user_id": "string",
    "message": "string"
  }
  ```

- **POST /voice-to-text**: Process voice input and convert to text.

  - Accepts multipart/form-data with an `audio_file`.

- **POST /analyze-image**: Analyze uploaded medical images.

  - Accepts multipart/form-data with an `image_file` and optional `prompt`.

- **POST /appointments**: Create a new appointment.

  ```json
  {
    "user_id": "string",
    "date_time": "ISO string",
    "purpose": "string",
    "email": "string"
  }
  ```

- **GET /appointments/{user_id}**: Retrieve all appointments for a user.

- **PUT /appointments/{appointment_id}**: Update an existing appointment.

  ```json
  {
    "date_time": "ISO string",
    "purpose": "string",
    "email": "string"
  }
  ```

- **DELETE /appointments/{appointment_id}**: Delete an appointment.

For detailed API documentation, access the interactive Swagger UI at `http://localhost:8000/docs` when the server is running.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please ensure your code follows the project's coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
