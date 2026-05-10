// src/types.ts

export type Sender = "user" | "llm" | "system" | "admin";
export type MessageStatus = "pending" | "sent" | "delivered" | "failed" | "processing";

export interface MessageMetadata {
    brightness?: "dark" | "normal" | "bright";
    shaken?: boolean;
    eyes_covered?: boolean;
    face_down?: boolean;
    squished?: boolean;
    touched?: boolean;
    // Allows for additional properties without TS errors
    [key: string]: unknown;
}

export interface Message {
    id: string;
    conversation: string; // PocketBase relation ID
    content: string;
    sender: Sender;
    // Metadata is now typed as an object
    metadata: MessageMetadata | null; // Nullable if not present
    audio?: string; // PocketBase file name
    image?: string; // PocketBase file name (planned)
    status: MessageStatus;
    processing_time?: number; // Debug only
    created: string; // ISO timestamp from PocketBase
    updated: string; // ISO timestamp from PocketBase

    // Additional PocketBase specific fields
    collectionId: string;
    collectionName: string;
    expand?: any; // For expanded relations
}

// Payload for sending messages
export interface MessagePayload {
    content?: string;
    audioFile?: File; // Optional audio file to send
    imageFile?: File; // Optional image file to send
    metadata?: MessageMetadata; // Optional metadata
}

// For conversations (if you have a conversation type)
export interface Conversation {
    id: string;
    title: string;
    user: string; // PocketBase relation ID
    is_active: boolean;
    created: string;
    updated: string;
}

