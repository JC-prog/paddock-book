import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AuthService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('starts with no current user and no access token', () => {
    expect(service.currentUser()).toBeNull();
    expect(service.getAccessToken()).toBeNull();
  });

  it('login() stores the access token in memory and exposes the current user', () => {
    service.login('driver@team.example', 'secret').subscribe();

    const req = httpMock.expectOne('http://localhost:8000/v1/auth/login');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      access_token: 'an-access-token',
      user: { id: 'u1', email: 'driver@team.example', department: 'sporting' }
    });

    expect(service.getAccessToken()).toBe('an-access-token');
    expect(service.currentUser()).toEqual({ id: 'u1', email: 'driver@team.example', department: 'sporting' });
  });

  it('does not persist the access token to localStorage or sessionStorage', () => {
    service.login('driver@team.example', 'secret').subscribe();
    httpMock.expectOne('http://localhost:8000/v1/auth/login').flush({
      access_token: 'an-access-token',
      user: { id: 'u1', email: 'driver@team.example', department: 'sporting' }
    });

    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it('refresh() restores a session when the refresh cookie is valid', () => {
    service.refresh().subscribe();

    const req = httpMock.expectOne('http://localhost:8000/v1/auth/refresh');
    expect(req.request.withCredentials).toBe(true);
    req.flush({
      access_token: 'a-refreshed-token',
      user: { id: 'u1', email: 'driver@team.example', department: 'sporting' }
    });

    expect(service.getAccessToken()).toBe('a-refreshed-token');
    expect(service.currentUser()).not.toBeNull();
  });

  it('refresh() leaves the user logged out when the refresh cookie is invalid', () => {
    service.refresh().subscribe();

    const req = httpMock.expectOne('http://localhost:8000/v1/auth/refresh');
    req.flush({ detail: 'Not authenticated' }, { status: 401, statusText: 'Unauthorized' });

    expect(service.getAccessToken()).toBeNull();
    expect(service.currentUser()).toBeNull();
  });

  it('register() stores the access token in memory and exposes the current user', () => {
    service.register('newdriver@team.example', 'secret', 'technical').subscribe();

    const req = httpMock.expectOne('http://localhost:8000/v1/auth/register');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body).toEqual({
      email: 'newdriver@team.example',
      password: 'secret',
      department: 'technical'
    });
    req.flush({
      access_token: 'a-new-access-token',
      user: { id: 'u2', email: 'newdriver@team.example', department: 'technical' }
    });

    expect(service.getAccessToken()).toBe('a-new-access-token');
    expect(service.currentUser()).toEqual({
      id: 'u2',
      email: 'newdriver@team.example',
      department: 'technical'
    });
  });

  it('register() propagates the error and leaves the user logged out on failure (e.g. duplicate email)', () => {
    service.register('taken@team.example', 'secret', 'sporting').subscribe({ error: () => {} });

    const req = httpMock.expectOne('http://localhost:8000/v1/auth/register');
    req.flush({ detail: 'duplicate' }, { status: 422, statusText: 'Unprocessable Entity' });

    expect(service.getAccessToken()).toBeNull();
    expect(service.currentUser()).toBeNull();
  });
});
