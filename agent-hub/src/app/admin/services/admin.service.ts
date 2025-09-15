import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
// Correct relative path to environments (folder is at src/environments)
import { environment } from '../../../environments/environment';
import { AuthService } from '../../services/auth.service';
import { MarketplaceService } from '../../services/marketplace.service';
import { PendingRequest, ReviewRequest } from '../../api/marketplace-api.service';

export interface SystemStats {
    totalUsers: number;
    totalChats: number;
    totalAgents: number;
    systemHealth: string;
}

export interface ActivityItem {
    id: string;
    type: 'user' | 'chat' | 'agent' | 'system';
    description: string;
    timestamp: Date;
}

export interface ActivityLog {
    id: string;
    type: 'user' | 'chat' | 'agent' | 'system';
    description: string;
    timestamp: string; // ISO timestamp
    metadata: Record<string, any>;
}

export interface ActivitySearchRequest {
    query?: string;
    types?: ('USER' | 'CHAT' | 'AGENT' | 'SYSTEM')[];
    start_time?: string;
    end_time?: string;
    user_id?: string;
    page?: number;
    page_size?: number;
}

export interface ActivitySearchResponse {
    events: ActivityLog[];
    total_count: number;
    page: number;
    page_size: number;
}

export interface Chat {
    id: string;
    userId: string;
    userEmail: string;
    userName: string;
    title: string;
    messageCount: number;
    createdAt: string;
    updatedAt: string;
}

export interface ChatQuery {
    id: string;
    chat_id: string;
    message: string;
    response: string;
    agent_used?: string;
    status?: string;
    created_at: string;
}

export interface Agent {
    name: string;
    tools: { id: string; name: string }[];
    status: 'healthy' | 'unhealthy' | 'unknown';
    toolCount: number;
}

export interface AgentsResponse {
    available_agents: { 
        [key: string]: {
            description: string;
            tools: string[];
        }
    };
}

export interface HealthResponse {
    status: string;
    timestamp: string;
    version?: string;
}

@Injectable({
    providedIn: 'root'
})
export class AdminService {
    private http = inject(HttpClient);
    private apiUrl = environment.apiUrl;
    private auth = inject(AuthService);
    private marketplaceService = inject(MarketplaceService);

    async getSystemStats(): Promise<SystemStats> {
        try {
            // Get stats from admin endpoint
            const statsResponse = await firstValueFrom(
                this.http.get<any>(`${this.apiUrl}/admin/stats`)
            );

            // Get agents from agents endpoint
            const agentsResponse = await firstValueFrom(
                this.http.get<AgentsResponse>(`${this.apiUrl}/agents`)
            );

            return {
                totalUsers: statsResponse.totalUsers,
                totalChats: statsResponse.totalChats,
                totalAgents: Object.keys(agentsResponse.available_agents).length,
                systemHealth: statsResponse.systemHealth
            };
        } catch (error) {
            console.error('Failed to get system stats:', error, 'token present:', !!this.auth.getAccessToken());
            return {
                totalUsers: 0,
                totalChats: 0,
                totalAgents: 0,
                systemHealth: 'Unknown'
            };
        }
    }

    async getRecentActivity(): Promise<ActivityItem[]> {
        // Mock data for now - in real implementation, this would come from audit logs
        return [
            {
                id: '1',
                type: 'user',
                description: 'New user registered: john.doe@example.com',
                timestamp: new Date(Date.now() - 300000) // 5 minutes ago
            },
            {
                id: '2',
                type: 'chat',
                description: 'New chat session started by user',
                timestamp: new Date(Date.now() - 600000) // 10 minutes ago
            },
            {
                id: '3',
                type: 'agent',
                description: 'PDF agent processed document',
                timestamp: new Date(Date.now() - 900000) // 15 minutes ago
            }
        ];
    }

    async getAllChats(): Promise<Chat[]> {
        try {
            const raw = await firstValueFrom(
                this.http.get<any[]>(`${this.apiUrl}/admin/chats`)
            );
            return raw.map(r => ({
                id: r.id,
                userId: r.userId,
                userEmail: r.userEmail,
                userName: r.userName,
                title: r.title,
                messageCount: r.messageCount,
                createdAt: r.createdAt,
                updatedAt: r.updatedAt
            }));
        } catch (error) {
            console.error('Failed to get chats:', error, 'token present:', !!this.auth.getAccessToken());
            return [];
        }
    }

    async getChatQueries(chatId: string): Promise<ChatQuery[]> {
        try {
            return await firstValueFrom(
                this.http.get<ChatQuery[]>(`${this.apiUrl}/admin/chats/${chatId}/queries`)
            );
        } catch (error) {
            console.error('Failed to get chat queries:', error);
            return [];
        }
    }

    async deleteChat(chatId: string): Promise<boolean> {
        try {
            await firstValueFrom(
                this.http.delete(`${this.apiUrl}/admin/chats/${chatId}`)
            );
            return true;
        } catch (error) {
            console.error('Failed to delete chat:', error);
            return false;
        }
    }

    async getUsers(role?: string): Promise<any[]> {
        try {
            const url = role ? `${this.apiUrl}/auth/admin/users?role=${role}` : `${this.apiUrl}/auth/admin/users`;
            return await firstValueFrom(this.http.get<any[]>(url));
        } catch (error) {
            console.error('Failed to load users:', error, 'token present:', !!this.auth.getAccessToken());
            return [];
        }
    }

    async getUser(userId: string): Promise<any | null> {
        try {
            return await firstValueFrom(this.http.get<any>(`${this.apiUrl}/auth/admin/users/${userId}`));
        } catch (error) {
            console.error('Failed to load user:', error);
            return null;
        }
    }

    async createUser(userData: any): Promise<any | null> {
        try {
            return await firstValueFrom(this.http.post<any>(`${this.apiUrl}/auth/admin/users`, userData));
        } catch (error) {
            console.error('Failed to create user:', error);
            throw error;
        }
    }

    async updateUser(userId: string, userData: any): Promise<any | null> {
        try {
            return await firstValueFrom(this.http.put<any>(`${this.apiUrl}/auth/admin/users/${userId}`, userData));
        } catch (error) {
            console.error('Failed to update user:', error);
            throw error;
        }
    }

    async deleteUser(userId: string): Promise<boolean> {
        try {
            await firstValueFrom(this.http.delete(`${this.apiUrl}/auth/admin/users/${userId}`));
            return true;
        } catch (error) {
            console.error('Failed to delete user:', error);
            return false;
        }
    }

    async updateUserRole(userId: string, role: string): Promise<boolean> {
        try {
            await firstValueFrom(this.http.put(`${this.apiUrl}/auth/admin/users/${userId}/role?new_role=${role}`, {}));
            return true;
        } catch (error) {
            console.error('Failed to update user role:', error);
            return false;
        }
    }

    async getAgents(): Promise<Agent[]> {
        try {
            const [agentsResponse, healthResponse] = await Promise.allSettled([
                firstValueFrom(this.http.get<AgentsResponse>(`${this.apiUrl}/agents`)),
                firstValueFrom(this.http.get<HealthResponse>(`${this.apiUrl}/healthz`))
            ]);

            const agents: Agent[] = [];

            if (agentsResponse.status === 'fulfilled') {
                const agentsData = agentsResponse.value.available_agents;

                for (const [agentName, agentDetails] of Object.entries(agentsData)) {
                    // Ensure tools is an array before mapping
                    const toolsArray = Array.isArray(agentDetails.tools) ? agentDetails.tools : [];
                    
                    // Convert string array to Tool objects
                    const toolObjects = toolsArray.map((toolName, index) => ({
                        id: `${agentName}-${index}`,
                        name: toolName
                    }));
                    
                    agents.push({
                        name: agentName,
                        tools: toolObjects,
                        toolCount: toolsArray.length,
                        status: healthResponse.status === 'fulfilled' ? 'healthy' : 'unknown'
                    });
                }
            }

            return agents;
        } catch (error) {
            console.error('Failed to get agents:', error);
            return [];
        }
    }

    async getSystemHealth(): Promise<HealthResponse> {
        try {
            return await firstValueFrom(
                this.http.get<HealthResponse>(`${this.apiUrl}/healthz`)
            );
        } catch (error) {
            console.error('Failed to get system health:', error);
            return {
                status: 'unhealthy',
                timestamp: new Date().toISOString()
            };
        }
    }

    // New methods for handling agent access requests
    async getPendingAgentRequests(): Promise<PendingRequest[]> {
        try {
            return await firstValueFrom(this.marketplaceService.getPendingRequests());
        } catch (error) {
            console.error('Failed to get pending agent requests:', error);
            return [];
        }
    }

    async reviewAgentRequest(requestId: string, review: ReviewRequest): Promise<any> {
        try {
            return await firstValueFrom(this.marketplaceService.reviewRequest(requestId, review));
        } catch (error) {
            console.error('Failed to review agent request:', error);
            throw error;
        }
    }

    async bulkReviewAgentRequests(requestIds: string[], action: 'approve' | 'reject', reason?: string): Promise<any> {
        try {
            return await firstValueFrom(this.marketplaceService.bulkReviewRequests({
                request_ids: requestIds,
                action,
                reason
            }));
        } catch (error) {
            console.error('Failed to bulk review agent requests:', error);
            throw error;
        }
    }

    // Activity logging methods
    private getAuthHeaders() {
        const token = this.auth.getAccessToken();
        return {
            Authorization: `Bearer ${token}`
        };
    }

    /**
     * Get recent activity logs
     * @param limit Number of events to return (default: 50, max: 100)
     * @param types Filter by event types
     * @param userId Filter by specific user ID
     * @param startTime Start of time range (ISO timestamp)
     * @param endTime End of time range (ISO timestamp)
     */
    async getRecentActivityLogs(
        limit: number = 50,
        types?: ('user' | 'chat' | 'agent' | 'system')[],
        userId?: string,
        startTime?: string,
        endTime?: string
    ): Promise<ActivityLog[]> {
        try {
            const params = new URLSearchParams();
            params.set('limit', limit.toString());
            
            if (types && types.length > 0) {
                params.set('types', types.join(','));
            }
            
            if (userId) {
                params.set('user_id', userId);
            }
            
            if (startTime) {
                params.set('start_time', startTime);
            }
            
            if (endTime) {
                params.set('end_time', endTime);
            }
            
            const url = `${this.apiUrl}/admin/activity/recent?${params.toString()}`;
            const logs = await firstValueFrom(
                this.http.get<ActivityLog[]>(url, { headers: this.getAuthHeaders() })
            );
            
            return logs;
        } catch (error) {
            console.error('Failed to get recent activity logs:', error);
            return [];
        }
    }

    /**
     * Get activity logs within a specific time range
     * @param startTime Start of time range (required, ISO timestamp)
     * @param endTime End of time range (required, ISO timestamp)
     * @param types Filter by event types
     * @param userId Filter by specific user ID
     */
    async getActivityLogsByRange(
        startTime: string,
        endTime: string,
        types?: ('user' | 'chat' | 'agent' | 'system')[],
        userId?: string
    ): Promise<ActivityLog[]> {
        try {
            const params = new URLSearchParams();
            params.set('start_time', startTime);
            params.set('end_time', endTime);
            
            if (types && types.length > 0) {
                params.set('types', types.join(','));
            }
            
            if (userId) {
                params.set('user_id', userId);
            }
            
            const url = `${this.apiUrl}/admin/activity/range?${params.toString()}`;
            const logs = await firstValueFrom(
                this.http.get<ActivityLog[]>(url, { headers: this.getAuthHeaders() })
            );
            
            return logs;
        } catch (error) {
            console.error('Failed to get activity logs by range:', error);
            return [];
        }
    }

    /**
     * Search activity logs with advanced filtering and pagination
     * @param searchRequest Search parameters
     */
    async searchActivityLogs(searchRequest: ActivitySearchRequest): Promise<ActivitySearchResponse> {
        try {
            const response = await firstValueFrom(
                this.http.post<ActivitySearchResponse>(
                    `${this.apiUrl}/admin/activity/search`,
                    searchRequest,
                    { headers: this.getAuthHeaders() }
                )
            );
            
            return response;
        } catch (error) {
            console.error('Failed to search activity logs:', error);
            return {
                events: [],
                total_count: 0,
                page: 1,
                page_size: 50
            };
        }
    }
}
