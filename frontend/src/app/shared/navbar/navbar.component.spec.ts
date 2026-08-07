import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { NavbarComponent } from './navbar.component';

describe('NavbarComponent', () => {
  function setup(loggedIn = false) {
    const currentUserSignal = signal(
      loggedIn ? { id: 'u1', email: 'driver@team.example', department: 'sporting' } : null
    );
    const authServiceStub = {
      currentUser: currentUserSignal,
      logout: vi.fn().mockReturnValue(of(undefined))
    } satisfies Partial<AuthService>;

    TestBed.configureTestingModule({
      imports: [NavbarComponent],
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }]
    });

    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    const fixture = TestBed.createComponent(NavbarComponent);
    fixture.detectChanges();
    return { fixture, authServiceStub, navigateSpy };
  }

  it('renders the application branding', () => {
    const { fixture } = setup();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('PaddockBook');
  });

  it('does not show a logout action when logged out', () => {
    const { fixture } = setup(false);

    const button = fixture.nativeElement.querySelector('[data-testid="logout-button"]');
    expect(button).toBeNull();
  });

  it('shows a logout action when logged in', () => {
    const { fixture } = setup(true);

    const button = fixture.nativeElement.querySelector('[data-testid="logout-button"]');
    expect(button).toBeTruthy();
  });

  it('calls auth service logout and navigates to /login when clicked', () => {
    const { fixture, authServiceStub, navigateSpy } = setup(true);

    const button: HTMLButtonElement = fixture.nativeElement.querySelector(
      '[data-testid="logout-button"]'
    );
    button.click();

    expect(authServiceStub.logout).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith('/login');
  });
});
