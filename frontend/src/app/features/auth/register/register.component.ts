import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="mx-auto mt-16 max-w-sm px-4">
      <h1 class="mb-6 text-xl font-semibold">Register</h1>
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
        <select
          [(ngModel)]="department"
          name="department"
          data-testid="department-select"
          class="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="sporting">Sporting</option>
          <option value="technical">Technical</option>
          <option value="financial">Financial</option>
        </select>
        @if (error()) {
          <p class="mb-3 text-sm text-red-600" data-testid="register-error">{{ error() }}</p>
        }
        <button
          type="submit"
          data-testid="register-submit"
          class="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >Register</button>
      </form>
      <p class="mt-4 text-sm text-slate-600">
        Already have an account? <a routerLink="/login" class="text-blue-600 hover:underline">Log in</a>
      </p>
    </div>
  `
})
export class RegisterComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  email = '';
  password = '';
  department = 'sporting';

  private readonly _error = signal<string | null>(null);
  readonly error = this._error.asReadonly();

  submit(): void {
    this._error.set(null);
    this.authService.register(this.email, this.password, this.department).subscribe({
      next: () => this.router.navigateByUrl('/'),
      error: () => this._error.set('Could not create an account with that email')
    });
  }
}
