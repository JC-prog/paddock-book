import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController
} from '@angular/common/http/testing';

import { HealthService, HEALTH_API_URL } from './health.service';

describe('HealthService', () => {
  let service: HealthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [HealthService]
    });
    service = TestBed.inject(HealthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('requests the backend health endpoint and returns the healthy status', () => {
    let result: unknown;
    service.getHealth().subscribe((value) => {
      result = value;
    });

    const req = httpMock.expectOne(HEALTH_API_URL);
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'ok' });

    expect(result).toEqual({ status: 'ok' });
  });

  it('propagates an error when the backend is unreachable', () => {
    let caughtError: unknown;
    service.getHealth().subscribe({
      next: () => {
        throw new Error('expected an error, got a successful response');
      },
      error: (err) => {
        caughtError = err;
      }
    });

    const req = httpMock.expectOne(HEALTH_API_URL);
    req.error(new ProgressEvent('network error'));

    expect(caughtError).toBeTruthy();
  });
});
