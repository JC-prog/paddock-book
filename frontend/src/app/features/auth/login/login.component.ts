import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="mx-auto mt-16 max-w-sm px-4">
      <h1 class="mb-6 text-xl font-semibold">Log in</h1>
      <form (ngSubmit)="submit()">
        <input
          [(ngModel)]="email"
          name="email"
          type="email"
          placeholder="Email"
          data-testid="email-input"
          class="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <input
          [(ngModel)]="password"
          name="password"
          type="password"
          placeholder="Password"
          data-testid="password-input"
          class="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        @if (error()) {
          <p class="mb-3 text-sm text-red-600" data-testid="login-error">{{ error() }}</p>
        }
        <button
          type="submit"
          data-testid="login-submit"
          class="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >Log in</button>
      </form>
      <p class="mt-4 text-sm text-slate-600">
        Need an account? <a routerLink="/register" class="text-blue-600 hover:underline">Register</a>
      </p>
    </div>
  `
})
export class LoginComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  email = '';
  password = '';

  private readonly _error = signal<string | null>(null);
  readonly error = this._error.asReadonly();

  submit(): void {
    this._error.set(null);
    this.authService.login(this.email, this.password).subscribe({
      next: () => this.router.navigateByUrl('/'),
      error: () => this._error.set('Invalid email or password')
    });
  }
}
