import { Injectable, inject } from '@angular/core';
import { 
  MarketplaceApi, 
  Agent, 
  OwnedAgent, 
  AgentRequestResponse, 
  AgentRequest, 
  PendingRequest, 
  ReviewRequest, 
  ReviewResponse, 
  BulkReviewRequest, 
  BulkReviewResponse, 
  RevokeOwnershipRequest, 
  RevokeOwnershipResponse, 
  UserAgentStats 
} from '../api/marketplace-api.service';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class MarketplaceService {
  private readonly api = inject(MarketplaceApi);
  private readonly http = inject(HttpClient);
  private readonly API_BASE = `${environment.apiUrl}/marketplace`;

  /** Get all agents (public) */
  getAgents(): Observable<Agent[]> {
    return this.api.getAgents();
  }

  /** Get owned agents (authenticated) */
  getOwnedAgents(): Observable<OwnedAgent[]> {
    return this.api.getOwnedAgents();
  }

  /** Request agent (authenticated) */
  requestAgent(agentId: string, justification?: string): Observable<AgentRequestResponse> {
    if (justification) {
      const formData = new FormData();
      formData.append('justification', justification);
      return this.http.post<AgentRequestResponse>(`${this.API_BASE}/request-agent/${agentId}`, formData, {
        withCredentials: true
      });
    }
    return this.api.requestAgent(agentId);
  }

  /** Request agent with justification (authenticated) - for future implementation */
  requestAgentWithJustification(agentId: string, justification: string): Observable<AgentRequestResponse> {
    const formData = new FormData();
    formData.append('justification', justification);
    return this.http.post<AgentRequestResponse>(`${this.API_BASE}/request-agent/${agentId}`, formData, {
      withCredentials: true
    });
  }

  /** Get agent details (authenticated) */
  getAgentById(agentId: string): Observable<Agent> {
    return this.api.getAgentById(agentId);
  }

  /** Get agent requests (authenticated) */
  getMyRequests(): Observable<AgentRequest[]> {
    return this.api.getMyRequests();
  }

  /** Get user agent stats (authenticated) */
  getUserAgentStats(): Observable<UserAgentStats> {
    return this.api.getUserAgentStats();
  }

  /** Get pending requests (admin only) */
  getPendingRequests(): Observable<PendingRequest[]> {
    return this.api.getPendingRequests();
  }

  /** Review agent request (admin only) */
  reviewRequest(requestId: string, review: ReviewRequest): Observable<ReviewResponse> {
    return this.api.reviewRequest(requestId, review);
  }

  /** Bulk review requests (admin only) */
  bulkReviewRequests(review: BulkReviewRequest): Observable<BulkReviewResponse> {
    return this.api.bulkReviewRequests(review);
  }

  /** Revoke agent ownership (admin only) */
  revokeOwnership(revoke: RevokeOwnershipRequest): Observable<RevokeOwnershipResponse> {
    return this.api.revokeOwnership(revoke);
  }
}