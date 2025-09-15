import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Wait for auth loading to complete with a timeout to prevent infinite loops
  const startTime = Date.now();
  while (authService.isLoading() && (Date.now() - startTime) < 5000) { // 5 second timeout
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  // If user is authenticated, allow access
  if (authService.isAuthenticated()) {
    return true;
  }

  // If not authenticated, redirect to login
  router.navigate(['/login'], { 
    queryParams: { returnUrl: state.url } 
  });
  
  return false;
};

export const guestGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Wait for auth loading to complete with a timeout to prevent infinite loops
  const startTime = Date.now();
  while (authService.isLoading() && (Date.now() - startTime) < 5000) { // 5 second timeout
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  // If user is authenticated, redirect to chat
  if (authService.isAuthenticated()) {
    router.navigate(['/chat']);
    return false;
  }

  // If not authenticated, allow access to login/public pages
  return true;
};
