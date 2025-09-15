import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { Observable } from 'rxjs';

export interface Tool {
  id: string;
  name: string;
}

export interface Agent {
  id: string;
  name: string;
  tools?: Tool[];
  description?: string;
}

export interface OwnedAgent {
  id: string;
  name: string;
}

export interface AgentRequestResponse {
  status: string;
  request_id?: string;
  message?: string;
}

export interface AgentRequest {
  id: string;
  agent_id: string;
  agent_name: string;
  status: 'pending' | 'approved' | 'rejected';
  justification?: string;
  review_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface PendingRequest {
  id: string;
  user_id: string;
  agent_id: string;
  agent_name: string;
  status: 'pending';
  created_at: string;
}

export interface ReviewRequest {
  action: 'approve' | 'reject';
  reason?: string;
}

export interface ReviewResponse {
  status: string;
  message: string;
  request_id: string;
  action: string;
}

export interface BulkReviewRequest {
  request_ids: string[];
  action: 'approve' | 'reject';
  reason?: string;
}

export interface BulkReviewResponse {
  status: string;
  message: string;
  results: {
    request_id: string;
    result: ReviewResponse;
  }[];
}

export interface RevokeOwnershipRequest {
  user_id: string;
  agent_id: string;
  reason?: string;
}

export interface RevokeOwnershipResponse {
  status: string;
  message: string;
  user_id: string;
  agent_id: string;
}

export interface UserAgentStats {
  user_id: string;
  owned_agents: number;
  pending_requests: number;
  approved_requests: number;
  rejected_requests: number;
  total_requests: number;
}

@Injectable({ providedIn: 'root' })
export class MarketplaceApi {
  private readonly http = inject(HttpClient);
  private readonly API_BASE = `${environment.apiUrl}/marketplace`;

  /**
   * Fetch all available agents (public endpoint)
   */
  getAgents(): Observable<Agent[]> {
    return this.http.get<Agent[]>(`${this.API_BASE}/agents`);
  }

  /**
   * Fetch agents owned by the current user (requires authentication)
   */
  getOwnedAgents(): Observable<OwnedAgent[]> {
    return this.http.get<OwnedAgent[]>(`${this.API_BASE}/owned-agents`, {
      withCredentials: true
    });
  }

  /**
   * Request ownership of an agent (requires authentication)
   */
  requestAgent(agentId: string): Observable<AgentRequestResponse> {
    return this.http.post<AgentRequestResponse>(`${this.API_BASE}/request-agent/${agentId}`, {}, {
      withCredentials: true
    });
  }

  /**
   * Get agent details by ID (requires authentication - user must own agent or be admin)
   */
  getAgentById(agentId: string): Observable<Agent> {
    return this.http.get<Agent>(`${this.API_BASE}/agent/${agentId}`, {
      withCredentials: true
    });
  }

  /**
   * Get agent requests made by the current user (requires authentication)
   */
  getMyRequests(): Observable<AgentRequest[]> {
    return this.http.get<AgentRequest[]>(`${this.API_BASE}/my-requests`, {
      withCredentials: true
    });
  }

  /**
   * Get user agent stats (requires authentication)
   */
  getUserAgentStats(): Observable<UserAgentStats> {
    return this.http.get<UserAgentStats>(`${this.API_BASE}/user-agent-stats`, {
      withCredentials: true
    });
  }

  /**
   * Get pending requests (admin only)
   */
  getPendingRequests(): Observable<PendingRequest[]> {
    return this.http.get<PendingRequest[]>(`${this.API_BASE}/pending-requests`, {
      withCredentials: true
    });
  }

  /**
   * Review agent request (admin only)
   */
  reviewRequest(requestId: string, review: ReviewRequest): Observable<ReviewResponse> {
    const formData = new FormData();
    formData.append('action', review.action);
    if (review.reason) {
      formData.append('reason', review.reason);
    }
    return this.http.post<ReviewResponse>(`${this.API_BASE}/review-request/${requestId}`, formData, {
      withCredentials: true
    });
  }

  /**
   * Bulk review requests (admin only)
   */
  bulkReviewRequests(review: BulkReviewRequest): Observable<BulkReviewResponse> {
    const formData = new FormData();
    review.request_ids.forEach(id => formData.append('request_ids[]', id));
    formData.append('action', review.action);
    if (review.reason) {
      formData.append('reason', review.reason);
    }
    return this.http.post<BulkReviewResponse>(`${this.API_BASE}/bulk-review`, formData, {
      withCredentials: true
    });
  }

  /**
   * Revoke agent ownership (admin only)
   */
  revokeOwnership(revoke: RevokeOwnershipRequest): Observable<RevokeOwnershipResponse> {
    const formData = new FormData();
    formData.append('user_id', revoke.user_id);
    formData.append('agent_id', revoke.agent_id);
    if (revoke.reason) {
      formData.append('reason', revoke.reason);
    }
    return this.http.post<RevokeOwnershipResponse>(`${this.API_BASE}/revoke-ownership`, formData, {
      withCredentials: true
    });
  }
}
