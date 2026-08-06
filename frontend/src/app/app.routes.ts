import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/chat/chat-page.component').then((m) => m.ChatPageComponent)
  },
  {
    path: 'health',
    loadComponent: () =>
      import('./features/health/health-status.component').then((m) => m.HealthStatusComponent)
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent)
  }
];
