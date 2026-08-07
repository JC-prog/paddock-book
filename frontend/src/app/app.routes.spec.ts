import { routes } from './app.routes';
import { authGuard } from './core/auth/auth.guard';

describe('app.routes', () => {
  it('resolves the "health" path to HealthStatusComponent', async () => {
    const healthRoute = routes.find((r) => r.path === 'health');
    expect(healthRoute).toBeTruthy();
    expect(healthRoute!.loadComponent).toBeTruthy();

    const loaded = await healthRoute!.loadComponent!();
    const { HealthStatusComponent } = await import('./features/health/health-status.component');

    expect(loaded).toBe(HealthStatusComponent);
  });

  it('resolves the "login" path to LoginComponent', async () => {
    const loginRoute = routes.find((r) => r.path === 'login');
    expect(loginRoute).toBeTruthy();
    expect(loginRoute!.loadComponent).toBeTruthy();

    const loaded = await loginRoute!.loadComponent!();
    const { LoginComponent } = await import('./features/auth/login/login.component');

    expect(loaded).toBe(LoginComponent);
  });

  it('resolves the "register" path to RegisterComponent', async () => {
    const registerRoute = routes.find((r) => r.path === 'register');
    expect(registerRoute).toBeTruthy();
    expect(registerRoute!.loadComponent).toBeTruthy();

    const loaded = await registerRoute!.loadComponent!();
    const { RegisterComponent } = await import('./features/auth/register/register.component');

    expect(loaded).toBe(RegisterComponent);
  });

  it('guards the root ("") path with authGuard', () => {
    const rootRoute = routes.find((r) => r.path === '');
    expect(rootRoute).toBeTruthy();
    expect(rootRoute!.canActivate).toContain(authGuard);
  });

  it('does not guard the "login", "register", or "health" paths', () => {
    const loginRoute = routes.find((r) => r.path === 'login');
    const registerRoute = routes.find((r) => r.path === 'register');
    const healthRoute = routes.find((r) => r.path === 'health');

    expect(loginRoute!.canActivate).toBeUndefined();
    expect(registerRoute!.canActivate).toBeUndefined();
    expect(healthRoute!.canActivate).toBeUndefined();
  });
});
