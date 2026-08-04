import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'health',
    loadComponent: () =>
      import('./features/health/health-status.component').then((m) => m.HealthStatusComponent)
  }
];
