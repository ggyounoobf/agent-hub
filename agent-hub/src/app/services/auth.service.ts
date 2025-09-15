import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FETCH_API } from '@ngx-templates/shared/fetch';
import { environment } from '../../environments/environment';

export enum UserRole {
  ADMIN = 'admin',
  USER = 'user'
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: UserRole;
  avatar_url?: string;
  github_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface GitHubAuthResponse {
  authorization_url: string;
  state: string;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private _fetch = inject(FETCH_API);
  private _router = inject(Router);

  // Signals for reactive state management
  private _user = signal<User | null>(null);
  private _isAuthenticated = signal<boolean>(false);
  private _isLoading = signal<boolean>(true);

  // Public readonly signals
  public readonly user = this._user.asReadonly();
  public readonly isAuthenticated = this._isAuthenticated.asReadonly();
  public readonly isLoading = this._isLoading.asReadonly();

  // Role-based helper methods
  public isAdmin(): boolean {
    const user = this._user();
    return user?.role === 'admin';
  }

  public hasRole(role: UserRole): boolean {
    const user = this._user();
    return user?.role === role;
  }

  private readonly ACCESS_TOKEN_KEY = 'agent_hub_access_token';
  private readonly REFRESH_TOKEN_KEY = 'agent_hub_refresh_token';

  constructor() {
    this.initializeAuth();
  }

  /**
   * Initialize authentication state on service creation
   */
  private async initializeAuth(): Promise<void> {
    // Add a timeout to prevent infinite loading state
    const timeoutPromise = new Promise<void>((_, reject) => {
      setTimeout(() => reject(new Error('Auth initialization timeout')), 10000);
    });
    
    const initPromise = (async () => {
      const accessToken = this.getStoredAccessToken();
      if (accessToken) {
        try {
          await this.getCurrentUser();
        } catch (error) {
          // If token is invalid, try to refresh
          await this.tryRefreshToken();
        }
      }
      this._isLoading.set(false);
    })();
    
    try {
      await Promise.race([initPromise, timeoutPromise]);
    } catch (error) {
      console.error('Auth initialization error:', error);
      this._isLoading.set(false);
    }
  }

  /**
   * Get stored access token
   */
  private getStoredAccessToken(): string | null {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem(this.ACCESS_TOKEN_KEY);
    }
    return null;
  }

  /**
   * Public accessor for current access token (used by Http interceptors)
   */
  public getAccessToken(): string | null {
    return this.getStoredAccessToken();
  }

  /**
   * Get stored refresh token
   */
  private getStoredRefreshToken(): string | null {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem(this.REFRESH_TOKEN_KEY);
    }
    return null;
  }

  /**
   * Store authentication tokens
   */
  storeTokens(tokens: AuthTokens): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem(this.ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(this.REFRESH_TOKEN_KEY, tokens.refresh_token);
    }
  }

  /**
   * Clear stored tokens
   */
  private clearTokens(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(this.ACCESS_TOKEN_KEY);
      localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    }
  }

  /**
   * Get authorization headers with Bearer token
   */
  private getAuthHeaders(): HeadersInit {
    const token = this.getStoredAccessToken();
    return token
      ? { Authorization: `Bearer ${token}` }
      : {};
  }

  /**
   * Login with email and password
   */
  async loginWithCredentials(email: string, password: string): Promise<void> {
    const response = await this._fetch(`${environment.apiUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      // Handle error immediately without additional async operations
      let errorMessage = 'Invalid email or password';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // If JSON parsing fails, use default message
      }
      throw new Error(errorMessage);
    }

    const tokens: AuthTokens = await response.json();
    this.storeTokens(tokens);
    await this.getCurrentUser();
  }

  /**
   * Sign up with credentials
   */
  async signUpWithCredentials(name: string, email: string, password: string): Promise<void> {
    try {
      const response = await this._fetch(`${environment.apiUrl}/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: name,
          email,
          password
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create account');
      }

      // Account created successfully - user may need to verify email
      const result = await response.json();

      // If tokens are returned immediately (no email verification required)
      if (result.tokens) {
        this.storeTokens(result.tokens);
        await this.getCurrentUser();
      }
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    }
  }

  /**
   * Initiate GitHub OAuth login
   */
  async loginWithGitHub(): Promise<void> {
    try {
      const response = await this._fetch(`${environment.apiUrl}/auth/github/login`);

      if (!response.ok) {
        throw new Error('Failed to initiate GitHub login');
      }

      const data: GitHubAuthResponse = await response.json();

      // Store state for verification (optional)
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem('github_oauth_state', data.state);
      }

      // Redirect to GitHub OAuth
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('GitHub login error:', error);
      throw error;
    }
  }

  /**
   * Handle OAuth callback (usually called from a callback route)
   */
  async handleOAuthCallback(code: string, state?: string): Promise<void> {
    try {
      const params = new URLSearchParams({
        code,
        ...(state && { state })
      });

      const response = await this._fetch(
        `${environment.apiUrl}/auth/github/callback?${params}`
      );

      if (!response.ok) {
        throw new Error('OAuth callback failed');
      }

      const result = await response.json();

      if (result.tokens) {
        this.storeTokens(result.tokens);
        await this.getCurrentUser();

        // Wait longer for the auth state to fully initialize
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Clean up OAuth state
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.removeItem('github_oauth_state');
        }

        // Redirect to main app and refresh
        await this._router.navigate(['/chat'], { replaceUrl: true });
        
        // Simple page refresh to ensure everything loads properly
        window.location.reload();
      } else {
        throw new Error('No tokens received from OAuth callback');
      }
    } catch (error) {
      console.error('OAuth callback error:', error);
      throw error;
    }
  }

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<User> {
    const response = await this._fetch(`${environment.apiUrl}/auth/me`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to get user information');
    }

    const user: User = await response.json();
    this._user.set(user);
    this._isAuthenticated.set(true);
    this._isLoading.set(false);

    return user;
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(): Promise<void> {
    const refreshToken = this.getStoredRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this._fetch(`${environment.apiUrl}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      throw new Error('Failed to refresh token');
    }

    const tokens: AuthTokens = await response.json();
    this.storeTokens(tokens);
  }

  /**
   * Try to refresh token silently
   */
  private async tryRefreshToken(): Promise<void> {
    try {
      await this.refreshToken();
      await this.getCurrentUser();
    } catch (error) {
      // If refresh fails, clear everything and redirect to login
      this.logout();
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    const refreshToken = this.getStoredRefreshToken();

    if (refreshToken) {
      try {
        // Attempt to revoke refresh token on server
        await this._fetch(`${environment.apiUrl}/auth/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch (error) {
        // Even if server logout fails, clear local tokens
        console.warn('Server logout failed:', error);
      }
    }

    // Clear local state
    this.clearTokens();
    this._user.set(null);
    this._isAuthenticated.set(false);

    // Redirect to login or home
    this._router.navigate(['/']);
  }

  /**
   * Logout from all devices
   */
  async logoutAll(): Promise<void> {
    try {
      await this._fetch(`${environment.apiUrl}/auth/logout-all`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
      });
    } catch (error) {
      console.warn('Server logout-all failed:', error);
    }

    // Clear local state
    this.clearTokens();
    this._user.set(null);
    this._isAuthenticated.set(false);

    // Redirect to login or home
    this._router.navigate(['/']);
  }

  /**
   * Delete user account
   */
  async deleteAccount(): Promise<void> {
    const response = await this._fetch(`${environment.apiUrl}/auth/me`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to delete account');
    }

    // Clear local state
    this.clearTokens();
    this._user.set(null);
    this._isAuthenticated.set(false);

    // Redirect to home
    this._router.navigate(['/']);
  }

  /**
   * Make authenticated API call
   */
  async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = {
      ...this.getAuthHeaders(),
      ...options.headers,
    };

    const response = await this._fetch(url, {
      ...options,
      headers,
    });

    // If token is expired, try to refresh
    if (response.status === 401 && this.getStoredRefreshToken()) {
      try {
        await this.refreshToken();

        // Retry the original request with new token
        const retryHeaders = {
          ...this.getAuthHeaders(),
          ...options.headers,
        };

        return await this._fetch(url, {
          ...options,
          headers: retryHeaders,
        });
      } catch (refreshError) {
        // If refresh fails, logout
        this.logout();
        throw new Error('Authentication failed');
      }
    }

    return response;
  }
}
