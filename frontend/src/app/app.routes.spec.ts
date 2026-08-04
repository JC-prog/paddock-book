import { routes } from './app.routes';

describe('app.routes', () => {
  it('resolves the "health" path to HealthStatusComponent', async () => {
    const healthRoute = routes.find((r) => r.path === 'health');
    expect(healthRoute).toBeTruthy();
    expect(healthRoute!.loadComponent).toBeTruthy();

    const loaded = await healthRoute!.loadComponent!();
    const { HealthStatusComponent } = await import('./features/health/health-status.component');

    expect(loaded).toBe(HealthStatusComponent);
  });
});
