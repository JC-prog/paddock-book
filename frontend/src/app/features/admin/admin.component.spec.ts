import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AdminComponent } from './admin.component';

describe('AdminComponent', () => {
  let httpMock: HttpTestingController;

  function setup() {
    TestBed.configureTestingModule({
      imports: [AdminComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    httpMock = TestBed.inject(HttpTestingController);

    const fixture = TestBed.createComponent(AdminComponent);
    return fixture;
  }

  afterEach(() => {
    httpMock.verify();
  });

  function text(fixture: ReturnType<typeof setup>): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('loads and displays the current setting on init', () => {
    const fixture = setup();
    fixture.detectChanges();

    const req = httpMock.expectOne('http://localhost:8000/v1/admin/settings/log-destination');
    expect(req.request.method).toBe('GET');
    req.flush({ log_to_file: true });
    fixture.detectChanges();

    const checkbox: HTMLInputElement = fixture.nativeElement.querySelector(
      '[data-testid="log-to-file-toggle"]'
    );
    expect(checkbox.checked).toBe(true);
  });

  it('changing the setting calls PUT and reflects the confirmed new value', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock
      .expectOne('http://localhost:8000/v1/admin/settings/log-destination')
      .flush({ log_to_file: true });
    fixture.detectChanges();

    const checkbox: HTMLInputElement = fixture.nativeElement.querySelector(
      '[data-testid="log-to-file-toggle"]'
    );
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event('change'));

    const putReq = httpMock.expectOne('http://localhost:8000/v1/admin/settings/log-destination');
    expect(putReq.request.method).toBe('PUT');
    expect(putReq.request.body).toEqual({ log_to_file: false });
    putReq.flush({ log_to_file: false });
    fixture.detectChanges();

    expect(checkbox.checked).toBe(false);
  });

  it('shows an error state when the initial load fails', () => {
    const fixture = setup();
    fixture.detectChanges();

    httpMock
      .expectOne('http://localhost:8000/v1/admin/settings/log-destination')
      .flush({ detail: 'error' }, { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text(fixture).toLowerCase()).toContain('could not load');
  });

  it('shows an error state and keeps the last confirmed value when saving fails', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock
      .expectOne('http://localhost:8000/v1/admin/settings/log-destination')
      .flush({ log_to_file: true });
    fixture.detectChanges();

    const checkbox: HTMLInputElement = fixture.nativeElement.querySelector(
      '[data-testid="log-to-file-toggle"]'
    );
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event('change'));

    httpMock
      .expectOne('http://localhost:8000/v1/admin/settings/log-destination')
      .flush({ detail: 'error' }, { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text(fixture).toLowerCase()).toContain('could not save');
    expect(checkbox.checked).toBe(true);
  });
});
