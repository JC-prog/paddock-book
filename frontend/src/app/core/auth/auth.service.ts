import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, tap } from 'rxjs';

const AUTH_API_BASE = 'http://localhost:8000/v1/auth';

export interface AuthUser {
  id: string;
  email: string;
  department: string;
}

interface AuthResponseBody {
  access_token: string;
  user: AuthUser;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly _accessToken = signal<string | null>(null);
  private readonly _currentUser = signal<AuthUser | null>(null);

  readonly currentUser = this._currentUser.asReadonly();

  getAccessToken(): string | null {
    return this._accessToken();
  }

  login(email: string, password: string): Observable<AuthUser> {
    return this.http
      .post<AuthResponseBody>(
        `${AUTH_API_BASE}/login`,
        { email, password },
        { withCredentials: true }
      )
      .pipe(
        tap((response) => this.setSession(response)),
        map((response) => response.user)
      );
  }

  refresh(): Observable<AuthUser | null> {
    return this.http
      .post<AuthResponseBody>(`${AUTH_API_BASE}/refresh`, {}, { withCredentials: true })
      .pipe(
        tap((response) => this.setSession(response)),
        map((response) => response.user),
        catchError(() => {
          this.clearSession();
          return of(null);
        })
      );
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${AUTH_API_BASE}/logout`, {}, { withCredentials: true }).pipe(
      tap(() => this.clearSession()),
      catchError(() => {
        this.clearSession();
        return of(undefined);
      })
    );
  }

  private setSession(response: AuthResponseBody): void {
    this._accessToken.set(response.access_token);
    this._currentUser.set(response.user);
  }

  private clearSession(): void {
    this._accessToken.set(null);
    this._currentUser.set(null);
  }
}
