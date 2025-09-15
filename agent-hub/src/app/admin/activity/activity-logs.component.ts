import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService, ActivityLog, ActivitySearchRequest } from '../services/admin.service';

@Component({
  selector: 'app-activity-logs',
  standalone: true,
  imports: [CommonModule, FormsModule, JsonPipe],
  templateUrl: './activity-logs.component.html',
  styleUrl: './activity-logs.component.scss'
})
export class ActivityLogsComponent implements OnInit {
  // Activity logs data
  activityLogs = signal<ActivityLog[]>([]);
  expandedLogs = signal<Set<string>>(new Set());
  
  // Pagination
  currentPage = signal(1);
  pageSize = signal(50);
  totalCount = signal(0);
  totalPages = signal(0);
  
  // Filters and search
  selectedTypes = signal<('user' | 'chat' | 'agent' | 'system')[]>([]);
  startTime = signal<string>('');
  endTime = signal<string>('');
  searchQuery = signal<string>('');
  
  // UI state
  isLoading = signal(false);
  lastUpdated = signal<Date>(new Date());
  
  constructor(private adminService: AdminService) {}
  
  ngOnInit() {
    this.loadActivityLogs();
  }
  
  async loadActivityLogs() {
    this.isLoading.set(true);
    
    try {
      // If we have a search query or specific filters, use search endpoint
      if (this.searchQuery() || this.selectedTypes().length > 0 || this.startTime() || this.endTime()) {
        // Convert lowercase types to uppercase for API
        const apiTypes = this.selectedTypes().length > 0 
          ? this.selectedTypes().map(type => type.toUpperCase() as 'USER' | 'CHAT' | 'AGENT' | 'SYSTEM')
          : undefined;
          
        const searchRequest: ActivitySearchRequest = {
          query: this.searchQuery() || undefined,
          types: apiTypes,
          start_time: this.startTime() || undefined,
          end_time: this.endTime() || undefined,
          page: this.currentPage(),
          page_size: this.pageSize()
        };
        
        const response = await this.adminService.searchActivityLogs(searchRequest);
        this.activityLogs.set(response.events);
        this.totalCount.set(response.total_count);
        this.totalPages.set(Math.ceil(response.total_count / response.page_size));
      } 
      // Otherwise, use the recent activity endpoint
      else {
        // Convert lowercase types to uppercase for API
        const apiTypes = this.selectedTypes().length > 0 
          ? this.selectedTypes().map(type => type.toUpperCase() as 'USER' | 'CHAT' | 'AGENT' | 'SYSTEM')
          : undefined;
          
        const logs = await this.adminService.getRecentActivityLogs(
          this.pageSize(),
          apiTypes as ('user' | 'chat' | 'agent' | 'system')[] | undefined,
          undefined,
          this.startTime() || undefined,
          this.endTime() || undefined
        );
        this.activityLogs.set(logs);
        this.totalCount.set(logs.length);
        this.totalPages.set(1);
      }
      
      this.lastUpdated.set(new Date());
    } catch (error) {
      console.error('Failed to load activity logs:', error);
    } finally {
      this.isLoading.set(false);
    }
  }
  
  async refreshLogs() {
    this.currentPage.set(1);
    await this.loadActivityLogs();
  }
  
  async previousPage() {
    if (this.currentPage() > 1) {
      this.currentPage.set(this.currentPage() - 1);
      await this.loadActivityLogs();
    }
  }
  
  async nextPage() {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.set(this.currentPage() + 1);
      await this.loadActivityLogs();
    }
  }
  
  toggleMetadata(logId: string) {
    const expanded = new Set(this.expandedLogs());
    if (expanded.has(logId)) {
      expanded.delete(logId);
    } else {
      expanded.add(logId);
    }
    this.expandedLogs.set(expanded);
  }
  
  onTypeFilterChange() {
    this.currentPage.set(1);
    this.loadActivityLogs();
  }
  
  onDateRangeChange() {
    this.currentPage.set(1);
    this.loadActivityLogs();
  }
  
  onSearchChange() {
    // Debounce search to avoid too many requests
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.currentPage.set(1);
      this.loadActivityLogs();
    }, 500);
  }
  
  resetFilters() {
    // Reset all filters
    this.selectedTypes.set([]);
    this.startTime.set('');
    this.endTime.set('');
    this.searchQuery.set('');
    this.currentPage.set(1);
    this.loadActivityLogs();
  }
  
  private searchTimeout: any;
  
  getLogTypeClass(type: string): string {
    switch (type) {
      case 'user': return 'user-log';
      case 'chat': return 'chat-log';
      case 'agent': return 'agent-log';
      case 'system': return 'system-log';
      default: return '';
    }
  }
  
  formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }
  
  formatMetadata(metadata: Record<string, any>): string {
    return JSON.stringify(metadata, null, 2);
  }
}