import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/chat/chat-page.component').then((m) => m.ChatPageComponent)
  },
  {
    path: 'health',
    loadComponent: () =>
      import('./features/health/health-status.component').then((m) => m.HealthStatusComponent)
  }
];
