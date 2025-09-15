import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  NgZone,
  OnInit,
  OnDestroy,
  signal,
  untracked,
  viewChild,
  ViewChild,
  ElementRef,
} from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { Location } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';

import { InfiniteScrollComponent } from '@ngx-templates/shared/infinite-scroll';
import { List } from 'immutable';

import {
  ChatInputComponent,
  InputEvent,
} from './shared/chat-input/chat-input.component';
import { ChatbotService } from '../data-access/chatbot.service';
import { AgentService } from '../data-access/agent.service';
import { AuthService } from '../services/auth.service';
import { QueryComponent } from './shared/query/query.component';
import { ChatIntroComponent } from './shared/chat-intro/chat-intro.component';
import { QuerySkeletonComponent } from './shared/query-skeleton/query-skeleton.component';
import { Query } from '../../model';
import { RoutePrefix } from '../route-prefixes';
import { environment } from '../../environments/environment';

@Component({
  selector: 'acb-chat',
  imports: [
    ChatInputComponent,
    QueryComponent,
    ChatIntroComponent,
    InfiniteScrollComponent,
    QuerySkeletonComponent,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatComponent implements OnInit, OnDestroy {
  private _route = inject(ActivatedRoute);
  private _agentService = inject(AgentService);
  private _auth = inject(AuthService);
  private _location = inject(Location);
  private _router = inject(Router);
  private _zone = inject(NgZone);
  
  // Make chatbot service public for template access
  chatbot = inject(ChatbotService);

  input = viewChild.required<ChatInputComponent>('input');

  loading = signal<boolean>(false);
  chatId = signal<string>('');
  currentChat = signal<any>(null);
  chatQueries = signal<List<Query>>(List());
  // Flag to indicate when we're in the process of loading to prevent duplicate renders
  isInitializing = signal<boolean>(true);
  // Error signal for displaying error messages
  error = signal<string | null>(null);
  // Map to track which chats are currently being loaded
  private _loadingChats = new Map<string, Promise<void>>();

  private _lastMessage = '';
  private _markQueryCompleted?: () => void;
  private _previousQueryCount = 0;
  chat = computed(() => this.currentChat());
  queries = computed(() => {
    // If we have a temp chat, use its queries
    const tempChat = this.chatbot.tempChat();
    if (tempChat) {
      console.log('Using temp chat queries:', tempChat.queries.size);
      return tempChat.queries;
    }
    // Otherwise use the regular chat queries
    const regularQueries = this.chatQueries();
    console.log('Using regular chat queries:', regularQueries.size);
    return regularQueries;
  });
  
  // Computed property to check if we're loading more queries
  isLoadingMore = computed(() => {
    const chatId = this.chatId();
    return chatId && this.chatbot.chatsState() === 'loading';
  });

  constructor() {
    // Simple constructor - logic moved to ngOnInit for clarity
    // Listen for changes in the chatbot service and update local state
    effect(() => {
      const chatId = this.chatId();
      if (chatId) {
        // Get the chat from the chatbot service
        const chats = this.chatbot.chats();
        const chat = chats.get(chatId);
        if (chat) {
          // Update local chat queries when chatbot service updates
          console.log(`Updating local chat queries for ${chatId}: ${this.chatQueries().size} -> ${chat.queries.size}`);
          
          // Check if new queries were added
          const previousCount = this._previousQueryCount;
          const newCount = chat.queries.size;
          this._previousQueryCount = newCount;
          
          this.chatQueries.set(chat.queries);
          
          // Auto-scroll to bottom if new queries were added
          if (newCount > previousCount) {
            this.scrollToBottom();
          }
        }
      }
    });
    
    // Add a global click handler to restore scroll if it gets stuck
    document.addEventListener('click', this.restoreScrollIfNeeded.bind(this));
  }

  async ngOnInit() {
    // Ensure body scroll is not stuck from any previous modal
    document.body.style.overflow = '';
    
    // Wait for authentication to complete
    if (this._auth.isLoading()) {
      await new Promise(resolve => {
        const checkAuth = () => {
          if (!this._auth.isLoading()) {
            resolve(void 0);
          } else {
            setTimeout(checkAuth, 100);
          }
        };
        checkAuth();
      });
    }

    if (!this._auth.isAuthenticated()) {
      return;
    }

    // Set up router listener for proper navigation handling
    this._setupRouterListener();

    // Listen for route param changes and reload chat
    this._route.paramMap.subscribe(async params => {
      const chatId = params.get('id');
      if (chatId) {
        await this.loadSpecificChat(chatId);
      } else {
        // For new chats, ensure we're in a clean state
        this.loading.set(false);
        this.chatId.set('');
        this.currentChat.set(null);
        this.chatQueries.set(List());
      }
      
      // Mark initialization as complete
      this.isInitializing.set(false);
    });
  }

  ngOnDestroy() {
    // Clean up global event listener
    document.removeEventListener('click', this.restoreScrollIfNeeded.bind(this));
    
    // Ensure body scroll is restored
    document.body.style.overflow = '';
  }

  async send(e: InputEvent) {
    this._lastMessage = e.message;
    this._markQueryCompleted = e.complete;
    this.error.set(null); // Clear any previous errors

    try {
      await this._send(e.message, e.files);
      // Auto-scroll to bottom after sending
      this.scrollToBottom();
      // Mark query as completed if successful
      if (this._markQueryCompleted) {
        this._markQueryCompleted();
      }
    } catch (err) {
      console.error('Error sending message:', err);
      // Display a user-friendly error message
      if (err instanceof Error) {
        this.error.set(err.message);
      } else {
        this.error.set('An unexpected error occurred. Please try again.');
      }
      // Don't call markQueryCompleted here - let the user decide to retry or not
    }
  }

  async sendPredefined(message: string) {
    this._lastMessage = message;
    
    this._send(message); // No files for predefined messages
    this.input().focus();
    // Auto-scroll to bottom after sending
    this.scrollToBottom();
  }

  /**
   * Handle agent selection changes from the agent selector component
   */
  onAgentSelectionChanged(selectedAgentNames: string[]) {
    // For now, we're just logging the selected agents
    // In the future, we might want to save this selection or use it in some other way
    console.log('Selected agents changed:', selectedAgentNames);
  }

  abort() {
    if (this._markQueryCompleted) {
      this._markQueryCompleted();
    }
    this.chatbot.abortLastQuery();
    this._lastMessage = '';
  }

  async loadNextPage(complete: () => void) {
    // Set loading state while fetching more queries
    this.loading.set(true);
    try {
      await this.chatbot.loadChatQueries(this.chatId());
    } finally {
      this.loading.set(false);
      complete();
    }
  }

  /**
   * Performs a check whether the last query
   * in the list is a newly a created.
   */
  isNewQuery(q: Query): boolean {
    // This is the only viable approach given our data model design
    // (since we use a dummy message before receiving the actual response).
    const queries = this.queries();
    const lastQuery = queries.size > 0 ? queries.last() : null;
    
    const isNew = !!(
      lastQuery && 
      q.id === lastQuery.id &&
      (!!q.response || q.status === 'failed') &&
      q.message === this._lastMessage
    );

    if (isNew) {
      // This is rather unconventional approach that shouldn't
      // be used, but it's important to clear the last message
      // after we find the new query in order to avoid any
      // potential side effects and/or bugs.
      this._zone.runOutsideAngular(() => {
        setTimeout(() => {
          this._lastMessage = '';
        });
      });
    }

    return isNew;
  }

  /**
   * Scroll to the bottom of the conversation
   */
  private scrollToBottom(): void {
    // Use setTimeout to ensure DOM is updated before scrolling
    setTimeout(() => {
      const conversationElement = document.querySelector('.conversation');
      if (conversationElement) {
        conversationElement.scrollTop = conversationElement.scrollHeight;
      }
    }, 0);
  }
  
  /**
   * Restore scroll if it gets stuck (emergency fallback)
   */
  private restoreScrollIfNeeded(): void {
    // Check if any modal is currently open by looking for modal elements
    const imageModal = document.querySelector('acb-image-modal.modal-open');
    const pdfModal = document.querySelector('acb-pdf-viewer[data-open="true"]');
    
    // If no modals are open but body overflow is hidden, restore it
    if (!imageModal && !pdfModal && document.body.style.overflow === 'hidden') {
      console.log('Restoring scroll - no modals open but body overflow was hidden');
      document.body.style.overflow = '';
    }
  }

  private async loadSpecificChat(chatId: string) {
    // Prevent loading the same chat multiple times
    if (this.chatId() === chatId && this.currentChat() && this.queries().size > 0) {
      console.log('Chat already loaded, skipping:', chatId);
      return;
    }
    
    // Check if this chat is already being loaded
    if (this._loadingChats.has(chatId)) {
      console.log('Chat already being loaded, waiting:', chatId);
      return this._loadingChats.get(chatId);
    }
    
    console.log('Loading specific chat:', chatId);
    this.loading.set(true);
    this.chatId.set(chatId);

    // Create a promise for this chat load
    const loadPromise = (async () => {
      try {
        // Directly fetch the chat from the API
        const response = await this._auth.authenticatedFetch(`${environment.apiUrl}/chats/${chatId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch chat: ${response.status}`);
        }

        const chatData = await response.json();
        console.log('Chat data received:', chatData);
        
        // Transform the chat data to match our expected format
        const transformedChatData = {
          ...chatData,
          queries: chatData.items || chatData.queries || [],
          total_queries: chatData.total || chatData.total_queries || 0
        };
        
        // Set the chat data
        this.currentChat.set(transformedChatData);

        // Initialize the page tracking for this chat
        this.chatbot.initializeChatPage(chatId);

        // Fetch first page of queries for this chat
        await this.chatbot.loadChatQueries(chatId);

      } catch (error) {
        console.error('Error loading chat:', error);
        // Redirect to main chat if error
        this._router.navigate(['/chat'], { replaceUrl: true });
      } finally {
        this.loading.set(false);
        // Mark initialization as complete
        this.isInitializing.set(false);
        // Remove from loading map
        this._loadingChats.delete(chatId);
        // Auto-scroll to bottom after loading
        this.scrollToBottom();
      }
    })();

    // Store the promise in the map
    this._loadingChats.set(chatId, loadPromise);
    return loadPromise;
  }

  private async _send(message: string, files?: File[]) {
    const chatId = this.chatId();
    // Use agent names instead of IDs
    let selectedAgentNames = this._agentService.selectedAgentNames();

    // For admin users, if no agents are selected, automatically select all agents
    if (this._auth.isAdmin() && selectedAgentNames.length === 0) {
      const allAgentNames = this._agentService.agents().map(agent => agent.name);
      selectedAgentNames = allAgentNames;
    }

    if (chatId) {
      await this.chatbot.sendQuery(chatId, message, files, selectedAgentNames);
    } else {
      const chat = await this.chatbot.createChat(message, files, selectedAgentNames);

      if (chat) {
        // Navigate to the new chat instead of just updating the URL
        // This will properly trigger the route parameter change event
        this._router.navigate([RoutePrefix.Chat, chat.id]);
      }
    }
  }

  // Listen for router events to handle navigation properly
  private _setupRouterListener() {
    // Listen for navigation events to handle browser back/forward buttons
    this._router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        // Check if we're on a chat route
        if (event.url.startsWith('/chat')) {
          // Extract chat ID from URL
          const urlParts = event.url.split('/');
          const chatId = urlParts.length > 2 ? urlParts[2] : '';
          
          // If we have a chat ID and it's different from current, load it
          if (chatId && chatId !== this.chatId()) {
            this.loadSpecificChat(chatId);
          } else if (!chatId && this.chatId()) {
            // If we're going back to a new chat, reset state
            this.chatId.set('');
            this.currentChat.set(null);
            this.chatQueries.set(List());
          }
        }
      }
    });
  }
}
