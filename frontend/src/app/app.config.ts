import { APP_INITIALIZER, ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './core/auth/auth.service';
import { authInterceptor } from './core/auth/auth.interceptor';
import { routes } from './app.routes';

// Blocks app bootstrap until the initial silent-refresh attempt resolves
// (success or failure — AuthService.refresh() never rejects), so the
// auth guard's currentUser() check reflects the real session state
// instead of racing an in-flight refresh call on a hard page reload.
function initializeAuth(authService: AuthService): () => Promise<unknown> {
  return () => firstValueFrom(authService.refresh());
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideRouter(routes),
    {
      provide: APP_INITIALIZER,
      useFactory: initializeAuth,
      deps: [AuthService],
      multi: true
    }
  ]
};
