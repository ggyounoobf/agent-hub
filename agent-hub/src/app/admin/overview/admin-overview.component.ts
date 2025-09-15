import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, SystemStats } from '../services/admin.service';
import { AnalyticsService, AnalyticsOverview } from '../services/analytics.service';
import { AdminRequestManagementComponent } from './request-management.component';

interface ActivityItem {
    id: string;
    type: 'user' | 'chat' | 'agent' | 'system';
    description: string;
    timestamp: Date;
}

@Component({
    selector: 'app-admin-overview',
    standalone: true,
    imports: [CommonModule, AdminRequestManagementComponent],
    templateUrl: './admin-overview.component.html',
    styleUrl: './admin-overview.component.scss'
})
export class AdminOverviewComponent implements OnInit {
    // Existing signals
    totalUsers = signal(0);
    totalChats = signal(0);
    totalAgents = signal(0);
    systemHealth = signal('Healthy');
    recentActivity = signal<ActivityItem[]>([]);
    
    // New analytics signals
    analyticsOverview = signal<AnalyticsOverview | null>(null);
    querySuccessRate = signal<number>(0);
    recentUsers = signal<number>(0);
    recentQueries = signal<number>(0);
    totalFiles = signal<number>(0);
    isLoading = signal(true);
    hasError = signal(false);
    errorMessage = signal('');

    constructor(
        private adminService: AdminService,
        private analyticsService: AnalyticsService
    ) { }

    ngOnInit() {
        this.loadOverviewData();
        this.loadAnalyticsData();
    }

    async loadOverviewData() {
        try {
            // Load statistics
            const stats = await this.adminService.getSystemStats();
            this.totalUsers.set(stats.totalUsers);
            this.totalChats.set(stats.totalChats);
            this.totalAgents.set(stats.totalAgents);
            this.systemHealth.set(stats.systemHealth);

            // Load recent activity
            const activity = await this.adminService.getRecentActivity();
            this.recentActivity.set(activity);
        } catch (error) {
            console.error('Failed to load overview data:', error);
            // Set fallback values to ensure data is displayed
            this.totalUsers.set(this.totalUsers() || 0);
            this.totalChats.set(this.totalChats() || 0);
            this.totalAgents.set(this.totalAgents() || 0);
        }
    }

    async loadAnalyticsData(fallbackToOverview: boolean = true) {
        try {
            this.isLoading.set(true);
            this.hasError.set(false);
            this.errorMessage.set('');
            
            const overview = await this.analyticsService.getOverview();
            this.analyticsOverview.set(overview);
            
            // Update existing signals with analytics data
            this.totalUsers.set(overview.total_users);
            this.totalChats.set(overview.total_chats);
            this.totalAgents.set(overview.total_agents);
            this.totalFiles.set(overview.total_files);
            this.querySuccessRate.set(overview.query_success_rate);
            this.recentUsers.set(overview.recent_users);
            this.recentQueries.set(overview.recent_queries);
        } catch (error) {
            console.error('Failed to load analytics data:', error);
            this.hasError.set(true);
            this.errorMessage.set('Failed to load analytics data. Showing latest available data.');
            
            // Fallback to overview data if analytics fails
            if (fallbackToOverview) {
                await this.loadOverviewData();
            }
        } finally {
            this.isLoading.set(false);
        }
    }

    getActivityIcon(type: string): string {
        switch (type) {
            case 'user': return 'icon-user-plus';
            case 'chat': return 'icon-message-circle';
            case 'agent': return 'icon-cpu';
            case 'system': return 'icon-activity';
            default: return 'icon-info';
        }
    }

    getActivityIconClass(type: string): string {
        switch (type) {
            case 'user': return 'user-activity';
            case 'chat': return 'chat-activity';
            case 'agent': return 'agent-activity';
            case 'system': return 'system-activity';
            default: return '';
        }
    }

    formatTime(timestamp: Date): string {
        const now = new Date();
        const diff = now.getTime() - timestamp.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return 'Just now';
    }
}
