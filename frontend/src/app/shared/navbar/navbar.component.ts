import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [],
  template: `
    <nav class="flex items-center justify-between bg-slate-900 px-4 py-3 text-white sm:px-6">
      <span class="text-lg font-semibold">PaddockBook</span>
      @if (authService.currentUser(); as user) {
        <div class="flex items-center gap-3 text-sm">
          <span class="text-slate-300">{{ user.email }}</span>
          <button
            type="button"
            data-testid="logout-button"
            (click)="logout()"
            class="rounded-lg bg-slate-700 px-3 py-1.5 font-medium hover:bg-slate-600"
          >Log out</button>
        </div>
      }
    </nav>
  `
})
export class NavbarComponent {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  logout(): void {
    this.authService.logout().subscribe(() => this.router.navigateByUrl('/login'));
  }
}
