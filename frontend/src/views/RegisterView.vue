<script setup lang="ts">
import { ref } from "vue";
import { useAuth } from "../composables/useAuth";
import { RouterLink } from "vue-router";
import Card from "primevue/card";
import Password from "primevue/password";

const { register, loading, error } = useAuth();
const email = ref("");
const password = ref("");
const passwordConfirm = ref("");
</script>

<template>
  <div class="center-screen">
    <Card>
      <template #title>Create Account</template>
      <template #content>
        <div class="flex-col">
          <label>Email</label>
          <InputText v-model="email" />

          <label>Password (min 8 chars)</label>
          <Password v-model="password" toggleMask />

          <label>Confirm Password</label>
          <Password v-model="passwordConfirm" :feedback="false" toggleMask />

          <small v-if="error" class="error-text">{{ error }}</small>

          <Button
            label="Register"
            @click="register(email, password, passwordConfirm)"
            :loading="loading"
          />

          <div class="footer-link">
            Already have an account?
            <RouterLink to="/login">Login here</RouterLink>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
/* Same styles as LoginView */
.center-screen {
  display: flex;
  justify-content: center;
  align-items: center;
}
.flex-col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.error-text {
  color: red;
}
.footer-link {
  margin-top: 1rem;
  text-align: center;
}
</style>
