import { Component } from '@angular/core';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [],
  template: `
    <nav class="flex items-center bg-slate-900 px-4 py-3 text-white sm:px-6">
      <span class="text-lg font-semibold">PaddockBook</span>
    </nav>
  `
})
export class NavbarComponent {}
