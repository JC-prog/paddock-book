import { routes } from './app.routes';
import { adminGuard } from './core/auth/admin.guard';
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

  it('resolves the "admin" path to AdminComponent', async () => {
    const adminRoute = routes.find((r) => r.path === 'admin');
    expect(adminRoute).toBeTruthy();
    expect(adminRoute!.loadComponent).toBeTruthy();

    const loaded = await adminRoute!.loadComponent!();
    const { AdminComponent } = await import('./features/admin/admin.component');

    expect(loaded).toBe(AdminComponent);
  });

  it('resolves the "admin/jobs" path to JobsComponent', async () => {
    const jobsRoute = routes.find((r) => r.path === 'admin/jobs');
    expect(jobsRoute).toBeTruthy();
    expect(jobsRoute!.loadComponent).toBeTruthy();

    const loaded = await jobsRoute!.loadComponent!();
    const { JobsComponent } = await import('./features/admin/jobs/jobs.component');

    expect(loaded).toBe(JobsComponent);
  });

  it('guards the "admin/jobs" path with authGuard and adminGuard', () => {
    const jobsRoute = routes.find((r) => r.path === 'admin/jobs');
    expect(jobsRoute).toBeTruthy();
    expect(jobsRoute!.canActivate).toContain(authGuard);
    expect(jobsRoute!.canActivate).toContain(adminGuard);
  });

  it('resolves the "admin/chat-provider" path to ChatProviderComponent', async () => {
    const chatProviderRoute = routes.find((r) => r.path === 'admin/chat-provider');
    expect(chatProviderRoute).toBeTruthy();
    expect(chatProviderRoute!.loadComponent).toBeTruthy();

    const loaded = await chatProviderRoute!.loadComponent!();
    const { ChatProviderComponent } = await import(
      './features/admin/chat-provider/chat-provider.component'
    );

    expect(loaded).toBe(ChatProviderComponent);
  });

  it('guards the "admin/chat-provider" path with authGuard and adminGuard', () => {
    const chatProviderRoute = routes.find((r) => r.path === 'admin/chat-provider');
    expect(chatProviderRoute).toBeTruthy();
    expect(chatProviderRoute!.canActivate).toContain(authGuard);
    expect(chatProviderRoute!.canActivate).toContain(adminGuard);
  });

  it('guards the root ("") path with authGuard', () => {
    const rootRoute = routes.find((r) => r.path === '');
    expect(rootRoute).toBeTruthy();
    expect(rootRoute!.canActivate).toContain(authGuard);
  });

  it('guards the "admin" path with authGuard and adminGuard', () => {
    const adminRoute = routes.find((r) => r.path === 'admin');
    expect(adminRoute).toBeTruthy();
    expect(adminRoute!.canActivate).toContain(authGuard);
    expect(adminRoute!.canActivate).toContain(adminGuard);
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
