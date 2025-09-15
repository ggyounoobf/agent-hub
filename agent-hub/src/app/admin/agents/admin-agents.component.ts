import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, Agent as AdminAgent, HealthResponse } from '../services/admin.service';
import { Tool } from '../../api/marketplace-api.service';

interface ToolCategory {
    name: string;
    count: number;
    icon: string;
}

@Component({
    selector: 'app-admin-agents',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './admin-agents.component.html',
    styleUrl: './admin-agents.component.scss'
})
export class AdminAgentsComponent implements OnInit {
    agents = signal<AdminAgent[]>([]);
    systemHealth = signal<HealthResponse>({ status: 'unknown', timestamp: new Date().toISOString() });
    isLoading = signal(true);
    isRefreshing = signal(false);
    expandedAgents = signal<Set<string>>(new Set());

    toolCategories = computed<ToolCategory[]>(() => {
        const categories = new Map<string, number>();

        this.agents().forEach(agent => {
            agent.tools.forEach(tool => {
                const category = this.getToolCategory(tool);
                categories.set(category, (categories.get(category) || 0) + 1);
            });
        });

        return Array.from(categories.entries()).map(([name, count]) => ({
            name,
            count,
            icon: this.getCategoryIcon(name)
        })).sort((a, b) => b.count - a.count);
    });

    constructor(private adminService: AdminService) { }

    ngOnInit() {
        this.loadData();
    }

    async loadData() {
        await Promise.all([
            this.loadAgents(),
            this.loadSystemHealth()
        ]);
    }

    async loadAgents() {
        try {
            this.isLoading.set(true);
            const agents = await this.adminService.getAgents();
            this.agents.set(agents);
        } catch (error) {
            console.error('Failed to load agents:', error);
        } finally {
            this.isLoading.set(false);
        }
    }

    async loadSystemHealth() {
        try {
            const health = await this.adminService.getSystemHealth();
            this.systemHealth.set(health);
        } catch (error) {
            console.error('Failed to load system health:', error);
        }
    }

    async refreshHealth() {
        try {
            this.isRefreshing.set(true);
            await this.loadSystemHealth();
        } finally {
            this.isRefreshing.set(false);
        }
    }

    toggleTools(agentName: string) {
        const expanded = this.expandedAgents();
        const newExpanded = new Set(expanded);

        if (newExpanded.has(agentName)) {
            newExpanded.delete(agentName);
        } else {
            newExpanded.add(agentName);
        }

        this.expandedAgents.set(newExpanded);
    }

    formatAgentName(name: string): string {
        // Split by underscores and capitalize each word
        return name.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ')
            .replace(/Agent/i, '')
            .trim();
    }

    formatToolName(tool: { id: string; name: string }): string {
        // Split by underscores and capitalize each word
        return tool.name.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ')
            .replace(/^(Pdf|Sample|Scrape)_/, '')
            .trim();
    }

    getToolCategory(tool: { id: string; name: string }): string {
        if (tool.name.startsWith('pdf_')) return 'PDF Processing';
        if (tool.name.startsWith('scrape_') || tool.name.includes('url')) return 'Web Scraping';
        if (tool.name.startsWith('sample_')) return 'Sample Tools';
        if (tool.name === 'add') return 'Math Operations';
        return 'General';
    }

    getCategoryIcon(category: string): string {
        switch (category) {
            case 'PDF Processing': return 'icon-file-text';
            case 'Web Scraping': return 'icon-globe';
            case 'Sample Tools': return 'icon-code';
            case 'Math Operations': return 'icon-calculator';
            default: return 'icon-tool';
        }
    }

    getHealthClass(status: string): string {
        switch (status.toLowerCase()) {
            case 'healthy':
            case 'ok':
                return 'healthy';
            case 'unhealthy':
            case 'error':
                return 'unhealthy';
            default:
                return 'unknown';
        }
    }

    getHealthText(status: string): string {
        switch (status.toLowerCase()) {
            case 'healthy':
            case 'ok':
                return 'System Healthy';
            case 'unhealthy':
            case 'error':
                return 'System Issues';
            default:
                return 'Status Unknown';
        }
    }

    getStatusClass(status: string): string {
        return status;
    }

    getStatusText(status: string): string {
        switch (status) {
            case 'healthy': return 'Online';
            case 'unhealthy': return 'Offline';
            default: return 'Unknown';
        }
    }

    formatTime(timestamp: string): string {
        return new Date(timestamp).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}
