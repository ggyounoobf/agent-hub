import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../services/admin.service';

interface HealthMetric {
    status: 'healthy' | 'warning' | 'unhealthy';
    responseTime?: string;
    uptime?: string;
    connections?: string;
    size?: string;
    activeAgents?: number;
    totalTools?: number;
    used?: number;
    available?: number;
}

interface SystemLog {
    id: string;
    timestamp: Date;
    level: 'info' | 'warn' | 'error';
    message: string;
    details?: string;
}

@Component({
    selector: 'app-admin-system',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-system.component.html',
    styleUrl: './admin-system.component.scss'
})
export class AdminSystemComponent implements OnInit {
    apiHealth = signal<HealthMetric>({ status: 'healthy', responseTime: '45', uptime: '5d 12h' });
    dbHealth = signal<HealthMetric>({ status: 'healthy', connections: '12/50', size: '1.2GB' });
    mcpHealth = signal<HealthMetric>({ status: 'healthy', activeAgents: 4, totalTools: 25 });
    storageHealth = signal<HealthMetric>({ status: 'warning', used: 78, available: 22 });

    systemLogs = signal<SystemLog[]>([]);
    isRefreshing = signal(false);
    isLoadingLogs = signal(true);
    lastUpdate = signal(new Date());
    logLevel = '';

    filteredLogs = computed(() => {
        let filtered = this.systemLogs();

        if (this.logLevel) {
            filtered = filtered.filter(log => log.level === this.logLevel);
        }

        return filtered.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    });

    overallHealth = computed(() => {
        const metrics = [
            this.apiHealth(),
            this.dbHealth(),
            this.mcpHealth(),
            this.storageHealth()
        ];

        if (metrics.some(m => m.status === 'unhealthy')) return 'unhealthy';
        if (metrics.some(m => m.status === 'warning')) return 'warning';
        return 'healthy';
    });

    constructor(private adminService: AdminService) { }

    ngOnInit() {
        this.loadSystemHealth();
        this.loadSystemLogs();
    }

    async loadSystemHealth() {
        try {
            // Load actual health data from API
            const health = await this.adminService.getSystemHealth();
            this.lastUpdate.set(new Date());

            // Update API health based on actual response
            this.apiHealth.set({
                status: health.status === 'ok' ? 'healthy' : 'unhealthy',
                responseTime: '45',
                uptime: '5d 12h'
            });

            // Load MCP agents data
            const agents = await this.adminService.getAgents();
            const totalTools = agents.reduce((sum, agent) => sum + agent.toolCount, 0);

            this.mcpHealth.set({
                status: agents.length > 0 ? 'healthy' : 'warning',
                activeAgents: agents.length,
                totalTools
            });

        } catch (error) {
            console.error('Failed to load system health:', error);
            this.apiHealth.set({ status: 'unhealthy', responseTime: 'N/A', uptime: 'N/A' });
        }
    }

    async loadSystemLogs() {
        try {
            this.isLoadingLogs.set(true);

            // Mock system logs - in real implementation, this would come from actual log files
            const mockLogs: SystemLog[] = [
                {
                    id: '1',
                    timestamp: new Date(Date.now() - 300000),
                    level: 'info',
                    message: 'System health check completed successfully',
                    details: 'All services operational'
                },
                {
                    id: '2',
                    timestamp: new Date(Date.now() - 600000),
                    level: 'warn',
                    message: 'Storage usage above 75%',
                    details: 'Consider cleaning up old files or expanding storage'
                },
                {
                    id: '3',
                    timestamp: new Date(Date.now() - 900000),
                    level: 'info',
                    message: 'New user registered',
                    details: 'User: jane@example.com'
                },
                {
                    id: '4',
                    timestamp: new Date(Date.now() - 1200000),
                    level: 'error',
                    message: 'Failed to connect to MCP agent',
                    details: 'Agent: pdf_agent, Error: Connection timeout'
                },
                {
                    id: '5',
                    timestamp: new Date(Date.now() - 1500000),
                    level: 'info',
                    message: 'Database backup completed',
                    details: 'Backup size: 1.2GB'
                }
            ];

            this.systemLogs.set(mockLogs);
        } catch (error) {
            console.error('Failed to load system logs:', error);
        } finally {
            this.isLoadingLogs.set(false);
        }
    }

    async refreshAll() {
        try {
            this.isRefreshing.set(true);
            await Promise.all([
                this.loadSystemHealth(),
                this.loadSystemLogs()
            ]);
        } finally {
            this.isRefreshing.set(false);
        }
    }

    filterLogs() {
        // Filtering is handled by the computed signal
    }

    clearLogs() {
        if (confirm('Are you sure you want to clear all system logs? This action cannot be undone.')) {
            this.systemLogs.set([]);
        }
    }

    getOverallHealthClass(): string {
        return this.overallHealth();
    }

    getOverallHealthText(): string {
        switch (this.overallHealth()) {
            case 'healthy': return 'All Systems Operational';
            case 'warning': return 'Some Issues Detected';
            case 'unhealthy': return 'Critical Issues Found';
            default: return 'Status Unknown';
        }
    }

    getHealthClass(status: string): string {
        return status;
    }

    getHealthText(status: string): string {
        switch (status) {
            case 'healthy': return 'Healthy';
            case 'warning': return 'Warning';
            case 'unhealthy': return 'Unhealthy';
            default: return 'Unknown';
        }
    }

    getLogClass(level: string): string {
        return level;
    }

    formatTime(timestamp: Date | string): string {
        return new Date(timestamp).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}
