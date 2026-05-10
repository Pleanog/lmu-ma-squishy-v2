// src/composables/useChat.ts
import { ref, watch, onMounted, onUnmounted, type Ref } from "vue";
import { pb } from "../lib/pocketbase";
import type { Message, MessagePayload, Conversation } from "../types";

export function useChat(chatId: Ref<string>) {
    const messages = ref<Message[]>([]);
    const currentChatTitle = ref<string>("");
    const loadingMessages = ref<boolean>(false);
    const unsubscribePb = ref<(() => void) | null>(null);


    // Helper to construct audio/image URL
    const getFileUrl = (
        msg: Message,
        fieldName: "audio" | "image",
    ): string | undefined => {
        // Check if the field exists AND if it's a string (PocketBase file name)
        // For single file fields, PocketBase stores the filename directly as a string.
        // For multi-file fields, it's an array of strings.
        // If it's a single file and empty, it will often be `""` (empty string)
        // If it's a multi file and empty, it will be `[]`
        // Let's ensure we only get a URL if there's an actual filename string.

        // A safer check for a single file field (which PocketBase typically does for `audio` and `image` if set to single):
        if (typeof msg[fieldName] === 'string' && msg[fieldName]) {
            return `${pb.baseUrl}/api/files/${msg.collectionId}/${msg.id}/${msg[fieldName]}`;
        }
        // If PocketBase stored it as an array (even for single file field definition),
        // we should check if the array has elements and use the first one.
        // This handles cases where it might be `['filename.mp3']`
        if (Array.isArray(msg[fieldName]) && msg[fieldName].length > 0) {
            // Assuming you only expect one file for `audio` and `image`
            const filename = msg[fieldName][0];
            if (typeof filename === 'string' && filename) {
                return `${pb.baseUrl}/api/files/${msg.collectionId}/${msg.id}/${filename}`;
            }
        }

        return undefined; // Return undefined if no valid filename is found
    };

    const fetchMessages = async (id: string) => {
        if (!id) {
            messages.value = [];
            currentChatTitle.value = "";
            return;
        }

        loadingMessages.value = true;
        try {
            const chatMessages = await pb.collection("messages").getFullList<Message>(
                {
                    filter: `conversation = "${id}"`,
                    sort: "created",
                },
            );
            messages.value = chatMessages.map((msg) => ({
                ...msg,
                // Parse metadata if it's a string, otherwise use as is
                metadata:
                    typeof msg.metadata === "string" && msg.metadata
                        ? JSON.parse(msg.metadata)
                        : msg.metadata || null,
            }));

            const conversation = await pb
                .collection("conversations")
                .getOne<Conversation>(id);
            currentChatTitle.value = conversation.title;
        } catch (error) {
            console.error("Failed to fetch messages or conversation:", error);
            messages.value = [];
            currentChatTitle.value = "Error loading chat";
        } finally {
            loadingMessages.value = false;
        }
    };

    const setupRealtime = (id: string) => {
        if (unsubscribePb.value) {
            unsubscribePb.value(); // Unsubscribe from previous chat
            unsubscribePb.value = null;
        }

        if (id) {
            pb.collection("messages").subscribe<Message>(
                "*",
                (e) => {
                    if (e.record.conversation !== id) return; // Only messages for current chat

                    const updatedRecord = {
                        ...e.record,
                        metadata:
                            typeof e.record.metadata === "string" && e.record.metadata
                                ? JSON.parse(e.record.metadata)
                                : e.record.metadata || null,
                    };

                    if (e.action === "create") {
                        messages.value.push(updatedRecord);
                    } else if (e.action === "update") {
                        const index = messages.value.findIndex((m) => m.id === e.record.id);
                        if (index !== -1) {
                            messages.value[index] = updatedRecord;
                        }
                    } else if (e.action === "delete") {
                        messages.value = messages.value.filter((m) => m.id !== e.record.id);
                    }
                },
                {
                    filter: `conversation = "${id}"`, // Filter subscriptions by current chat
                },
            );
        }
    };

    const sendMessage = async (payload: MessagePayload) => {
        if (!chatId.value) {
            console.warn("No active chat to send message to.");
            return;
        }

        if (!payload.content && !payload.audioFile && !payload.imageFile) {
            console.warn("Cannot send empty message.");
            return;
        }

        const formData = new FormData();
        formData.append("conversation", chatId.value);
        formData.append("sender", "user"); // Always 'user' for client-sent messages
        formData.append("status", "pending");

        if (payload.content) {
            formData.append("content", payload.content);
        }
        if (payload.audioFile) {
            formData.append("audio", payload.audioFile);
        }
        if (payload.imageFile) {
            formData.append("image", payload.imageFile);
        }
        if (payload.metadata && Object.keys(payload.metadata).length > 0) {
            formData.append("metadata", JSON.stringify(payload.metadata));
        }

        try {
            // Create message; realtime subscription will add it to the UI
            await pb.collection("messages").create(formData);
        } catch (e) {
            console.error("Failed to send message:", e);
            // TODO: Implement user feedback for failed messages (e.g., mark as failed)
        }
    };

    // Watch for chatId changes to refetch messages and set up new real-time subscription
    watch(
        chatId,
        async (newId, oldId) => {
            if (newId !== oldId) {
                await fetchMessages(newId);
                setupRealtime(newId);
            }
        },
        { immediate: true },
    );

    onUnmounted(() => {
        if (unsubscribePb.value) {
            unsubscribePb.value();
        }
    });

    return {
        messages,
        currentChatTitle,
        sendMessage,
        loadingMessages,
        getFileUrl,
         // Export the helper
    };
}