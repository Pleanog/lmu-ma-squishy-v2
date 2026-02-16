<template>
  <div v-if="router.currentRoute.value.name === 'settings'">
    <!-- <Header
      :breadcrumbs="headerBreadcrumbs"
      :title="headerTitle"
      :actions="headerActions"
      :visibleCount="3"
    /> -->

    <div class="settings-grid-container">
      <FeatureCard
        v-for="card in settingsCards"
        :key="card.to"
        :icon-name="card.icon"
        :title="card.title"
        :description="card.description"
        @click="navigate(card.to)"
      />
    </div>

    <br />
    <br />
    <FeatureList :items="settingsList" />

    <PButton
      class="logout-button"
      label="Abmelde44n"
      severity="danger"
      @click="navigate('logout')"
    >
      <template #icon>
        <component :is="'LogOutIcon'" size="24" stroke-width="2" />
      </template>
    </PButton>
  </div>

  <router-view v-else></router-view>
</template>

<script setup lang="ts">
import FeatureCard from "../components/FeatureCard.vue";
import FeatureList from "../components/FeatureList.vue";

import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const navigate = (routeName: string) => {
  console.log(`Navigating to ${routeName}`);
  router.push({ name: routeName });
};

const logout = () => {
  // userStore.logout();
  // router.replace({ name: "login" });
};

const headerTitle = ref("Einstellungen");
const headerBreadcrumbs = ref([
  { label: "Dashboard", to: { name: "dashboard" } },
  { label: "Einstellungen" },
]);
const headerActions = ref([
  // the logout button
  {
    label: "AppDaten neu laden",
    icon: "RefreshCwIcon",
    // command: () => appDataStore.load(),
    command: () => console.log("AppDaten neu laden"),
    severity: "secondary",
  },
  {
    label: "Abmelden",
    icon: "LogOutIcon",
    command: logout,
    severity: "danger",
    outlined: false,
    text: false,
  },
]);

const settingsCards = ref([
  {
    icon: "UserCogIcon",
    title: "Account & Sicherheit",
    description:
      "Passwort, Zwei-Faktor-Authentifizierung und Kontosicherheit verwalten.",
    to: "security",
  },
  {
    icon: "PaletteIcon",
    title: "Erscheinungsbild & Sprache",
    description: "Farbschema und Sprache anpassen.",
    to: "appearance",
  },
  // {
  //     icon: 'ReceiptTextIcon',
  //     title: 'Verträge & Abrechnung',
  //     description: 'Verträge verwalten und Abrechnungen einsehen.',
  //     to: 'contracts',
  // },
  // {
  //     icon: 'CreditCardIcon',
  //     title: 'Zahlungsdetails',
  //     description: 'Rechnungsadressen und Zahlungsmethoden bearbeiten.',
  //     to: 'payments',
  // },
  // {
  //     icon: 'MailIcon',
  //     title: 'Benachrichtigungen',
  //     description: 'E-Mail- und In-App-Benachrichtigungen anpassen.',
  //     to: 'notifications',
  // },
  // {
  //     icon: 'CookieIcon',
  //     title: 'Datenschutz & Cookies',
  //     description: 'Einstellungen für Datenschutz und Cookies verwalten.',
  //     to: 'privacy',
  // },
]);

const settingsList = ref([
  // {
  //     title: 'Hilfe & Kontakt',
  //     description: 'Support kontaktieren und Hilfeartikel durchsuchen.',
  //     to: 'support',
  // },
  // {
  //     title: 'Über Uns',
  //     description: 'Informationen über das Unternehmen und das Team.',
  //     to: 'about_us',
  // },
  {
    title: "Datenschutzerklärung & Nutzungsbedingungen",
    description:
      "Details zu unserer Datenschutzerklärung und Nutzungsbedingungen lesen.",
    to: "page",
    params: { slug: "datenschutz" },
  },
  {
    title: "Impressum",
    description: "",
    to: "page",
    params: { slug: "impressum" },
  },
]);
</script>

<style lang="scss" scoped>
.settings-grid-container {
  display: grid;
  gap: 1rem;

  grid-template-columns: 1fr;

  @media (min-width: 600px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 1200px) {
    grid-template-columns: repeat(4, 1fr);
  }
}

.logout-button {
  width: 100%;
  padding: 1rem 3rem;
  gap: 0.5rem;
  display: none;
  @media (max-width: 768px) {
    align-items: center;
    justify-content: center;
    width: 100%;
    display: flex;
    width: auto;
    margin: 2rem auto 0 auto;
  }
}
</style>
