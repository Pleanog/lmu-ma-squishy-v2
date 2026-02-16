import { ref, watch, nextTick } from 'vue';
import { pb } from '../lib/pocketbase';
import type { Message, Conversation } from '../types/chat';

export function useChat(conversationId: any) {
    const messages = ref<Message[]>([]);
    const currentChatTitle = ref<string>("");
    const loadingMessages = ref(false);
    
    // Internal variable to track realtime unsubscribe function
    let unsubscribeFn: (() => void) | null = null;

    // Load History & Meta
    async function initChat(id: string) {
        loadingMessages.value = true;
        messages.value = []; // Clear old messages immediately
        
        try {
            // 1. Get Chat Title/Details
            const chat = await pb.collection('conversations').getOne<Conversation>(id);
            currentChatTitle.value = chat.title;

            // 2. Get Messages
            const res = await pb.collection('messages').getList<Message>(1, 100, {
                filter: `conversation = "${id}"`,
                sort: 'created',
            });
            messages.value = res.items;
        } catch (e) {
            console.error("Error loading chat:", e);
        } finally {
            loadingMessages.value = false;
        }
    }

    // Realtime Subscription
    async function subscribe(id: string) {
        // Unsubscribe from previous chat if exists
        if (unsubscribeFn) {
            unsubscribeFn();
            unsubscribeFn = null;
        }

        unsubscribeFn = await pb.collection('messages').subscribe('*', (e) => {
            if (e.action === 'create' && e.record.conversation === id) {
                messages.value.push(e.record as unknown as Message);
            }
        });
    }

    // Send Message
    async function sendMessage(text: string, metadata: any = {}) {
        const id = typeof conversationId === 'string' ? conversationId : conversationId.value;
        if (!id || !text.trim()) return;

        try {
            await pb.collection('messages').create({
                conversation: id,
                content: text,
                sender: 'user',
                metadata: metadata
            });
            // No need to push manually, subscription handles it
        } catch (e) {
            console.error("Send failed:", e);
        }
    }

    // Watch for ID changes to switch chats automatically
    watch(
        () => (typeof conversationId === 'function' ? conversationId() : conversationId.value),
        async (newId) => {
            if (newId) {
                await initChat(newId);
                await subscribe(newId);
            }
        },
        { immediate: true }
    );

    return {
        messages,
        currentChatTitle,
        loadingMessages,
        sendMessage
    };
}