import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { pb } from '../lib/pocketbase';

// Global state (so it persists across components)
const currentUser = ref(pb.authStore.model);

// Update currentUser whenever the store changes (e.g. login/logout)
pb.authStore.onChange(() => {
    currentUser.value = pb.authStore.model;
});

export function useAuth() {
    const router = useRouter();
    const loading = ref(false);
    const error = ref('');

    async function login(email: string, pass: string) {
        loading.value = true;
        error.value = '';
        try {
            await pb.collection('users').authWithPassword(email, pass);
            router.push('/dashboard');
        } catch (e: any) {
            error.value = "Invalid email or password.";
        } finally {
            loading.value = false;
        }
    }

    async function register(email: string, pass: string, passConfirm: string) {
        loading.value = true;
        error.value = '';
        try {
            // 1. Create the user
            await pb.collection('users').create({
                email,
                password: pass,
                passwordConfirm: passConfirm,
            });
            // 2. Automatically login after register
            await login(email, pass);
        } catch (e: any) {
            // Pocketbase returns detailed errors, we simplify for now
            error.value = "Registration failed. Email might be taken or password too short (<8 chars). " + e.message;
        } finally {
            loading.value = false;
        }
    }

    function logout() {
        pb.authStore.clear(); // Removes the token
        router.push('/login');
    }

    async function resetPassword(email: string) {
        loading.value = true;
        error.value = '';
        try {
            await pb.collection('users').requestPasswordReset(email);
            alert("Check your emails for the reset link!");
        } catch (e) {
            error.value = "Failed to request reset.";
        } finally {
            loading.value = false;
        }
    }

    return {
        currentUser,
        loading,
        error,
        login,
        register,
        logout,
        resetPassword
    };
}