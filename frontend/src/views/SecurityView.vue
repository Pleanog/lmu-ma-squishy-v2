<template>
  <div v-if="currentRoute.name === 'security'">
    <Header
      :breadcrumbs="breadcrumbs"
      :title="dynamicTitle || 'Account & Sicherheit'"
      :visibleCount="3"
    />

    <div class="content-wrapper">
      <div class="content">
        <div class="content-full">
          <FeatureList :items="settingsItems" />

          <br />

          <DetailCard
            :title="`Ihre Berechtigungen als: ${$t('roles.slugs.' + user.role_slug) || user.role_slug}`"
            :data="userPermissionsData"
            :maxRows="5"
            :modalWidth="'50vw'"
          >
            <template #permissions="{ item }">
              <StatusTag
                v-for="(tag, index) in getPermissions(item.value)"
                style="margin-right: 0.5rem"
                :key="index"
                :state="tag"
              />
            </template>
          </DetailCard>

          <br />

          <DetailCard
            :title="'Nutzerstatus & Details'"
            :data="userDetailsData"
            :isLoading="isLoadingSingleUser"
            :hasError="hasErrorSingleUser"
            :errorObject="errorObjectSingleUser"
            :max-rows="8"
            :modalWidth="'50vw'"
          >
            <template #status="{ item }">
              <StatusTag :state="item.value" />
            </template>

            <template #email_status="{ item }">
              <StatusTag :state="item.value" />
            </template>

            <template #pwd_reset="{ item }">
              <StatusTag :state="item.value" />
            </template>

            <template #customers="{ item }">
              <div
                v-if="item.value && item.value.length > 0"
                style="display: flex; flex-direction: column; gap: 0.5rem"
              >
                <VisualIdentity
                  v-for="customer in item.value"
                  :key="customer.id"
                  :title="customer.company_name"
                  :subtitle="
                    customer.firstname
                      ? `${customer.firstname} ${customer.lastname}`
                      : ''
                  "
                  :isSquircle="true"
                />
              </div>
              <span v-else>Keine Kunden zugewiesen</span>
            </template>
          </DetailCard>
        </div>
      </div>
    </div>

    <FormModalShell
      v-model:visible="showUserEditModal"
      title="Profil bearbeiten"
      save-button-label="Speichern"
      :save-api-call="saveUser"
      :validate-and-get-data="getFormValidationAndData"
      @reset="resetFormFromShell"
      @saved="handlePostSaveSuccess"
      modal-width="800px"
    >
      <UserEditCreateForm
        ref="userFormRef"
        :editUser="selectedUser"
        :usersList="users"
      />
    </FormModalShell>
  </div>
  <RouterView v-else />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, shallowRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "primevue/usetoast";
import { useBreadcrumbs } from "../../composables/useBreadcrumbs.js";
import { useUserStore } from "@app/stores/user";
import { useUsers } from "../../composables/useUsers.js";
import { useAppDataStore } from "@app/stores/appData";
import { formatDateTime } from "../../utils/datetimeHelpers.js";
import { getPermissions } from "../../utils/roleConstants.js";
import { useI18n } from "vue-i18n";
import { USER_STATUS_CONFIG } from "../../utils/userConstants.js";

const { t } = useI18n();

const route = useRoute();
const router = useRouter();
const currentRoute = computed(() => route);
const toast = useToast();
const userStore = useUserStore();
const appDataStore = useAppDataStore();

const user = computed(() => userStore.user);

// User Data
const { users, fetchUsers, updateUser } = useUsers();

// --- State ---
const showUserEditModal = ref(false);
const userFormRef = ref(null);
const selectedUser = ref(null);

// --- Modal Actions ---
const openEditUserModal = async () => {
  fetchUsers();
  console.log("Users fetched for edit modal:", users.value);
  selectedUser.value = { ...user.value };
  showUserEditModal.value = true;
};

const logout = () => {
  userStore.logout();
  router.replace({ name: "login" });
};

onMounted(() => {
  appDataStore.load();
});

const mapPermissionsToDetailData = (permissions) => {
  if (!permissions || typeof permissions !== "object") return [];

  return Object.entries(permissions).map(([resource, actions]) => ({
    key: "permissions",
    label: t("roles.groups." + resource),
    value: actions,
  }));
};

const userPermissionsData = computed(() => {
  return mapPermissionsToDetailData(user.value.permissions);
});

const userDetailsData = computed(() => {
  if (!user.value || user.value.id === null) return [];

  const data = user.value;

  // Helper to determine Account Status Tag
  const accountStatus = data.is_locked
    ? USER_STATUS_CONFIG.is_locked
    : USER_STATUS_CONFIG.is_active;

  // Helper to determine Password Reset Tag
  const pwdResetStatus = data.need_password_reset
    ? USER_STATUS_CONFIG.password_needs_reset
    : USER_STATUS_CONFIG.password_needs_no_reset;

  // Helper for Email Verification
  const emailStatus = data.email_verified_at
    ? USER_STATUS_CONFIG.email_is_verified
    : USER_STATUS_CONFIG.email_needs_verification;

  return [
    { label: "Benutzer ID", value: data.id },
    { label: "Name", value: `${data.firstname} ${data.lastname}` },
    { label: "E-Mail", value: data.email },

    // Visual Status Tags
    { label: "Kontostatus", key: "status", value: accountStatus },
    { label: "E-Mail Status", key: "email_status", value: emailStatus },
    { label: "Passwort-Sicherheit", key: "pwd_reset", value: pwdResetStatus },

    // Role Info
    {
      label: "Rolle",
      value: t("roles.slugs." + data.role_slug) || data.role_slug,
    },
    { label: "Rollen-ID", value: data.role_id }, // Added

    // Contact
    { label: "Telefon", value: data.phone || "-" },
    { label: "Mobil", value: data.mobile || "-" },

    // Associated Data
    { label: "Zugewiesene Kunden", key: "customers", value: data.customers },

    // Timestamps
    { label: "Erstellt am", value: formatDateTime(data.created_at) },
    { label: "Zuletzt bearbeitet", value: formatDateTime(data.updated_at) },
  ];
});

const settingsItems = shallowRef([
  {
    title: "Account Details bearbeiten",
    icon: "EditIcon",
    description: "Sehen Sie alle gespeicherten persönlichen Daten ein",
    onClick: openEditUserModal,
  },
  {
    title: "E-Mail verifizieren",
    description:
      "Verifizieren Sie Ihre E-Mail-Adresse für zusätzliche Sicherheit",
    component: "PButton",
    componentProps: {
      label: "E-Mail verifizieren",
      severity: "secondary",
      outlined: true,
      text: false,
    },
    onClick: () => router.push({ name: "change_password" }),
  },
  {
    title: "Abmelden",
    description: "Melden Sie sich von Ihrem Konto ab",
    icon: "LogOutIcon",
    component: "PButton",
    componentProps: {
      label: "Abmelden",
      severity: "danger",
      outlined: false,
      text: false,
    },
    onClick: logout,
  },
]);

// --- Form Handler for FormModalShell ---

const getFormValidationAndData = async () => {
  if (!userFormRef.value) {
    return { valid: false, errors: { general: "Formular nicht geladen." } };
  }
  return userFormRef.value.validateAndGetData();
};

const saveUser = async (formData) => {
  await updateUser(formData);
};

const handlePostSaveSuccess = () => {
  toast.add({
    severity: "success",
    summary: "Erfolg",
    detail: "Profil aktualisiert",
    life: 3000,
  });
  userStore.freshUser();
};

const resetFormFromShell = () => {
  if (userFormRef.value && userFormRef.value.reset) {
    userFormRef.value.reset();
  }
  selectedUser.value = null;
};

const dynamicTitle = computed(() => {
  return "Account & Sicherheit";
});

const { breadcrumbs } = useBreadcrumbs();
</script>

<style lang="scss" scoped></style>
