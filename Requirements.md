Prototype

Project Name: AI Companion "Squishy"

Overview
"Squishy" is a physical AI companion designed to bridge the gap between digital assistance and physical interaction. Unlike standard voice assistants, Squishy possesses "sensory awareness." It understands its physical environment—whether it is being held, shaken, or placed in the dark—and adapts its personality and responses accordingly.

The system operates on a hybrid architecture:

The Body (Hardware): A Raspberry Pi-based device wrapped in a tactile shell. It uses a ReSpeaker array for voice interaction and a modular sensor suite to track its physical state.

The Mind (Server): A centralized Python-based "Brain" running on a Hetzner server (alongside PocketBase), utilizing Google Gemini 1.5 Flash for multimodal reasoning (Text + Audio).

The Interface (PWA): A Vue.js-based web app for managing conversations, viewing chat history, and manual interaction.

Core User Experience
Users can interact with Squishy via natural voice commands (Wake Word) or through the mobile app. The AI maintains a continuous identity across both platforms. Crucially, the AI's responses are context-aware. If Squishy is shaken, it might react with chaos or excitement. If the lights go out, it whispers. The system also features a "Long-Term Memory," allowing it to remember user details over time, creating a deepening bond.

Part 2: Requirements Engineering Specification
1. System Architecture

- Architecture Pattern: Client-Server-Client (Hardware <-> Backend <-> Web App).
- Backend: PocketBase (Golang/SQLite) for data persistence, auth, and realtime subscriptions.
- AI Service: Python Orchestrator running as a server-side worker.
- LLM: Google Gemini 3 Flash (Handling Text & Native Audio).
- TTS: OpenAI TTS or Google gTTS (for voice output).
- Deployment: Dockerized environment

2. Functional Requirements
2.1 User Interface (Frontend / PWA)

Framework: Vue 3 + Vite + PrimeVue.

Platform: Progressive Web App (Installable on iOS/Android).

Authentication:

User Login & Registration (Email/Password).

Password Reset functionality.

Chat Interface:

Real-time chat history synchronization (Text & Audio players).

Ability to record/upload audio messages.

Scope Exclusion: No image generation or image recognition support in the UI for this phase.

Conversation Management:

List view of multiple conversations.

Ability to create new chats.

Active Context: Only one conversation is flagged as is_active at a time. The hardware always interacts with the currently active conversation.

2.2 Backend & AI Logic ("The Brain")

Event Handling: The Python script must listen to PocketBase messages events in real-time.

Context Injection: Before sending a user message to the LLM, the Brain must check the metadata JSON attached to the message (containing sensor states) and inject a System Prompt modification (e.g., "User is shaking you").

Audio Processing:

Must accept raw audio files (WAV/M4A/MP3).

Must generate audio responses (TTS) and upload them back to the database.

Long-Term Memory:

The system must extract relevant facts from conversations and store them in a structured format (e.g., user_facts collection) to persist context across different chat sessions.

2.3 Hardware Logic ("The Body")

Platform: Raspberry Pi with ReSpeaker Hat (Mic Array).

Wake Word: Local processing (e.g., openWakeWord) to detect activation phrases without cloud latency.

Interaction Flow:

Detect Wake Word -> Start Recording.

User Speaks -> Stop Recording (VAD or Silence Detection).

Data Package: Bundle Audio + Current Sensor State Metadata.

Send to Backend -> Wait for ai response.

Download Response Audio -> Play via Speaker.

Special State (Face Down): If the device is placed face down, it ignores the active chat context and enters a "Sleep/Muted" mode or specific context.

2.4 Sensor Module Architecture

Modularity: Each sensor (Gyro, Light, Touch, etc.) must run as an independent module/thread.

Resilience: If one sensor driver fails/crashes, the error must be logged, but the main application loop must continue (Graceful Degradation).

State Management:

Sensors write their status to a local "Current State" store (in-memory object or semi-persistent file) whenever a change occurs.

Polling/Interrupts: Sensors update at appropriate intervals (e.g., Light sensor checks every 1s, Gyro checks continuously for interrupt).

Transmission: The state is not streamed continuously. It is only read and sent as metadata when an audio/text event is triggered.

3. Sensor & Data Definitions
3.1 Sensor States (Metadata Schema)

The hardware will track and send the following JSON structure with every message. Note: For the start, these values may be simulated (mocked).

Sensor / State	Type	Values / Logic
Brightness	Enum	dark, dim, normal, bright (Derived from lux sensor)
Shaken	Bool	true if accelerometer variance exceeds threshold within last 2s.
Squished	Bool	true if pressure sensor detects force.
Touched	Bool	true if capacitive touch is active.
Eyes Covered	Bool	true if specific light sensor/proximity sensor is blocked.
Face Down	Bool	true if gyroscope orientation indicates downward position.
3.2 Data Flow Example

Light Module: Reads 10 lux -> Updates local state: brightness = "dark".

Gyro Module: Detects vibration -> Updates local state: shaken = true.

User: Says "Wake Word".

Main Loop: Captures Audio. Reads Local State {'brightness': 'dark', 'shaken': true, ...}.

Upload: Sends Audio + Metadata to PocketBase.

Backend: Brain sees shaken=true -> Instructs LLM: "You are being shaken! Respond chaotically."

4. Non-Functional Requirements

Latency: Voice-to-Voice response time should be minimized (Target < 3 seconds).

Privacy: Audio is only recorded and transmitted after Wake Word detection or manual activation.

Scalability: The architecture must allow moving from Localhost to Hetzner Cloud via Docker without code changes.

----

Live Chat im Chatinterface, mit Sprach konversation.
Bilder generieren oder erkennen ist nicht unterstüzt erstmal!
Audio als datei oder Aufnahme ist unterstützt oder sogar als conversation, weil das mit dem pie angedacht ist.

Mehrere chats, ein chat ist maximal auf einmal aktiv.

der letzte chat der aktiv war ist der kontext den squishy übernimmt, außer er liegt auf dem Gesicht ...

Es gibt eine memory funktion, die KI sammelt infos und speichert sich für long term memory ab.

Login Registration, Passwort reset.

Hardware:
Diverse sensoren, 
wake word mit respeaker
dann aufnahme erstmal machen und senden, später vielleicht als live stream
sensoren sollten als module eingebunden werden, die im temp memory spichern, was sie gesehen haben, also wenn es dunkel ist wird das abgespeichert mit einem timestamp, oder wenn die hardware geschüttelt wird, dann auch shaken und timestamp. Wenn der nutzer das wakeword sagt wird das auch mit einem timestamp abgespeichert. Dann kann der nutzer seine eingabe machen. Dann wird alles an das Backend gesendet, als metadaten und content. Der Zustand der hardware wird immer mitgesendet.
Jeder Sensor kann also durchgehend oder in einem intervall die sensordaten auslesen. Ein helligkeitssensor, muss vielleicht nur jede Sekunde die helligkeit überprüfen. In einer lokalen datei oder vielleicht auch einfach im ram, oder einem semipesistenten Store werden die aktuellen zustände der sensoren gespeichert.
Jeder Sensor sagt einfach immer wenn er eine änderung hatte und speichert sie da ab.
Dann steht da z.b. brightness = dark, shaken = false, face_down = false,
Der Gyro sensor überprüft ob er geschüttelt wird und wenn dann speichert er es ab, wenn dann nicht mehr geschüttelt wird, dann schreibt er wieder skahen = false.

Die Hardware sollte möglichst robust und voneinander unabhänig laufen. Also wenn ein Sensor ausfällt, dann sollte dass geloggt werden aber alles andere sollte weiterhin funktionieren.

nachdem ein wakeword gesendet wurde wartet die hardware erstmal auf die antwort des backends bevor sie diese Antwort dann alss audio ausgibt.

Für den start werden die sensor eingaben erstmal nur als random values gesetzt.
Es gibt. brightness, shaken, sqhished, touched, face_down, eyes_covered, 
Bei brightness gibt es vier abstufungen, beim rest erstmal nur true false

