import { ChangeDetectionStrategy, Component, inject, input, OnInit, signal, computed, HostBinding, ElementRef, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { toSignal } from '@angular/core/rxjs-interop';
import { FETCH_API } from '@ngx-templates/shared/fetch';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../services/auth.service';
import { ClickOutsideDirective } from '../../directives/click-outside.directive';
import { SidebarStateService } from '../../services/sidebar-state.service';

interface HealthStatus {
  status: string;
  agent_loaded: boolean;
}

@Component({
  selector: 'acb-header',
  imports: [CommonModule, ClickOutsideDirective],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HeaderComponent implements OnInit {
  private fetch = inject(FETCH_API);
  private _authService = inject(AuthService);
  private _router = inject(Router);
  private _elementRef = inject(ElementRef);
  private _sidebarState = inject(SidebarStateService);

  sidebarExpanded = input<boolean>(false);

  isConnected = signal<boolean>(false);
  healthStatus = signal<string>('checking');
  showUserMenu = signal<boolean>(false);

  // Track current route to show/hide header based on route
  private _navigationEnd = toSignal(
    this._router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd)
    )
  );

  // Show header only on chat routes
  shouldShowHeader = computed(() => {
    const nav = this._navigationEnd();
    if (!nav) return true; // Show by default

    const url = nav.url;
    const isValidRoute = url === '/' || url.startsWith('/chat') || url === '/chat';

    return isValidRoute;
  });

  // Compute sidebar width based on state
  sidebarWidth = computed(() => {
    // On mobile, sidebar doesn't affect header position
    if (typeof window !== 'undefined' && window.innerWidth <= 768) {
      return '0px';
    }

    // On desktop, adjust based on sidebar state
    return this._sidebarState.expanded() ? '280px' : '48px';
  });

  constructor() {
    // Modern Gemini-style header component aligned with sidebar

    // Update CSS custom property when sidebar state changes
    effect(() => {
      const sidebarWidth = this.sidebarWidth();
      this._elementRef.nativeElement.style.setProperty('--sidebar-width', sidebarWidth);
    });

    // Handle responsive changes
    if (typeof window !== 'undefined') {
      const handleResize = () => {
        const newWidth = window.innerWidth <= 768 ? '0px' : (this._sidebarState.expanded() ? '280px' : '48px');
        this._elementRef.nativeElement.style.setProperty('--sidebar-width', newWidth);
      };

      window.addEventListener('resize', handleResize);
    }
  }

  // Expose auth service signals
  user = this._authService.user;
  isAuthenticated = this._authService.isAuthenticated;

  async ngOnInit() {
    await this.checkHealth();
    // Check health every 30 seconds
    setInterval(() => this.checkHealth(), 30000);
  }

  async checkHealth() {
    try {
      this.healthStatus.set('checking');
      const response = await this.fetch(`${environment.apiUrl}/healthz`);

      if (response.ok) {
        const health: HealthStatus = await response.json();
        this.isConnected.set(health.status === 'ok' && health.agent_loaded);
        this.healthStatus.set(health.status === 'ok' && health.agent_loaded ? 'connected' : 'error');
      } else {
        this.isConnected.set(false);
        this.healthStatus.set('error');
      }
    } catch (error) {
      this.isConnected.set(false);
      this.healthStatus.set('error');
    }
  }

  toggleUserMenu(): void {
    this.showUserMenu.update(show => !show);
  }

  navigateToLogin(): void {
    this._router.navigate(['/login']);
  }

  logout(): void {
    this._authService.logout();
    this.showUserMenu.set(false);
  }

  logoutAll(): void {
    this._authService.logoutAll();
    this.showUserMenu.set(false);
  }

  // Toggle sidebar from header (mobile)
  toggleSidebar(): void {
    this._sidebarState.toggle();
  }
}
