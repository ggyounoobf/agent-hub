import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';

import { provideWindow } from '@ngx-templates/shared/services';
import {
  provideFetchApi
} from '@ngx-templates/shared/fetch';
import { APP_ROUTES } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(APP_ROUTES),
    provideWindow(),
    // Register HttpClient with synchronous auth interceptor so Authorization header is applied.
    provideHttpClient(withInterceptors([
      authInterceptor
    ])),
    provideFetchApi(),
  ]
};
