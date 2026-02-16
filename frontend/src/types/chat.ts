export interface Conversation {
    id: string;
    created: string;
    updated: string;
    title: string;
    user: string;
    is_active: boolean;
}

export interface Message {
    id: string;
    conversation: string;
    created: string;
    updated: string;
    content: string;
    sender: 'user' | 'llm' | 'system' | 'admin';
    
    audio?: string[]; 
    image?: string[];
    
    metadata?: {
        brightness?: 'low' | 'normal' | 'high';
        shaken?: boolean;
        generated_by?: string;
        [key: string]: any;
    };

    status: 'pending' | 'sent' | 'delivered' | 'failed' | 'processing';
    processing_time?: number;
}