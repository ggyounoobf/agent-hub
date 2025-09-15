import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { List, Map } from 'immutable';
import { marked } from 'marked';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService } from '../services/auth.service';

import { Chat, Query } from '../../model';
import { mapChat, mapChats, mapQueries, mapQuery } from './utils/mappers';

@Injectable({ providedIn: 'root' })
export class ChatbotApi {
  private http = inject(HttpClient);
  private _authService = inject(AuthService);
  private _chatStorage = new globalThis.Map<string, any[]>(); // Store chat messages locally

  constructor() {
    // Configure marked options for better formatting
    marked.setOptions({
      breaks: true, // Convert line breaks to <br>
      gfm: true, // GitHub flavored markdown
    });
  }

  // Clean response and apply markdown parsing
  private async formatResponse(content: string): Promise<string> {
    // First clean the content
    const cleaned = content
      // Remove duplicate separators
      .replace(/---+/g, '\n---\n')
      // Add proper spacing around headers
      .replace(/^(#+\s*.*$)/gm, '\n$1\n')
      // Clean up code blocks
      .replace(/```(\w+)?\n?/g, '\n```$1\n')
      // Remove excessive whitespace
      .replace(/\n{3,}/g, '\n\n')
      // Clean up the start and end
      .trim();

    // Then convert markdown to HTML (await the promise)
    return await marked(cleaned);
  }

  // Keep the old cleanResponse method for backwards compatibility
  private async cleanResponse(content: string): Promise<string> {
    return await this.formatResponse(content);
  }

  /**
   * Check if localStorage is available (browser environment)
   */
  private isLocalStorageAvailable(): boolean {
    return typeof Storage !== 'undefined' && typeof localStorage !== 'undefined';
  }

  /**
   * Get data from localStorage safely
   */
  private getFromLocalStorage(key: string): string | null {
    if (this.isLocalStorageAvailable()) {
      return localStorage.getItem(key);
    }
    return null;
  }

  /**
   * Set data to localStorage safely
   */
  private setToLocalStorage(key: string, value: string): void {
    if (this.isLocalStorageAvailable()) {
      localStorage.setItem(key, value);
    }
  }

  /**
   * Fetches all available chats without their queries.
   * Uses authenticated API if user is logged in, otherwise falls back to local storage.
   */
  async getChats(): Promise<Map<string, Chat>> {
    if (this._authService.isAuthenticated()) {
      try {
        const data = await firstValueFrom(
          this.http.get<any>(`${environment.apiUrl}/chats/`, {
            withCredentials: true
          })
        );
        
        const chats = data.items || [];
        return mapChats(chats);
      } catch (error) {
        console.warn('Failed to fetch chats from API, falling back to local storage:', error);
      }
    }

    // Fallback to local storage
    const chatsData = this.getFromLocalStorage('nexus-chats');
    const chats = chatsData ? JSON.parse(chatsData) : {};

    // Load messages from storage into memory
    Object.entries(chats).forEach(([chatId, chatData]: [string, any]) => {
      if (chatData.messages && !this._chatStorage.has(chatId)) {
        this._chatStorage.set(chatId, chatData.messages);
      }
    });

    return mapChats(Object.values(chats));
  }

  /**
   * Fetches queries for a specific chat with pagination.
   */
  async getChatQueries(chatId: string, options: { page: number }): Promise<List<Query>> {
    if (this._authService.isAuthenticated()) {
      try {
        const data = await firstValueFrom(
          this.http.get<any>(`${environment.apiUrl}/chats/${chatId}/queries?page=${options.page}`, {
            withCredentials: true
          })
        );
        
        const queries = data.items || [];
        return mapQueries(queries);
      } catch (error) {
        console.warn('Failed to fetch chat queries from API, falling back to local storage:', error);
      }
    }

    // Fallback to local storage
    let chatMessages = this._chatStorage.get(chatId) || [];
    if (chatMessages.length === 0) {
      const chatsData = this.getFromLocalStorage('nexus-chats');
      const chats = chatsData ? JSON.parse(chatsData) : {};
      const storedMessages = chats[chatId]?.messages || [];
      if (storedMessages.length > 0) {
        chatMessages = storedMessages;
        this._chatStorage.set(chatId, chatMessages);
      }
    }

    const pageSize = 20;
    const startIndex = (options.page - 1) * pageSize;
    const endIndex = startIndex + pageSize;

    const queries: any[] = [];
    for (let i = 0; i < chatMessages.length; i += 2) {
      const userMessage = chatMessages[i];
      const assistantMessage = chatMessages[i + 1];

      if (userMessage && userMessage.role === 'user') {
        // Create proper timestamps that maintain chronological order
        const baseTime = new Date();
        baseTime.setMinutes(baseTime.getMinutes() - (chatMessages.length - i) * 5); // 5 minutes apart
        
        queries.push({
          id: `${chatId}-${i}`,
          message: userMessage.content,
          response: assistantMessage?.content || '',
          created_at: baseTime.toISOString(),
          files_uploaded: userMessage.files_uploaded || []
        });
      }
    }

    const paginatedQueries = queries.slice(startIndex, endIndex);
    return mapQueries(paginatedQueries);
  }

  /**
   * Creates a new chat by a provided initial/start message with optional files.
   */
  async createChat(message: string, files?: File[], selectedAgents?: string[]): Promise<Chat | undefined> {
    if (this._authService.isAuthenticated()) {
      try {
        // Use the improved multi-agent-query endpoint
        const formData = new FormData();
        formData.append('prompt', message);
        
        if (selectedAgents && selectedAgents.length > 0) {
          formData.append('agent_name', selectedAgents.join(','));
        }

        if (files && files.length > 0) {
          files.forEach(file => {
            formData.append('files', file);
          });
        }

        const result = await firstValueFrom(
          this.http.post<any>(`${environment.apiUrl}/agents/multi-agent-query`, formData, {
            withCredentials: true
          })
        );

        console.log('✅ createChat API response:', result);

        // The API returns a query response with chat_id
        if (result.chat_id) {
          try {
            console.log('🔄 Fetching chat details for ID:', result.chat_id);
            const chat = await firstValueFrom(
              this.http.get<any>(`${environment.apiUrl}/chats/${result.chat_id}`, {
                withCredentials: true
              })
            );
            console.log('✅ Fetched chat details:', chat);
            
            const mappedChat = mapChat(chat);
            console.log('✅ Mapped chat:', mappedChat);
            return mappedChat;
          } catch (error) {
            console.error('❌ Error fetching chat:', error);
          }
        } else {
          console.error('❌ No chat_id in API response:', result);
        }
        
        return undefined;
      } catch (error) {
        console.warn('Failed to create chat via API, falling back to local method:', error);
      }
    }

    // Fallback to local storage method
    const chatId = Date.now().toString();

    // Use FormData for file uploads
    const formData = new FormData();
    formData.append('prompt', message);

    if (!selectedAgents || selectedAgents.length === 0) {
      throw new Error('No agent selected. Please select an agent before proceeding.');
    }

    const agentName = selectedAgents[0];
    console.log('createChat using agent:', agentName);
    formData.append('agent_name', agentName);

    // Add files if provided
    if (files && files.length > 0) {
      files.forEach(file => {
        formData.append('files', file);
      });
    }

    try {
      const result = await firstValueFrom(
        this.http.post<any>(`${environment.apiUrl}/agents/multi-agent-query`, formData, {
          withCredentials: true
        })
      );

      console.log('createChat result:', result);

      // Format the response content with markdown parsing
      const formattedResponse = await this.formatResponse(result.response || "No response received");

      // Create files_uploaded structure for local storage
      const filesUploaded = files?.map(file => ({ 
        id: this.generateFileId(),
        name: file.name, 
        uploaded_at: new Date().toISOString() 
      })) || [];

      const userMessage = { 
        role: "user", 
        content: message, 
        files_uploaded: filesUploaded 
      };
      const assistantMessage = { role: "assistant", content: formattedResponse };

      const chatMessages = [userMessage, assistantMessage];

      this._chatStorage.set(chatId, chatMessages);

      // Store in localStorage for persistence
      const chatsData = this.getFromLocalStorage('nexus-chats');
      const allChats = chatsData ? JSON.parse(chatsData) : {};
      const chat = {
        id: chatId,
        title: message.substring(0, 50) + '...',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        total_queries: 1,
        queries: [], // Will be populated by getChatQueries
        messages: chatMessages // Store messages with file info
      };

      allChats[chatId] = chat;
      this.setToLocalStorage('nexus-chats', JSON.stringify(allChats));

      return mapChat(chat);
    } catch (error) {
      console.error('Error in createChat fallback:', error);
    }

    return undefined;
  }

  /**
   * Sends a query to an existing chat with optional files.
   */
  async sendQuery(chatId: string, message: string, files?: File[], selectedAgents?: string[]): Promise<Query | undefined> {
    if (this._authService.isAuthenticated()) {
      try {
        // Use the improved multi-agent-query endpoint
        const formData = new FormData();
        formData.append('prompt', message);
        formData.append('chat_id', chatId);
        
        if (selectedAgents && selectedAgents.length > 0) {
          formData.append('agent_name', selectedAgents.join(','));
        }

        if (files && files.length > 0) {
          files.forEach(file => {
            formData.append('files', file);
          });
        }

        const result = await firstValueFrom(
          this.http.post<any>(`${environment.apiUrl}/agents/multi-agent-query`, formData, {
            withCredentials: true
          })
        );

        console.log('sendQuery result:', result);
        
        return mapQuery(result);
      } catch (error) {
        console.error('Error in sendQuery:', error);
        // Re-throw the error so it can be handled by the calling code
        throw error;
      }
    }

    // Fallback to local storage method
    const formData = new FormData();
    formData.append('prompt', message);
    formData.append('chat_id', chatId);

    if (!selectedAgents || selectedAgents.length === 0) {
      throw new Error('No agent selected. Please select an agent before proceeding.');
    }

    const agentName = selectedAgents[0];
    console.log('sendQuery using agent:', agentName);
    formData.append('agent_name', agentName);

    // Add files if provided
    if (files && files.length > 0) {
      files.forEach(file => {
        formData.append('files', file);
      });
    }

    try {
      const result = await firstValueFrom(
        this.http.post<any>(`${environment.apiUrl}/agents/multi-agent-query`, formData, {
          withCredentials: true
        })
      );

      console.log('sendQuery result:', result);

      // Format the response content with markdown parsing
      const formattedResponse = await this.formatResponse(result.response || "No response received");

      const existingMessages = this._chatStorage.get(chatId) || [];
      
      // Create files_uploaded structure for local storage
      const filesUploaded = files?.map(file => ({ 
        id: this.generateFileId(),
        name: file.name, 
        uploaded_at: new Date().toISOString() 
      })) || [];
      
      const userMessage = { 
        role: "user", 
        content: message, 
        files_uploaded: filesUploaded 
      };
      const assistantMessage = { role: "assistant", content: formattedResponse };

      const updatedMessages = [...existingMessages, userMessage, assistantMessage];
      this._chatStorage.set(chatId, updatedMessages);

      // Update localStorage
      const chatsData = this.getFromLocalStorage('nexus-chats');
      const allChats = chatsData ? JSON.parse(chatsData) : {};
      if (allChats[chatId]) {
        allChats[chatId].messages = updatedMessages;
        allChats[chatId].updatedAt = new Date().toISOString();
        allChats[chatId].totalQueries = Math.floor(updatedMessages.length / 2);
        this.setToLocalStorage('nexus-chats', JSON.stringify(allChats));
      }

      // Create a query object with file information
      const queryWithFiles = {
        id: Date.now().toString(),
        message: message,
        response: formattedResponse,
        created_at: new Date().toISOString(),
        files_uploaded: filesUploaded
      };

      return mapQuery(queryWithFiles);
    } catch (error) {
      console.error('Error in sendQuery fallback:', error);
      // Re-throw the error so it can be handled by the calling code
      throw error;
    }

    return undefined;
  }

  /**
   * Deletes a chat.
   */
  async deleteChat(chatId: string): Promise<void> {
    if (this._authService.isAuthenticated()) {
      try {
        await firstValueFrom(
          this.http.delete(`${environment.apiUrl}/chats/${chatId}`, {
            withCredentials: true
          })
        );
        return;
      } catch (error) {
        console.warn('Failed to delete chat via API, falling back to local method:', error);
      }
    }

    // Fallback to local storage method
    this._chatStorage.delete(chatId);

    // Remove from localStorage
    const chatsData = this.getFromLocalStorage('nexus-chats');
    const chats = chatsData ? JSON.parse(chatsData) : {};
    delete chats[chatId];
    this.setToLocalStorage('nexus-chats', JSON.stringify(chats));

    return;
  }

  /**
   * Aborts the last query, if in progress.
   */
  abortLastQuery() {
    // Note: HttpClient doesn't have the same abort functionality as fetch
    // You might need to implement this using takeUntil with a Subject
    // or use HttpInterceptor for cancellation
    console.log('Abort functionality needs to be implemented for HttpClient');
  }
  
  /**
   * Generate a simple file ID for local storage
   */
  private generateFileId(): string {
    return 'file-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  }
}