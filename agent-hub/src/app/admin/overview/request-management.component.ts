import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../services/admin.service';
import { PendingRequest, ReviewRequest } from '../../api/marketplace-api.service';
import { ToastsService } from '@ngx-templates/shared/toasts';

@Component({
  selector: 'app-admin-request-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './request-management.component.html',
  styleUrl: './request-management.component.scss'
})
export class AdminRequestManagementComponent implements OnInit {
  private adminService = inject(AdminService);
  private toastService = inject(ToastsService);

  pendingRequests = signal<PendingRequest[]>([]);
  filteredRequests = signal<PendingRequest[]>([]);
  searchQuery = signal<string>('');
  selectedRequests = signal<Set<string>>(new Set());
  isLoading = signal<boolean>(true);
  isProcessing = signal<boolean>(false);
  rejectionReasons = signal<Record<string, string>>({});
  bulkRejectionReason = signal<string>('');

  // Computed properties
  filteredAndSearchedRequests = computed(() => {
    const query = this.searchQuery().toLowerCase();
    return this.pendingRequests().filter(request => 
      request.agent_name.toLowerCase().includes(query) ||
      request.id.toLowerCase().includes(query)
    );
  });

  selectedCount = computed(() => this.selectedRequests().size);

  ngOnInit() {
    this.loadPendingRequests();
  }

  async loadPendingRequests() {
    try {
      this.isLoading.set(true);
      const requests = await this.adminService.getPendingAgentRequests();
      this.pendingRequests.set(requests || []);
      this.filteredRequests.set(requests || []);
    } catch (error) {
      console.error('Failed to load pending requests:', error);
      this.toastService.create('Failed to load pending requests');
    } finally {
      this.isLoading.set(false);
    }
  }

  onSearchInput(event: Event) {
    const target = event.target as HTMLInputElement;
    this.searchQuery.set(target.value);
  }

  clearSearch() {
    this.searchQuery.set('');
  }

  toggleRequestSelection(requestId: string) {
    const selected = new Set(this.selectedRequests());
    if (selected.has(requestId)) {
      selected.delete(requestId);
      // Also clear any rejection reason for this request
      this.rejectionReasons.update(reasons => {
        const newReasons = { ...reasons };
        delete newReasons[requestId];
        return newReasons;
      });
    } else {
      selected.add(requestId);
    }
    this.selectedRequests.set(selected);
  }

  selectAll() {
    const allIds = this.filteredAndSearchedRequests().map(req => req.id);
    this.selectedRequests.set(new Set(allIds));
  }

  clearSelection() {
    this.selectedRequests.set(new Set());
    // Clear all rejection reasons
    this.rejectionReasons.set({});
    this.bulkRejectionReason.set('');
  }

  setRejectionReason(requestId: string, reason: string) {
    this.rejectionReasons.update(reasons => ({
      ...reasons,
      [requestId]: reason
    }));
  }

  getRejectionReason(requestId: string): string {
    return this.rejectionReasons()[requestId] || '';
  }

  onBulkRejectionReasonChange(reason: string) {
    this.bulkRejectionReason.set(reason);
    // Also update individual rejection reasons for selected requests
    const selectedIds = Array.from(this.selectedRequests());
    const updatedReasons: Record<string, string> = { ...this.rejectionReasons() };
    selectedIds.forEach(id => {
      updatedReasons[id] = reason;
    });
    this.rejectionReasons.set(updatedReasons);
  }

  getBulkRejectionReason(): string {
    return this.bulkRejectionReason();
  }

  async approveRequest(requestId: string) {
    try {
      this.isProcessing.set(true);
      const review: ReviewRequest = { action: 'approve' };
      const response = await this.adminService.reviewAgentRequest(requestId, review);
      
      if (response?.status === 'success') {
        this.toastService.create(`Request approved successfully`);
        // Remove the approved request from the list
        const updatedRequests = this.pendingRequests().filter(req => req.id !== requestId);
        this.pendingRequests.set(updatedRequests);
      } else {
        this.toastService.create(`Failed to approve request: ${response?.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to approve request:', error);
      this.toastService.create('Failed to approve request');
    } finally {
      this.isProcessing.set(false);
    }
  }

  async rejectRequest(requestId: string) {
    try {
      this.isProcessing.set(true);
      const reason = this.getRejectionReason(requestId);
      const review: ReviewRequest = { action: 'reject', reason };
      const response = await this.adminService.reviewAgentRequest(requestId, review);
      
      if (response?.status === 'success') {
        this.toastService.create(`Request rejected successfully`);
        // Remove the rejected request from the list
        const updatedRequests = this.pendingRequests().filter(req => req.id !== requestId);
        this.pendingRequests.set(updatedRequests);
        // Clear the rejection reason
        this.rejectionReasons.update(reasons => {
          const newReasons = { ...reasons };
          delete newReasons[requestId];
          return newReasons;
        });
      } else {
        this.toastService.create(`Failed to reject request: ${response?.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to reject request:', error);
      this.toastService.create('Failed to reject request');
    } finally {
      this.isProcessing.set(false);
    }
  }

  async bulkApprove() {
    if (this.selectedRequests().size === 0) return;
    
    try {
      this.isProcessing.set(true);
      const requestIds = Array.from(this.selectedRequests());
      const response = await this.adminService.bulkReviewAgentRequests(requestIds, 'approve');
      
      if (response?.status === 'success') {
        this.toastService.create(`Bulk approval completed successfully`);
        // Remove approved requests from the list
        const updatedRequests = this.pendingRequests().filter(req => !requestIds.includes(req.id));
        this.pendingRequests.set(updatedRequests);
        this.selectedRequests.set(new Set());
        this.bulkRejectionReason.set('');
      } else {
        this.toastService.create(`Failed to complete bulk approval: ${response?.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to bulk approve requests:', error);
      this.toastService.create('Failed to complete bulk approval');
    } finally {
      this.isProcessing.set(false);
    }
  }

  async bulkReject() {
    if (this.selectedRequests().size === 0) return;
    
    try {
      this.isProcessing.set(true);
      const requestIds = Array.from(this.selectedRequests());
      // Get the bulk rejection reason
      const reason = this.bulkRejectionReason() || '';
      const response = await this.adminService.bulkReviewAgentRequests(requestIds, 'reject', reason);
      
      if (response?.status === 'success') {
        this.toastService.create(`Bulk rejection completed successfully`);
        // Remove rejected requests from the list
        const updatedRequests = this.pendingRequests().filter(req => !requestIds.includes(req.id));
        this.pendingRequests.set(updatedRequests);
        this.selectedRequests.set(new Set());
        // Clear all rejection reasons for these requests
        this.rejectionReasons.update(reasons => {
          const newReasons = { ...reasons };
          requestIds.forEach(id => delete newReasons[id]);
          return newReasons;
        });
        this.bulkRejectionReason.set('');
      } else {
        this.toastService.create(`Failed to complete bulk rejection: ${response?.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to bulk reject requests:', error);
      this.toastService.create('Failed to complete bulk rejection');
    } finally {
      this.isProcessing.set(false);
    }
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  }
}