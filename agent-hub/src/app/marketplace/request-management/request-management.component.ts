import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MarketplaceService } from '../../services/marketplace.service';
import { AgentRequest } from '../../api/marketplace-api.service';
import { ToastsService } from '@ngx-templates/shared/toasts';
import { firstValueFrom } from 'rxjs';

@Component({
    selector: 'acb-request-management',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './request-management.component.html',
    styleUrl: './request-management.component.scss',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RequestManagementComponent implements OnInit {
    private _marketplaceService = inject(MarketplaceService);
    private _toast = inject(ToastsService);

    searchQuery = signal<string>('');
    statusFilter = signal<string>('');
    sortBy = signal<'date' | 'tool' | 'status'>('date');
    sortOrder = signal<'asc' | 'desc'>('desc');
    expandedCards = signal<Set<string>>(new Set());
    requests = signal<AgentRequest[]>([]);
    loading = signal<boolean>(true);
    isAppealing = signal<Record<string, boolean>>({});

    // Get user's requests
    filteredRequests = computed(() => {
        const allRequests = this.requests();
        const query = this.searchQuery().toLowerCase();
        const status = this.statusFilter();

        let filtered = allRequests.filter(request => {
            const matchesSearch = !query ||
                request.agent_name.toLowerCase().includes(query) ||
                request.id.toLowerCase().includes(query);

            const matchesStatus = !status || request.status === status;

            return matchesSearch && matchesStatus;
        });

        // Sort requests
        const sortField = this.sortBy();
        const order = this.sortOrder();

        filtered.sort((a, b) => {
            let comparison = 0;

            switch (sortField) {
                case 'date':
                    comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                    break;
                case 'tool':
                    comparison = a.agent_name.localeCompare(b.agent_name);
                    break;
                case 'status':
                    comparison = a.status.localeCompare(b.status);
                    break;
            }

            return order === 'desc' ? -comparison : comparison;
        });

        return filtered;
    });

    statusCounts = computed(() => {
        const allRequests = this.requests();
        return {
            all: allRequests.length,
            pending: allRequests.filter(r => r.status === 'pending').length,
            approved: allRequests.filter(r => r.status === 'approved').length,
            rejected: allRequests.filter(r => r.status === 'rejected').length
        };
    });

    ngOnInit() {
        this.loadRequests();
    }

    async loadRequests() {
        try {
            this.loading.set(true);
            this._marketplaceService.getMyRequests().subscribe({
                next: (requests) => {
                    this.requests.set(requests || []);
                    this.loading.set(false);
                },
                error: (error) => {
                    console.error('Failed to load requests:', error);
                    this._toast.create('Failed to load requests.');
                    this.loading.set(false);
                }
            });
        } catch (error) {
            console.error('Error loading requests:', error);
            this._toast.create('Failed to load requests.');
            this.loading.set(false);
        }
    }

    onSearchInput(event: Event) {
        const target = event.target as HTMLInputElement;
        this.searchQuery.set(target.value);
    }

    onStatusFilterChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        this.statusFilter.set(target.value);
    }

    onSortChange(field: 'date' | 'tool' | 'status') {
        if (this.sortBy() === field) {
            // Toggle sort order if same field
            this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
        } else {
            this.sortBy.set(field);
            this.sortOrder.set('asc');
        }
    }

    clearFilters() {
        this.searchQuery.set('');
        this.statusFilter.set('');
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'pending': return 'status-pending';
            case 'approved': return 'status-approved';
            case 'rejected': return 'status-denied';
            default: return '';
        }
    }

    getStatusText(status: string): string {
        switch (status) {
            case 'pending': return 'Pending';
            case 'approved': return 'Approved';
            case 'rejected': return 'Rejected';
            default: return status;
        }
    }

    getRelativeTime(dateString: string): string {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;

        return date.toLocaleDateString();
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

    toggleExpand(requestId: string) {
        const expanded = new Set(this.expandedCards());
        if (expanded.has(requestId)) {
            expanded.delete(requestId);
        } else {
            expanded.add(requestId);
        }
        this.expandedCards.set(expanded);
    }

    isExpanded(requestId: string): boolean {
        return this.expandedCards().has(requestId);
    }

    canAppeal(request: AgentRequest): boolean {
        return request.status === 'rejected';
    }

    async appealRequest(requestId: string) {
        // Set appealing state for this request
        this.isAppealing.update(state => ({ ...state, [requestId]: true }));
        
        try {
            // Find the original request to get agent info
            const originalRequest = this.requests().find(r => r.id === requestId);
            if (!originalRequest) {
                throw new Error('Request not found');
            }

            // Create a new request for the same agent
            const response = await firstValueFrom(this._marketplaceService.requestAgent(
                originalRequest.agent_id,
                originalRequest.justification
            ));

            if (response?.status === 'success') {
                this._toast.create('Re-request submitted successfully!');
                // Reload requests to show the new pending request
                await this.loadRequests();
            } else {
                throw new Error(response?.message || 'Failed to submit re-request');
            }
        } catch (error) {
            console.error('Failed to appeal request:', error);
            this._toast.create('Failed to submit re-request. Please try again.');
        } finally {
            // Remove appealing state
            this.isAppealing.update(state => {
                const newState = { ...state };
                delete newState[requestId];
                return newState;
            });
        }
    }
}
