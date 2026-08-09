import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';

import { adminGuard } from './admin.guard';
import { AuthService } from './auth.service';

describe('adminGuard', () => {
  let authServiceStub: Partial<AuthService>;
  let router: Router;

  beforeEach(() => {
    authServiceStub = { currentUser: (() => null) as AuthService['currentUser'] };

    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }]
    });
    router = TestBed.inject(Router);
  });

  function runGuard() {
    return TestBed.runInInjectionContext(() =>
      adminGuard({} as never, { url: '/admin' } as never)
    );
  }

  it('allows navigation when the current user is an admin', () => {
    authServiceStub.currentUser = (() => ({
      id: 'u1',
      email: 'admin@team.example',
      department: 'sporting',
      is_admin: true
    })) as AuthService['currentUser'];

    const result = runGuard();

    expect(result).toBe(true);
  });

  it('redirects to / when the current user is not an admin', () => {
    authServiceStub.currentUser = (() => ({
      id: 'u1',
      email: 'driver@team.example',
      department: 'sporting',
      is_admin: false
    })) as AuthService['currentUser'];

    const result = runGuard();

    expect(result).not.toBe(true);
    expect(router.serializeUrl(result as UrlTree)).toBe('/');
  });

  it('redirects to / when there is no current user', () => {
    const result = runGuard();

    expect(result).not.toBe(true);
    expect(router.serializeUrl(result as UrlTree)).toBe('/');
  });
});
