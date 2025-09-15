import { computed, inject, Injectable, signal } from '@angular/core';
import { Map, List } from 'immutable';

import { Chat, Query } from '../../model';
import { ChatbotApi } from '../api/chatbot-api.service';

type ItemState = 'null' | 'loading' | 'loaded';

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private _chatbotApi = inject(ChatbotApi);

  private _chats = signal<Map<string, Chat>>(Map());
  private _chatsState = signal<ItemState>('null');
  private _chatsPages = signal<Map<string, number>>(Map());
  private _tempChat = signal<Chat | null>(null);
  private _lastUsedChat: string = '';

  /**
   * All loaded chats.
   */
  chats = this._chats.asReadonly();

  /**
   * Temp/dummy chat used until a new chat is created.
   */
  tempChat = this._tempChat.asReadonly();

  /**
   * Keeps the state of chats.
   */
  chatsState = this._chatsState.asReadonly();

  /**
   * Chat pages.
   */
  chatsPages = this._chatsPages.asReadonly();

  /**
   * Returns all chats sorted in chronological order.
   */
  sortedChats = computed(() =>
    this._chats()
      .toList()
      .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()),
  );

  async loadChats() {
    if (this._chatsState() === 'loading') {
      return; // Prevent multiple concurrent loads
    }
    
    this._chatsState.set('loading');
    
    try {
      const chats = await this._chatbotApi.getChats();
      console.log(`Loaded ${chats.size} chats from API`);
      this._chats.update((c) => c.concat(chats));
      this._chatsState.set('loaded');
    } catch (error) {
      console.error('Failed to load chats:', error);
      this._chatsState.set('null'); // Reset state so it can be retried
      throw error;
    }
  }

  async loadChatQueries(chatId: string) {
    const page = this._chatsPages().get(chatId) || 1;
    console.log(`Loading queries for chat ${chatId}, page ${page}`);
    this._chatsPages.update((p) => p.set(chatId, page + 1));

    const queries = await this._chatbotApi.getChatQueries(chatId, { page });

    this._updateChatQueries(chatId, (q) => q.concat(queries), false);
  }

  /**
   * Initialize the page tracking for a chat to start from page 1
   */
  initializeChatPage(chatId: string) {
    this._chatsPages.update((p) => p.set(chatId, 1));
  }

  async createChat(message: string, files?: File[], selectedAgents?: string[]) {
    console.log('Creating new chat with message:', message);
    // We need to create a dummy chat for visualization
    // purposes, until we receive a response from the API.
    const dummyQuery = this._createDummyQuery(message);
    this._tempChat.set(
      new Chat({
        queries: List([dummyQuery]),
      }),
    );
    
    try {
      const chat = await this._chatbotApi.createChat(message, files, selectedAgents);

      if (chat) {
        console.log('Chat created successfully:', chat.id);
        this._tempChat.set(null); // Unset temp/dummy chat.
        this._chats.update((c) => c.set(chat.id, chat));
        this._chatsPages.update((p) => p.set(chat.id, 1));
      } else {
        // If chat creation failed or returned undefined, refresh the entire chat list
        console.log('Chat creation returned undefined, refreshing chat list...');
        this._tempChat.set(null);
        await this.refreshChats();
      }

      return chat;
    } catch (error) {
      console.error('Error creating chat:', error);
      
      // Create a failed query to show the error in the temp chat
      const failedQuery = new Query({
        id: dummyQuery.id,
        message: message,
        response: '',
        createdAt: dummyQuery.createdAt,
        status: 'failed',
        errorMessage: error instanceof Error ? error.message : 'Failed to create chat. Please try again.'
      });
      
      // Update temp chat with failed query
      this._tempChat.set(
        new Chat({
          queries: List([failedQuery]),
        }),
      );
      
      // Re-throw the error so it can be handled by the UI
      throw error;
    }
  }

  /**
   * Force refresh of chats from the API
   */
  async refreshChats() {
    this._chatsState.set('loading');
    try {
      const chats = await this._chatbotApi.getChats();
      console.log(`Refreshing chats: ${chats.size} chats loaded`);
      this._chats.set(chats); // Replace entire chat list with fresh data
      this._chatsState.set('loaded');
    } catch (error) {
      console.error('Failed to refresh chats:', error);
      this._chatsState.set('null');
      throw error;
    }
  }

  async sendQuery(chatId: string, message: string, files?: File[], selectedAgents?: string[]) {
    // We need to create a dummy query for visualization
    // purposes, until we receive a response from the API.
    this._lastUsedChat = chatId;
    const msgQuery = this._createDummyQuery(message);
    console.log(`Creating dummy query for chat ${chatId}:`, msgQuery);
    this._updateChatQueries(chatId, (q) => q.push(msgQuery));

    try {
      const query = await this._chatbotApi.sendQuery(chatId, message, files, selectedAgents);
      this._lastUsedChat = '';

      if (query) {
        console.log(`Received actual query for chat ${chatId}:`, query);
        // Pop the dummy and push the actual query.
        this._updateChatQueries(chatId, (q) => q.pop().push(query));
        this._chats.update((c) =>
          c.set(chatId, c.get(chatId)!.set('updatedAt', new Date())),
        );
      }
    } catch (error) {
      this._lastUsedChat = '';
      console.error('Error sending query:', error);
      
      // Create a failed query instead of just removing the dummy
      const failedQuery = new Query({
        id: msgQuery.id,
        message: message,
        response: '',
        createdAt: msgQuery.createdAt,
        status: 'failed',
        errorMessage: error instanceof Error ? error.message : 'An unexpected error occurred. Please try again.'
      });
      
      // Replace the dummy query with the failed query
      this._updateChatQueries(chatId, (q) => q.pop().push(failedQuery));
      
      // Re-throw the error so it can be handled by the UI
      throw error;
    }
  }

  deleteChat(chatId: string) {
    return this._chatbotApi.deleteChat(chatId).then(() => {
      this._chats.update((c) => c.delete(chatId));
    });
  }

  abortLastQuery() {
    if (this._tempChat()) {
      this._tempChat.set(null);
    }
    if (this._lastUsedChat) {
      // Remove the last query (could be dummy or failed)
      this._updateChatQueries(this._lastUsedChat, (q) => q.pop());
      this._lastUsedChat = '';
    }

    this._chatbotApi.abortLastQuery();
  }

  private _updateChatQueries(
    chatId: string,
    updateFn: (queries: List<Query>) => List<Query>,
    syncTotalCount: boolean = true,
  ) {
    this._chats.update((chats) => {
      let chat = chats.get(chatId)!;
      let updatedQueries = updateFn(chat.queries);
      
      // Remove duplicate queries by ID
      const uniqueQueries = List<Query>(updatedQueries.filter((query, index, self) => 
        index === self.findIndex(q => q.id === query.id)
      ));
      
      // If we removed duplicates, use the unique list
      if (uniqueQueries.size !== updatedQueries.size) {
        updatedQueries = uniqueQueries;
      }
      
      let totalChange = 0;

      // Debugging: log query counts before and after update
      console.log(`Updating chat ${chatId}: ${chat.queries.size} -> ${updatedQueries.size} queries`);
      
      // We are usually syncing when there is new
      // content as opposed to just loading existing
      // content.
      if (syncTotalCount) {
        totalChange =
          updatedQueries.size > chat.queries.size
            ? 1
            : updatedQueries.size < chat.queries.size
              ? -1
              : 0;
      }

      chat = chat
        .set('queries', updatedQueries)
        .set('totalQueries', chat.totalQueries + totalChange);

      return chats.set(chat.id, chat);
    });
  }

  private _createDummyQuery(message: string) {
    return new Query({
      message,
      createdAt: new Date(),
    });
  }
}
