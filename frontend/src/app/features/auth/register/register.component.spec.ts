import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { RegisterComponent } from './register.component';

describe('RegisterComponent', () => {
  function setup() {
    const authServiceStub = {
      register: vi.fn().mockReturnValue(of({ id: 'u1', email: 'a@b.com', department: 'sporting' }))
    } satisfies Partial<AuthService>;

    TestBed.configureTestingModule({
      imports: [RegisterComponent],
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }]
    });

    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    const fixture = TestBed.createComponent(RegisterComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, authServiceStub, navigateSpy };
  }

  it('navigates into the app, already logged in, on successful registration', () => {
    const { component, navigateSpy } = setup();
    component.email = 'a@b.com';
    component.password = 'secret';
    component.department = 'sporting';

    component.submit();

    expect(navigateSpy).toHaveBeenCalledWith('/');
  });

  it('shows a clear error and does not navigate when registration fails (e.g. duplicate email)', () => {
    const { component, authServiceStub, navigateSpy } = setup();
    authServiceStub.register.mockReturnValue(throwError(() => new Error('duplicate')));
    component.email = 'a@b.com';
    component.password = 'secret';

    component.submit();

    expect(component.error()).toBeTruthy();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('calls authService.register with the entered email, password, and department', () => {
    const { component, authServiceStub } = setup();
    component.email = 'a@b.com';
    component.password = 'secret';
    component.department = 'technical';

    component.submit();

    expect(authServiceStub.register).toHaveBeenCalledWith('a@b.com', 'secret', 'technical');
  });

  it('renders the error message in the template on failure', () => {
    const { fixture, component, authServiceStub } = setup();
    authServiceStub.register.mockReturnValue(throwError(() => new Error('duplicate')));
    component.email = 'a@b.com';
    component.password = 'secret';

    component.submit();
    fixture.detectChanges();

    const errorEl: HTMLElement = fixture.nativeElement.querySelector('[data-testid="register-error"]');
    expect(errorEl).toBeTruthy();
  });
});
