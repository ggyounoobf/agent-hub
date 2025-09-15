import {
  ChangeDetectionStrategy,
  Component,
  computed,
  HostBinding,
  inject,
  signal,
} from '@angular/core';
import { NavigationEnd, Router, RouterModule } from '@angular/router';
import { Location } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';

import { ThemeSwitchComponent } from '@ngx-templates/shared/theme';

import { FooterComponent } from './footer/footer.component';
import { ChatLinkComponent } from './chat-link/chat-link.component';
import { ChatbotService } from '../../data-access/chatbot.service';
import { NavigationService } from '../../data-access/navigation.service';
import { SidebarStateService } from '../../services/sidebar-state.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'acb-sidebar',
  imports: [
    RouterModule,
    FooterComponent,
    ChatLinkComponent,
  ],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SidebarComponent {
  chatbot = inject(ChatbotService);
  navigationService = inject(NavigationService);
  authService = inject(AuthService);
  private _location = inject(Location);
  private _router = inject(Router);
  private _sidebarState = inject(SidebarStateService);



  // Use the service as the single source of truth
  expanded = this._sidebarState.expanded;

  private _routerEvents = toSignal(this._router.events);

  selectedChat = computed(() => {
    const isNavEnd = this._routerEvents() instanceof NavigationEnd;
    if (isNavEnd || this.chatbot.chats().size) {
      // We can't access the route param from the sidebar since it's out of route scope.
      // We rely on the URL composition where the chat ID is last.
      return this._location.path().split('/').pop() || '';
    }
    return '';
  });

  constructor() {
    // The service now handles localStorage initialization
  }

  toggle() {
    this._sidebarState.toggle();
  }

  onMarketplaceClick(event: Event) {
    event.preventDefault();
    this.navigationService.toggleMarketplace();
  }

  @HostBinding('class.expanded')
  get isExpanded() {
    return this.expanded();
  }
}
