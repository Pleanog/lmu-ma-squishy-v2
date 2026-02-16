<script setup lang="ts">
import { ref } from "vue";
import { useAuth } from "../composables/useAuth";
import { RouterLink } from "vue-router";
import Card from "primevue/card"; // Import Card specifically for layout
import Password from "primevue/password"; // Import Password component

const { login, resetPassword, loading, error } = useAuth();

const email = ref("");
const password = ref("");
</script>

<template>
  <div class="center-screen">
    <Card style="overflow: hidden">
      <template #title>Login</template>
      <template #content>
        <div class="flex-col">
          <label>Email</label>
          <InputText
            v-model="email"
            type="email"
            placeholder="user@example.com"
          />

          <label>Password</label>
          <Password v-model="password" :feedback="false" toggleMask />

          <small v-if="error" class="error-text">{{ error }}</small>

          <div class="actions">
            <Button
              label="Login"
              @click="login(email, password)"
              :loading="loading"
            />
            <Button
              label="Forgot Password?"
              class="p-button-text"
              @click="resetPassword(email)"
            />
          </div>

          <div class="footer-link">
            No account? <RouterLink to="/register">Register here</RouterLink>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.center-screen {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}
.flex-col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.error-text {
  color: red;
}
.actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
}
.footer-link {
  margin-top: 1rem;
  text-align: center;
}
</style>
