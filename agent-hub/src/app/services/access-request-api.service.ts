import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { MarketplaceService } from '../services/marketplace.service';
import { AgentRequest, ReviewRequest } from '../api/marketplace-api.service';

@Injectable({
    providedIn: 'root'
})
export class AccessRequestApiService {
    private marketplaceService = inject(MarketplaceService);

    // Get all access requests for the current user
    getUserAccessRequests(): Observable<AgentRequest[]> {
        return this.marketplaceService.getMyRequests();
    }

    // Submit a new access request for an agent
    submitAccessRequest(agentId: string): Observable<any> {
        return this.marketplaceService.requestAgent(agentId);
    }

    // Get pending access requests (admin only)
    getPendingAccessRequests(): Observable<any[]> {
        return this.marketplaceService.getPendingRequests();
    }

    // Review an access request (admin only)
    reviewAccessRequest(requestId: string, review: ReviewRequest): Observable<any> {
        return this.marketplaceService.reviewRequest(requestId, review);
    }

    // Bulk review access requests (admin only)
    bulkReviewAccessRequests(requestIds: string[], action: 'approve' | 'reject', reason?: string): Observable<any> {
        return this.marketplaceService.bulkReviewRequests({
            request_ids: requestIds,
            action,
            reason
        });
    }
}