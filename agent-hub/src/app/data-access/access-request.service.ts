import { Injectable, signal } from '@angular/core';
import { AccessRequest, AccessRequestForm } from '../../model';

@Injectable({
    providedIn: 'root'
})
export class AccessRequestService {
    private _requests = signal<AccessRequest[]>([]);

    // Mock current user - in real app this would come from auth service
    private readonly currentUser = {
        id: 'user-123',
        name: 'Alice'
    };

    constructor() {
        // Load mock data
        this.loadMockData();
    }

    private loadMockData() {
        const mockRequests: AccessRequest[] = [
            {
                id: 'req-1',
                userId: this.currentUser.id,
                userName: this.currentUser.name,
                toolName: 'Docker Agent',
                toolId: 'docker-agent',
                accessLevel: 'Admin',
                justification: 'Need to manage containers for development purposes',
                status: 'Pending',
                requestedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
                updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
                duration: 'Permanent',
                category: 'DevOps',
                description: 'Restart containers, check status, manage images'
            },
            {
                id: 'req-2',
                userId: this.currentUser.id,
                userName: this.currentUser.name,
                toolName: 'Cloud Agent',
                toolId: 'cloud-agent',
                accessLevel: 'Basic',
                justification: 'Working on AWS infrastructure project',
                status: 'Approved',
                requestedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
                updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
                duration: 'Temporary',
                reviewedBy: 'Admin',
                reviewedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
                category: 'Cloud',
                description: 'Manage cloud resources in AWS, Azure etc.'
            },
            {
                id: 'req-3',
                userId: this.currentUser.id,
                userName: this.currentUser.name,
                toolName: 'DB Agent',
                toolId: 'db-agent',
                accessLevel: 'Basic',
                justification: 'Need database access for analytics',
                status: 'Denied',
                requestedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
                updatedAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
                duration: 'Permanent',
                reason: 'Insufficient access level for requested operations',
                reviewedBy: 'Security Team',
                reviewedAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
                category: 'Database',
                description: 'Access and query SQL databases'
            },
            {
                id: 'req-4',
                userId: this.currentUser.id,
                userName: this.currentUser.name,
                toolName: 'CI/CD Agent',
                toolId: 'cicd-agent',
                accessLevel: 'Advanced',
                justification: 'Setting up deployment pipelines',
                status: 'Under Review',
                requestedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
                updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
                duration: 'Permanent',
                category: 'DevOps',
                description: 'Administer your CI/CD pipelines'
            }
        ];

        this._requests.set(mockRequests);
    }

    getRequests() {
        return this._requests.asReadonly();
    }

    getUserRequests(userId?: string) {
        const targetUserId = userId || this.currentUser.id;
        return this._requests().filter(req => req.userId === targetUserId);
    }

    async submitAccessRequest(requestForm: AccessRequestForm): Promise<AccessRequest> {
        const newRequest: AccessRequest = {
            id: this.generateId(),
            userId: this.currentUser.id,
            userName: this.currentUser.name,
            ...requestForm,
            status: 'Pending',
            requestedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 800));

        const currentRequests = this._requests();
        this._requests.set([newRequest, ...currentRequests]);

        return newRequest;
    }

    async updateRequestStatus(requestId: string, status: AccessRequest['status'], reason?: string): Promise<void> {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 500));

        const currentRequests = this._requests();
        const updatedRequests = currentRequests.map(req => {
            if (req.id === requestId) {
                return {
                    ...req,
                    status,
                    reason,
                    updatedAt: new Date().toISOString(),
                    reviewedAt: new Date().toISOString(),
                    reviewedBy: 'System Admin'
                };
            }
            return req;
        });

        this._requests.set(updatedRequests);
    }

    getRequestById(id: string): AccessRequest | undefined {
        return this._requests().find(req => req.id === id);
    }

    getRequestsByStatus(status: AccessRequest['status']): AccessRequest[] {
        return this._requests().filter(req => req.status === status);
    }

    private generateId(): string {
        return 'req-' + Math.random().toString(36).substr(2, 9);
    }
}
