import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface MultiAgentQueryRequest {
  prompt: string;
  agent_name?: string; // Comma-separated list of agent names
  files?: File[];
}

export interface MultiAgentQueryResponse {
  response: string;
  token_usage: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
  } | null;
  agent_used: string;
}

export interface ChatQueryRequest {
  prompt: string;
  chat_id: string;
  agent_name?: string; // Comma-separated list of agent names
  files?: File[];
}

@Injectable({
  providedIn: 'root'
})
export class MultiAgentQueryService {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly API_BASE = `${environment.apiUrl}`;

  /**
   * Send a multi-agent query with form data (supports file uploads)
   * @param request The query request with prompt and optional agent names and files
   */
  queryWithFormData(request: MultiAgentQueryRequest): Observable<MultiAgentQueryResponse> {
    const formData = new FormData();
    formData.append('prompt', request.prompt);
    
    if (request.agent_name) {
      console.log('MultiAgentQueryService Using Agent:', request.agent_name);
      formData.append('agent_name', request.agent_name);
    }
    
    if (request.files) {
      request.files.forEach(file => {
        formData.append('files', file);
      });
    }

    return this.http.post<MultiAgentQueryResponse>(
      `${this.API_BASE}/multi-agent-query`, 
      formData,
      { 
        withCredentials: true 
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Send a multi-agent query with JSON data (no file support, but saves to database)
   * @param request The query request with prompt and optional agent names
   */
  queryWithJSON(request: MultiAgentQueryRequest): Observable<MultiAgentQueryResponse> {
    const requestBody: any = {
      prompt: request.prompt
    };
    
    if (request.agent_name) {
      console.log('MultiAgentQueryService Using Agent:', request.agent_name);
      requestBody.agent_name = request.agent_name;
    }

    return this.http.post<MultiAgentQueryResponse>(
      `${this.API_BASE}/multi-agent-query-json`, 
      requestBody,
      { 
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Send a query to an existing chat with form data (supports file uploads)
   * @param request The chat query request with prompt, chat_id, and optional agent names and files
   */
  sendChatQueryWithFormData(request: ChatQueryRequest): Observable<MultiAgentQueryResponse> {
    const formData = new FormData();
    formData.append('prompt', request.prompt);
    formData.append('chat_id', request.chat_id);
    
    if (request.agent_name) {
      console.log('MultiAgentQueryService Using Agent:', request.agent_name);
      formData.append('agent_name', request.agent_name);
    }
    
    if (request.files) {
      request.files.forEach(file => {
        formData.append('files', file);
      });
    }

    return this.http.post<MultiAgentQueryResponse>(
      `${this.API_BASE}/multi-agent-query`, 
      formData,
      { 
        withCredentials: true 
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Send a query to an existing chat with JSON data
   * @param request The chat query request with prompt, chat_id, and optional agent names
   */
  sendChatQueryWithJSON(request: ChatQueryRequest): Observable<MultiAgentQueryResponse> {
    const requestBody: any = {
      prompt: request.prompt,
      chat_id: request.chat_id
    };
    
    if (request.agent_name) {
      console.log('MultiAgentQueryService Using Agent:', request.agent_name);
      requestBody.agent_name = request.agent_name;
    }

    return this.http.post<MultiAgentQueryResponse>(
      `${this.API_BASE}/multi-agent-query-json`, 
      requestBody,
      { 
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse) {

    if (error.status === 0) {
      // A client-side or network error occurred.
      return throwError(() => new Error('Could not connect to the server. Please check your network connection.'));
    }

    let errorMessage = 'An unknown error occurred';
    if (error.error && error.error.detail) {
      errorMessage = error.error.detail;
    } else if (error.message) {
      errorMessage = error.message;
    }

    console.error(`MultiAgentQueryService error: ${error.status}`, error.error);
    return throwError(() => new Error(errorMessage));
  }
}