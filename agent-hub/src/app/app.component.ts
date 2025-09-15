import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  HostListener,
  inject,
  NgModule,
  OnInit,
  ViewChild,
} from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ModalOutletComponent } from '@ngx-templates/shared/modal';
import { ToastOutletComponent } from '@ngx-templates/shared/toasts';

import { HeaderComponent } from './shared/header/header.component';
import { SidebarComponent } from './shared/sidebar/sidebar.component';
import { ChatbotService } from './data-access/chatbot.service';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'acb-root',
  imports: [
    RouterOutlet,
    HeaderComponent,
    SidebarComponent,
    ModalOutletComponent,
    ToastOutletComponent,
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  private _chatbot = inject(ChatbotService);
  private _auth = inject(AuthService);
  isMobile = window.innerWidth <= 768;

  @ViewChild(SidebarComponent) sidebar!: SidebarComponent;

  constructor() {
    // Load chats when user becomes authenticated and app is no longer loading
    effect(() => {
      const isAuthenticated = this._auth.isAuthenticated();
      const isLoading = this._auth.isLoading();
      const chatsState = this._chatbot.chatsState();
      
      if (isAuthenticated && !isLoading && chatsState === 'null') {
        // Small delay to ensure auth state is fully established
        setTimeout(() => this._chatbot.loadChats(), 100);
      }
    });
  }

  ngOnInit() {
    // Initial load if already authenticated
    if (this._auth.isAuthenticated() && !this._auth.isLoading()) {
      this._chatbot.loadChats();
    }
  }

  toggleSidebar() {
    this.sidebar?.toggle();
  }

  // Use computed for better reactivity with OnPush
  isSidebarExpanded = computed(() => {
    return this.sidebar?.expanded() || false;
  });

  @HostListener('window:resize', ['$event'])
  onResize(event: any) {
    this.isMobile = event.target.innerWidth <= 768;
  }
}
