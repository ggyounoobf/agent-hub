import { Component, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

interface LoginData {
  email: string;
  password: string;
}

interface SignupData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  private _authService = inject(AuthService);
  private _router = inject(Router);
  private _cdr = inject(ChangeDetectorRef);

  // State management
  isLoading = this._authService.isLoading;
  isLoggingIn = false;
  isSigningUp = false;
  error = '';
  successMessage = '';
  activeTab: 'login' | 'signup' = 'login';

  // Form data
  loginData: LoginData = {
    email: '',
    password: ''
  };

  signupData: SignupData = {
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  };

  // Password visibility toggles
  showLoginPassword = false;
  showSignupPassword = false;
  showConfirmPassword = false;

  switchTab(tab: 'login' | 'signup'): void {
    this.activeTab = tab;
    this.clearMessages();
    this.resetForms();
    this.resetLoadingStates();
  }

  clearMessages(): void {
    this.error = '';
    this.successMessage = '';
  }

  resetLoadingStates(): void {
    this.isLoggingIn = false;
    this.isSigningUp = false;
  }

  resetForms(): void {
    this.loginData = { email: '', password: '' };
    this.signupData = { name: '', email: '', password: '', confirmPassword: '' };
  }

  passwordsMatch(): boolean {
    return this.signupData.password === this.signupData.confirmPassword;
  }

  onLoginSubmit(): void {
    if (!this.isLoggingIn) {
      this.loginWithCredentials();
    }
  }

  onSignupSubmit(): void {
    if (!this.isSigningUp) {
      this.signUpWithCredentials();
    }
  }

  async loginWithCredentials(): Promise<void> {
    this.isLoggingIn = true;
    this.error = '';

    try {
      await this._authService.loginWithCredentials(this.loginData.email, this.loginData.password);
      // Navigate and refresh to ensure proper initialization
      await this._router.navigate(['/chat']);
      // Small delay then refresh to ensure clean state
      setTimeout(() => window.location.reload(), 100);
    } catch (error: any) {
      // Set error immediately when caught
      this.error = error?.message || 'Login failed. Please check your credentials.';
      this.isLoggingIn = false;
      this._cdr.detectChanges(); // Force immediate UI update
      console.error('Login error:', error);
      return;
    }
    
    // Always reset loading state
    this.isLoggingIn = false;
  }

  async signUpWithCredentials(): Promise<void> {
    this.isSigningUp = true;
    this.error = '';

    try {
      if (!this.passwordsMatch()) {
        this.error = 'Passwords do not match.';
        return;
      }

      await this._authService.signUpWithCredentials(
        this.signupData.name,
        this.signupData.email,
        this.signupData.password
      );

      this.successMessage = 'Account created successfully! Please check your email to verify your account.';

      // Switch to login tab after successful signup
      setTimeout(() => {
        this.switchTab('login');
        this.successMessage = '';
      }, 3000);

    } catch (error: any) {
      // Set error immediately when caught
      this.error = error?.message || 'Failed to create account. Please try again.';
      this.isSigningUp = false;
      this._cdr.detectChanges(); // Force immediate UI update
      console.error('Signup error:', error);
      return;
    }

    // Always reset loading state
    this.isSigningUp = false;
  }

  async loginWithGitHub(): Promise<void> {
    this.isLoggingIn = true;
    this.error = '';

    try {
      await this._authService.loginWithGitHub();
    } catch (error: any) {
      // Set error immediately when caught
      this.error = 'Failed to initiate GitHub login. Please try again.';
      this.isLoggingIn = false;
      this._cdr.detectChanges(); // Force immediate UI update
      console.error('GitHub login error:', error);
      return;
    }

    // Always reset loading state
    this.isLoggingIn = false;
  }

  continueAsGuest(): void {
    // Navigate to chat without authentication
    this._router.navigate(['/chat']);
  }
}
