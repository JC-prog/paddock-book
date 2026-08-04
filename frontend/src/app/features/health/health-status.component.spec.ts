import { TestBed } from '@angular/core/testing';
import { Subject, of, throwError } from 'rxjs';

import { HealthStatusComponent } from './health-status.component';
import { HealthService } from './health.service';

describe('HealthStatusComponent', () => {
  function setup(healthServiceStub: Partial<HealthService>) {
    TestBed.configureTestingModule({
      imports: [HealthStatusComponent],
      providers: [{ provide: HealthService, useValue: healthServiceStub }]
    });

    const fixture = TestBed.createComponent(HealthStatusComponent);
    return fixture;
  }

  it('shows a checking state before the backend responds', () => {
    const pending = new Subject<{ status: string }>();
    const fixture = setup({ getHealth: () => pending.asObservable() });

    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).toContain('checking');
  });

  it('shows a healthy state when the backend responds ok', () => {
    const fixture = setup({ getHealth: () => of({ status: 'ok' }) });

    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).toContain('healthy');
  });

  it('shows an unreachable state when the backend request fails', () => {
    const fixture = setup({ getHealth: () => throwError(() => new Error('network error')) });

    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).toContain('unreachable');
  });
});
