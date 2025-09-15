import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AnalyticsService, AnalyticsOverview, UsageStatistics, AgentPerformance, UserActivity } from '../services/analytics.service';
import { AnalyticsIconsComponent } from './icons.component';

@Component({
    selector: 'app-analytics-dashboard',
    standalone: true,
    imports: [CommonModule, AnalyticsIconsComponent],
    templateUrl: './analytics-dashboard.component.html',
    styleUrl: './analytics-dashboard.component.scss'
})
export class AnalyticsDashboardComponent implements OnInit {
    // Data signals
    analyticsOverview = signal<AnalyticsOverview | null>(null);
    usageStats = signal<UsageStatistics | null>(null);
    agentPerformance = signal<AgentPerformance | null>(null);
    userActivity = signal<UserActivity | null>(null);
    
    // UI state
    isLoading = signal(true);
    activeTab = signal('overview');
    timeRange = signal(30); // days

    constructor(private analyticsService: AnalyticsService) { }

    ngOnInit() {
        this.loadAllAnalyticsData();
    }

    private async loadAllAnalyticsData() {
        try {
            this.isLoading.set(true);
            
            // Load all analytics data in parallel
            const [overview, usage, performance, activity] = await Promise.all([
                this.analyticsService.getOverview(this.timeRange()),
                this.analyticsService.getUsageStatistics(this.timeRange()),
                this.analyticsService.getAgentPerformance(this.timeRange()),
                this.analyticsService.getUserActivity(this.timeRange())
            ]);
            
            // Sort data for better visualization
            if (usage?.agent_usage) {
                usage.agent_usage.sort((a, b) => b.usage_count - a.usage_count);
            }
            
            if (activity?.user_engagement) {
                activity.user_engagement.sort((a, b) => b.query_count - a.query_count);
            }
            
            this.analyticsOverview.set(overview);
            this.usageStats.set(usage);
            this.agentPerformance.set(performance);
            this.userActivity.set(activity);
        } catch (error) {
            console.error('Failed to load analytics data:', error);
        } finally {
            this.isLoading.set(false);
        }
    }

    onTimeRangeChange(days: number) {
        this.timeRange.set(days);
        this.loadAllAnalyticsData();
    }

    setActiveTab(tab: string) {
        this.activeTab.set(tab);
    }

    // Helper methods for data formatting
    formatDate(dateString: string): string {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    getAgentColor(agentName: string): string {
        const colors = [
            '#8b5cf6', // purple
            '#10b981', // green
            '#f59e0b', // amber
            '#ef4444', // red
            '#3b82f6', // blue
            '#ec4899'  // pink
        ];
        
        // Simple hash function to get consistent color for each agent
        let hash = 0;
        for (let i = 0; i < agentName.length; i++) {
            hash = agentName.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        return colors[Math.abs(hash) % colors.length];
    }

    // Helper methods for charts
    getMaxValue(timeSeries: { date: string; value: number }[]): number {
        if (!timeSeries || timeSeries.length === 0) return 0;
        return Math.max(...timeSeries.map(item => item.value));
    }

    getMaxAgentUsage(): number {
        if (!this.usageStats() || !this.usageStats()!.agent_usage) return 0;
        const values = this.usageStats()!.agent_usage.map(agent => agent.usage_count);
        return values.length > 0 ? Math.max(...values) : 0;
    }

    getMaxUserEngagement(): number {
        if (!this.userActivity() || !this.userActivity()!.user_engagement) return 0;
        const values = this.userActivity()!.user_engagement.map(user => user.query_count);
        return values.length > 0 ? Math.max(...values) : 0;
    }

    // Format large numbers for better readability
    formatNumber(num: number): string {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
}