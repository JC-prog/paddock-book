import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

describe('authInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let authServiceStub: Partial<AuthService>;

  beforeEach(() => {
    authServiceStub = { getAccessToken: () => null };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceStub }
      ]
    });

    httpClient = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('attaches an Authorization header when a token is held', () => {
    authServiceStub.getAccessToken = () => 'a-token';

    httpClient.get('/some-endpoint').subscribe();

    const req = httpMock.expectOne('/some-endpoint');
    expect(req.request.headers.get('Authorization')).toBe('Bearer a-token');
  });

  it('does not attach an Authorization header when logged out', () => {
    httpClient.get('/some-endpoint').subscribe();

    const req = httpMock.expectOne('/some-endpoint');
    expect(req.request.headers.has('Authorization')).toBe(false);
  });
});
