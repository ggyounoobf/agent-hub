import { HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * Attaches Authorization bearer token to outgoing HTTP requests targeting the API host.
 * Also can be extended later for automatic refresh logic for HttpClient calls (currently handled in fetch flow).
 */
export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<any>, next: HttpHandlerFn) => {
  const auth = inject(AuthService);
  const token = auth.getAccessToken();

  // Only add header if token exists and header not already set
  if (token && !req.headers.has('Authorization')) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }

  // Temporary debug (remove in production):
  // console.debug('[authInterceptor] Request', req.url, 'Auth header set:', req.headers.has('Authorization'));

  return next(req);
};
