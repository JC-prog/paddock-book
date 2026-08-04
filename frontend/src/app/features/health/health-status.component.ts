import { Component, OnInit } from '@angular/core';

import { HealthService } from './health.service';

type HealthState = 'checking' | 'healthy' | 'unreachable';

@Component({
  selector: 'app-health-status',
  standalone: true,
  imports: [],
  template: `
    @switch (state) {
      @case ('checking') {
        <p>Checking backend status…</p>
      }
      @case ('healthy') {
        <p>Backend healthy</p>
      }
      @case ('unreachable') {
        <p>Backend unreachable</p>
      }
    }
  `
})
export class HealthStatusComponent implements OnInit {
  state: HealthState = 'checking';

  constructor(private readonly healthService: HealthService) {}

  ngOnInit(): void {
    this.state = 'checking';
    this.healthService.getHealth().subscribe({
      next: () => (this.state = 'healthy'),
      error: () => (this.state = 'unreachable')
    });
  }
}
