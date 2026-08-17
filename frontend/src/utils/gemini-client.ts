// FILE: src/utils/gemini-client.ts

import { ref, type Ref } from 'vue';

// Define expected event types based on your backend models
interface BaseEvent {
  type: string;
  timestamp: string; // ISO string
}

interface RegisterEvent extends BaseEvent {
  type: "register";
  client_type: "frontend" | "hardware" | "monitor";
  capabilities: string[]; // ClientCapability enum values as strings
  username?: string;
  participant_id?: string;
}

interface RegistrationAckEvent extends BaseEvent {
  type: "registration_ack";
  client_id: string;
  message: string;
  active_controller_id?: string;
  current_active_controller_type?: "frontend" | "hardware" | "monitor";
  routing_config?: {
    hardware_mic_enabled: boolean;
    hardware_speaker_enabled: boolean;
    ui_text_mode_enabled: boolean;
  };
}

interface ActiveControllerChangeEvent extends BaseEvent {
  type: "active_controller_change";
  new_active_controller_id: string;
  new_active_controller_type: "frontend" | "hardware" | "monitor";
  old_active_controller_id?: string;
  old_active_controller_type?: "frontend" | "hardware" | "monitor";
}

interface TranscriptEvent extends BaseEvent {
  type: "transcript";
  text: string;
  is_final: boolean;
}

// NOTE: This AudioOutputEvent is for internal tracking, not for direct data transfer in onMessage.
// The raw ArrayBuffer is passed directly.
// interface AudioOutputEvent extends BaseEvent {
//   type: "audio_output";
//   data: ArrayBuffer; // Raw audio bytes
// }

interface AudioInterruptEvent extends BaseEvent {
  type: "audio_interrupt";
  message: string;
}

interface ToolCallEvent extends BaseEvent {
  type: "tool_call";
  tool_call_id: string;
  tool_name: string;
  args: Record<string, any>;
  suggested_action?: "execute" | "simulate" | "visualize";
}

interface AIResponseEvent extends BaseEvent {
  type: "ai_response";
  text: string;
}

interface ErrorEvent extends BaseEvent {
  type: "error";
  message: string;
  code?: number;
}

interface SystemMessageEvent extends BaseEvent {
  type: "system_message";
  message: string;
}

interface SessionResetEvent extends BaseEvent {
  type: "session_reset";
  message: string;
}

interface TurnCompleteEvent extends BaseEvent {
  type: "turn_complete";
}

interface SensorObservedEvent extends BaseEvent {
  type: "sensor_event_observed";
  sensor_id: string;
  event?: string;
  value?: any;
  intensity?: string;
  source_client_type?: "frontend" | "hardware" | "monitor";
  mapped_gesture?: string;
}

interface SystemCommandEvent extends BaseEvent {
  type: "system_command";
  command: string;
  target?: string;
  payload?: Record<string, any>;
}

// All possible incoming JSON events from the backend
type IncomingBackendJsonEvent =
  | RegistrationAckEvent
  | ActiveControllerChangeEvent
  | TranscriptEvent
  | AudioInterruptEvent
  | ToolCallEvent
  | AIResponseEvent
  | ErrorEvent
  | SystemMessageEvent
  | SessionResetEvent
  | TurnCompleteEvent
  | SensorObservedEvent
  | SystemCommandEvent;


// Client capabilities (matching backend enum `ClientCapability`)
const FRONTEND_CAPABILITIES = [
  "audio_input",
  "audio_output",
  "text_input",
  "text_output",
  "tool_visualization",
  "sensor_simulation",
  "transcription_view",
  "ai_response_view"
];

interface GeminiClientConfig {
  wsUrl: string;
  onOpen: () => void;
  // Change onMessage signature: now receives either parsed JSON object or raw ArrayBuffer
  onMessage: (data: IncomingBackendJsonEvent | ArrayBuffer) => void;
  onClose: (event: CloseEvent) => void;
  onError: (event: Event) => void;
  clientType: "frontend" | "hardware" | "monitor";
  capabilities: string[];
  username?: string;
  participantId?: string;
}

function defaultWsUrl(): string {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/ws';
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/ws`;
}

export class GeminiClient {
  private ws: WebSocket | null = null;
  private config: GeminiClientConfig;
  private _isConnected = ref(false);
  private _clientId: Ref<string | null> = ref(null);
  private _activeControllerId: Ref<string | null> = ref(null);
  private _activeControllerType: Ref<"frontend" | "hardware" | "monitor" | null> = ref(null);
  private _pendingJsonMessages: string[] = [];

  constructor(config: Partial<GeminiClientConfig>) {
    this.config = {
      wsUrl: defaultWsUrl(),
      onOpen: () => console.log('WebSocket opened.'),
      onMessage: (data) => { // Default onMessage now expects parsed data or ArrayBuffer
        if (data instanceof ArrayBuffer) {
          console.log('WebSocket audio message:', data);
        } else {
          console.log('WebSocket JSON message:', data);
        }
      },
      onClose: (event) => console.log('WebSocket closed:', event),
      onError: (event) => console.error('WebSocket error:', event),
      clientType: "frontend", // Default to frontend
      capabilities: FRONTEND_CAPABILITIES, // Default capabilities
      username: undefined,
      participantId: undefined,
      ...config,
    };
  }

  public isConnected(): boolean {
    return this._isConnected.value;
  }

  public get clientId(): string | null {
    return this._clientId.value;
  }

  public get activeControllerId(): string | null {
    return this._activeControllerId.value;
  }

  public get activeControllerType(): "frontend" | "hardware" | "monitor" | null {
    return this._activeControllerType.value;
  }
  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      console.warn('WebSocket is already connected or connecting.');
      return;
    }

    this.ws = new WebSocket(this.config.wsUrl);

    this.ws.onopen = (_event) => {
      console.log("WebSocket connected. Sending registration...");
      this._isConnected.value = true;
      this.registerClient();
      this.config.onOpen();
    };

    this.ws.onmessage = async (event) => { // <<< Make onmessage async to handle Blob.arrayBuffer() promise
      // Prioritize Blob for audio data (if backend sends Blob)
      if (event.data instanceof Blob) {
        try {
          const arrayBuffer = await event.data.arrayBuffer(); // Convert Blob to ArrayBuffer
          this.config.onMessage(arrayBuffer); // Pass raw ArrayBuffer
        } catch (e) {
          console.error("Failed to convert Blob to ArrayBuffer:", e, event.data);
        }
        return; // Don't try to parse as JSON
      }

      // Handle raw ArrayBuffer directly (if backend sends ArrayBuffer)
      if (event.data instanceof ArrayBuffer) {
        this.config.onMessage(event.data); // Pass raw ArrayBuffer
        return; // Don't try to parse as JSON
      }

      // If not Blob or ArrayBuffer, try to parse as JSON string
      if (typeof event.data === 'string') {
        try {
          const parsedData: IncomingBackendJsonEvent = JSON.parse(event.data);
          console.log("Received backend JSON event:", parsedData);

          if (parsedData.type === "registration_ack") {
            const ack = parsedData as RegistrationAckEvent;
            this._clientId.value = ack.client_id;
            this._activeControllerId.value = ack.active_controller_id || null;
            this._activeControllerType.value = ack.current_active_controller_type || null;
            console.log(`Registered as ${this.config.clientType} with ID ${this._clientId.value}. Active Controller: ${this._activeControllerType.value} (${this._activeControllerId.value})`);
            this.flushPendingJsonMessages();
          } else if (parsedData.type === "active_controller_change") {
            const change = parsedData as ActiveControllerChangeEvent;
            this._activeControllerId.value = change.new_active_controller_id;
            this._activeControllerType.value = change.new_active_controller_type;
            console.log(`Active controller changed to: ${change.new_active_controller_type} (${change.new_active_controller_id})`);
          }
          // Delegate parsed JSON object to the component's onMessage
          this.config.onMessage(parsedData);

        } catch (e) {
          console.error("Failed to parse WebSocket message as JSON:", e, event.data);
        }
      } else {
        console.warn("Received unexpected WebSocket message type (neither Blob, ArrayBuffer, nor string):", typeof event.data, event.data);
      }
    };

    this.ws.onclose = (event) => {
      this._isConnected.value = false;
      this._clientId.value = null;
      this._activeControllerId.value = null;
      this._activeControllerType.value = null;
      this._pendingJsonMessages = [];
      this.config.onClose(event);
    };

    this.ws.onerror = (event) => {
      console.error('WebSocket error occurred:', event);
      this._isConnected.value = false;
      this._clientId.value = null;
      this._activeControllerId.value = null;
      this._activeControllerType.value = null;
      this._pendingJsonMessages = [];
      this.config.onError(event);
    };
  }

  private sendOrQueueJson(payload: Record<string, unknown>, label: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn(`WebSocket not connected, cannot send ${label}.`);
      return;
    }
    const serialized = JSON.stringify(payload);
    if (!this._clientId.value) {
      this._pendingJsonMessages.push(serialized);
      console.warn(`${label} queued until registration_ack is received.`);
      return;
    }
    this.ws.send(serialized);
  }

  private flushPendingJsonMessages(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN || !this._clientId.value) {
      return;
    }
    if (!this._pendingJsonMessages.length) {
      return;
    }
    const pending = [...this._pendingJsonMessages];
    this._pendingJsonMessages = [];
    for (const message of pending) {
      this.ws.send(message);
    }
  }

  private registerClient(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const registrationMessage: RegisterEvent = {
        type: "register",
        timestamp: new Date().toISOString(),
        client_type: this.config.clientType,
        capabilities: this.config.capabilities,
        username: this.config.username?.trim() || undefined,
        participant_id: this.config.participantId?.trim() || undefined,
      };
      this.ws.send(JSON.stringify(registrationMessage));
    } else {
      console.error('WebSocket not open, cannot register client.');
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: string | ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      if (typeof data === 'string') {
        // Assume text data if string, wrap in TextMessageEvent
        const textMessage = {
          type: "text_message",
          timestamp: new Date().toISOString(),
          text: data,
        };
        this.sendOrQueueJson(textMessage, "text message");
      } else if (data instanceof ArrayBuffer) {
        // Raw audio bytes are sent directly without JSON wrapper in this new design
        // because the backend expects raw bytes for audio_chunk events
        if (!this._clientId.value) {
          console.warn("Ignoring audio chunk before registration_ack.");
          return;
        }
        this.ws.send(data);
      } else {
        console.warn('Attempted to send unsupported data type:', typeof data);
      }
    } else {
      console.warn('WebSocket not connected, cannot send data.');
    }
  }

  sendText(text: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const textMessage = {
        type: "text_message",
        timestamp: new Date().toISOString(),
        text: text,
      };
      this.sendOrQueueJson(textMessage, "text message");
    } else {
      console.warn('WebSocket not connected, cannot send text message.');
    }
  }

  sendImage(base64Data: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const imageMessage = {
        type: "image_chunk",
        timestamp: new Date().toISOString(),
        data: base64Data,
      };
      this.sendOrQueueJson(imageMessage, "image data");
    } else {
      console.warn('WebSocket not connected, cannot send image data.');
    }
  }

  sendSensorEvent(sensorId: string, eventType: string, value: any, intensity?: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const sensorEvent = {
        type: "sensor_event",
        timestamp: new Date().toISOString(),
        sensor_id: sensorId,
        event: eventType,
        value: value,
        intensity: intensity,
      };
      this.sendOrQueueJson(sensorEvent, "sensor event");
    } else {
      console.warn('WebSocket not connected, cannot send sensor event.');
    }
  }

  sendGestureEvent(gestureName: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const gestureEvent = {
        type: "sensor_event",
        timestamp: new Date().toISOString(),
        sensor_id: "gesture",
        event: gestureName,
      };
      this.sendOrQueueJson(gestureEvent, "gesture event");
    } else {
      console.warn('WebSocket not connected, cannot send gesture event.');
    }
  }

  sendRoutingConfig(config: {
    hardwareMicEnabled: boolean;
    hardwareSpeakerEnabled: boolean;
    uiTextModeEnabled: boolean;
  }): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const routingConfigEvent = {
        type: "routing_config_update",
        timestamp: new Date().toISOString(),
        hardware_mic_enabled: config.hardwareMicEnabled,
        hardware_speaker_enabled: config.hardwareSpeakerEnabled,
        ui_text_mode_enabled: config.uiTextModeEnabled,
      };
      this.sendOrQueueJson(routingConfigEvent, "routing config");
    } else {
      console.warn('WebSocket not connected, cannot send routing config.');
    }
  }

  requestSetActiveController(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this._clientId.value) {
      const setActiveEvent = {
        type: "set_active_controller",
        timestamp: new Date().toISOString(),
        client_id: this._clientId.value,
      };
      this.sendOrQueueJson(setActiveEvent, "set active controller");
    } else {
      console.warn('WebSocket not connected or client ID not set, cannot request active controller.');
    }
  }
}