import { ref } from 'vue';
import { pb } from '../lib/pocketbase';
import { useAuth } from './useAuth';
import type { Conversation } from '../types/chat';

export function useConversations() {
    const { currentUser } = useAuth();
    const conversations = ref<Conversation[]>([]);
    const loading = ref(false);

    // Fetch all conversations for the current user
    async function fetchConversations() {
        if (!currentUser.value) return;
        
        loading.value = true;
        try {
            const result = await pb.collection('conversations').getList<Conversation>(1, 50, {
                filter: `user = "${currentUser.value.id}"`,
                sort: '-created',
            });
            conversations.value = result.items;
        } catch (e) {
            console.error("Error fetching conversations:", e);
        } finally {
            loading.value = false;
        }
    }

    // Create a new empty conversation
    async function createConversation(title = "New Chat") {
        if (!currentUser.value) return null;

        try {
            const newChat = await pb.collection('conversations').create<Conversation>({
                user: currentUser.value.id,
                title: title,
                is_active: true
            });
            // Add to start of list locally
            conversations.value = [newChat, ...conversations.value];
            return newChat;
        } catch (e) {
            console.error("Error creating chat:", e);
            return null;
        }
    }

    async function getConversationById(id: string): Promise<Conversation | null> {
        try {
            return await pb.collection('conversations').getOne<Conversation>(id);
        } catch (e) {
            return null;
        }
    }

    return {
        conversations,
        loading,
        fetchConversations,
        createConversation,
        getConversationById
    };
}