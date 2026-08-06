import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';

import { authGuard } from './auth.guard';
import { AuthService } from './auth.service';

describe('authGuard', () => {
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
      authGuard({} as never, { url: '/chat' } as never)
    );
  }

  it('allows navigation when authenticated', () => {
    authServiceStub.currentUser = (() => ({
      id: 'u1',
      email: 'a@b.com',
      department: 'sporting'
    })) as AuthService['currentUser'];

    const result = runGuard();

    expect(result).toBe(true);
  });

  it('redirects to /login when not authenticated', () => {
    const result = runGuard();

    expect(result).not.toBe(true);
    expect(router.serializeUrl(result as UrlTree)).toBe('/login');
  });
});
