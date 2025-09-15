import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-oauth-callback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="callback-container">
      <div class="callback-card">
        @if (isProcessing) {
          <div class="processing">
            <div class="spinner"></div>
            <h2>{{ progressMessage }}</h2>
            <p>Please wait while we finish setting up your account and redirect you to the chat.</p>
          </div>
        } @else if (error) {
          <div class="error">
            <div class="error-icon">⚠️</div>
            <h2>Authentication Failed</h2>
            <p>{{ error }}</p>
            <button class="retry-btn" (click)="goToLogin()">
              Try Again
            </button>
          </div>
        } @else {
          <div class="success">
            <div class="success-icon">✅</div>
            <h2>Welcome to Agent Hub!</h2>
            <p>Your account has been set up successfully.</p>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .callback-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 1rem;
    }

    .callback-card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
      padding: 3rem 2rem;
      width: 100%;
      max-width: 400px;
      text-align: center;
    }

    .processing, .error, .success {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    }

    .spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #f3f4f6;
      border-top: 4px solid #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .error-icon, .success-icon {
      font-size: 3rem;
      margin-bottom: 0.5rem;
    }

    h2 {
      font-size: 1.5rem;
      font-weight: 600;
      color: #1f2937;
      margin: 0;
    }

    p {
      color: #6b7280;
      margin: 0;
      line-height: 1.5;
    }

    .retry-btn {
      background: #667eea;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 0.75rem 1.5rem;
      font-size: 1rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      margin-top: 1rem;
    }

    .retry-btn:hover {
      background: #5a67d8;
      transform: translateY(-1px);
    }
  `]
})
export class OAuthCallbackComponent implements OnInit {
  private _route = inject(ActivatedRoute);
  private _router = inject(Router);
  private _authService = inject(AuthService);

  isProcessing = true;
  error = '';
  progressMessage = 'Completing authentication...';

  async ngOnInit(): Promise<void> {
    try {
      const params = this._route.snapshot.queryParamMap;
      const error = params.get('error');
      const success = params.get('success');
      
      if (error) {
        throw new Error(`OAuth error: ${error}`);
      }

      if (success === 'true') {
        // Extract tokens from URL parameters (from backend redirect)
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        const tokenType = params.get('token_type');
        const expiresIn = params.get('expires_in');

        if (accessToken && refreshToken) {
          // Store tokens directly
          const tokens = {
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: tokenType || 'Bearer',
            expires_in: expiresIn ? parseInt(expiresIn) : 3600
          };

          this._authService.storeTokens(tokens);
          await this._authService.getCurrentUser();
          
          this.progressMessage = 'Setting up your workspace...';
          
          // Wait longer for the auth state to fully initialize
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          this.progressMessage = 'Redirecting to chat...';
          
          // Success - redirect to main app and refresh
          this.isProcessing = false;
          await this._router.navigate(['/chat'], { replaceUrl: true });
          
          // Simple page refresh to ensure everything loads properly
          window.location.reload();
          return;
        }
      }

      // Fallback to original flow for backward compatibility
      const code = params.get('code');
      const state = params.get('state');

      if (code) {
        await this._authService.handleOAuthCallback(code, state || undefined);
        this.isProcessing = false;
        return;
      }

      throw new Error('No valid authentication data received');
      
    } catch (error) {
      console.error('OAuth callback error:', error);
      this.error = error instanceof Error ? error.message : 'An unknown error occurred';
      this.isProcessing = false;
    }
  }

  goToLogin(): void {
    this._router.navigate(['/login']);
  }
}
