// utils/gemini-client.ts

interface GeminiClientConfig {
  wsUrl: string; // This will be passed from the Vue component
  onOpen?: () => void;
  onMessage?: (event: MessageEvent) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
}

export class GeminiClient {
  private websocket: WebSocket | null = null;
  private config: GeminiClientConfig;

  constructor(config: GeminiClientConfig) {
    this.config = config;
  }

  connect(): void {
    if (this.websocket && (this.websocket.readyState === WebSocket.OPEN || this.websocket.readyState === WebSocket.CONNECTING)) {
      console.warn("WebSocket is already connected or connecting.");
      return;
    }

    // Use the wsUrl from the config, which comes from the Vue component's reactive state
    this.websocket = new WebSocket(this.config.wsUrl);
    this.websocket.binaryType = "arraybuffer"; // Important for audio data

    this.websocket.onopen = () => {
      if (this.config.onOpen) this.config.onOpen();
    };

    this.websocket.onmessage = (event: MessageEvent) => {
      if (this.config.onMessage) this.config.onMessage(event);
    };

    this.websocket.onclose = (event: CloseEvent) => {
      if (this.config.onClose) this.config.onClose(event);
    };

    this.websocket.onerror = (event: Event) => {
      if (this.config.onError) this.config.onError(event);
    };
  }

  send(data: string | ArrayBuffer | Blob): void { // Changed type here
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(data);
    } else {
      console.warn("WebSocket is not connected. Cannot send data.");
    }
  }

  sendText(text: string): void {
    this.send(JSON.stringify({ text: text })); // Original example used 'text' as the key
  }

  sendImage(base64Data: string, mimeType: string = "image/jpeg"): void {
    this.send(
      JSON.stringify({
        type: "image",
        mime_type: mimeType,
        data: base64Data,
      })
    );
  }

  disconnect(): void {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
  }

  isConnected(): boolean {
    return this.websocket !== null && this.websocket.readyState === WebSocket.OPEN;
  }
}