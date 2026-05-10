import { createRouter, createWebHistory } from 'vue-router';
import { pb } from './lib/pocketbase';

import LoginView from './views/LoginView.vue';
import RegisterView from './views/RegisterView.vue';
import DashboardView from './views/DashboardView.vue';
import SettingsView from './views/SettingsView.vue';
import WebSocketTestView from './views/WebSocketTestView.vue';
import GeminiLiveDemo from './views/GeminiLiveDemo.vue';


const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginView },
    { path: '/register', component: RegisterView },
    { path: '/dashboard', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { requiresAuth: true } },
    { path: '/ws-test', name: 'ws-test', component: WebSocketTestView, meta: { requiresAuth: true } },
    { path: '/gemini', name: 'gemini', component: GeminiLiveDemo, meta: { requiresAuth: true } },
  ],
});

router.beforeEach((to, _from, next) => {

  const isAuthenticated = pb.authStore.isValid;

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login');
  } else if ((to.path === '/login' || to.path === '/register') && isAuthenticated) {
    next('/dashboard');
  } else {
    next();
  }
});

export default router;