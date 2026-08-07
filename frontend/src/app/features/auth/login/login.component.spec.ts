import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  function setup() {
    const authServiceStub = {
      login: vi.fn().mockReturnValue(of({ id: 'u1', email: 'a@b.com', department: 'sporting' }))
    } satisfies Partial<AuthService>;

    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }]
    });

    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, authServiceStub, navigateSpy };
  }

  it('navigates into the app on successful login', () => {
    const { component, navigateSpy } = setup();
    component.email = 'a@b.com';
    component.password = 'secret';

    component.submit();

    expect(navigateSpy).toHaveBeenCalledWith('/');
  });

  it('shows a generic error and does not navigate on failed login', () => {
    const { component, authServiceStub, navigateSpy } = setup();
    authServiceStub.login.mockReturnValue(throwError(() => new Error('unauthorized')));
    component.email = 'a@b.com';
    component.password = 'wrong';

    component.submit();

    expect(component.error()).toBeTruthy();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('renders the generic error message in the template on failure', () => {
    const { fixture, component, authServiceStub } = setup();
    authServiceStub.login.mockReturnValue(throwError(() => new Error('unauthorized')));
    component.email = 'a@b.com';
    component.password = 'wrong';

    component.submit();
    fixture.detectChanges();

    const errorEl: HTMLElement = fixture.nativeElement.querySelector('[data-testid="login-error"]');
    expect(errorEl).toBeTruthy();
    expect(errorEl.textContent).toContain('Invalid email or password');
  });
});
