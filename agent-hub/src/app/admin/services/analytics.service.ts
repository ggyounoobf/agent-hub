import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../services/auth.service';

// Analytics Overview Response
interface AnalyticsOverviewResponse {
  data: {
    total_users: number;
    total_chats: number;
    total_queries: number;
    total_files: number;
    total_agents: number;
    recent_users: number;
    recent_chats: number;
    recent_queries: number;
    recent_files: number;
    query_success_rate: number;
    most_active_users: Array<{
      username: string;
      query_count: number;
    }>;
  };
}

// Usage Statistics Response
interface UsageStatisticsResponse {
  data: {
    query_time_series: Array<{
      date: string;
      value: number;
    }>;
    chat_time_series: Array<{
      date: string;
      value: number;
    }>;
    file_time_series: Array<{
      date: string;
      value: number;
    }>;
    agent_usage: Array<{
      agent_name: string;
      usage_count: number;
    }>;
    file_types: Array<{
      content_type: string;
      count: number;
      total_size: number;
    }>;
  };
}

// Agent Performance Response
interface AgentPerformanceResponse {
  data: {
    agent_performance: Array<{
      agent_name: string;
      total_queries: number;
      success_rate: number;
      average_tokens: number;
    }>;
    tool_usage: {
      [agent_name: string]: Array<{
        tool_name: string;
        usage_count: number;
      }>;
    };
  };
}

// User Activity Response
interface UserActivityResponse {
  data: {
    user_registration_time_series: Array<{
      date: string;
      value: number;
    }>;
    active_users_time_series: Array<{
      date: string;
      value: number;
    }>;
    user_engagement: Array<{
      username: string;
      query_count: number;
    }>;
  };
}

export interface AnalyticsOverview {
  total_users: number;
  total_chats: number;
  total_queries: number;
  total_files: number;
  total_agents: number;
  recent_users: number;
  recent_chats: number;
  recent_queries: number;
  recent_files: number;
  query_success_rate: number;
  most_active_users: Array<{
    username: string;
    query_count: number;
  }>;
}

export interface UsageStatistics {
  query_time_series: Array<{
    date: string;
    value: number;
  }>;
  chat_time_series: Array<{
    date: string;
    value: number;
  }>;
  file_time_series: Array<{
    date: string;
    value: number;
  }>;
  agent_usage: Array<{
    agent_name: string;
    usage_count: number;
  }>;
  file_types: Array<{
    content_type: string;
    count: number;
    total_size: number;
  }>;
}

export interface AgentPerformance {
  agent_performance: Array<{
    agent_name: string;
    total_queries: number;
    success_rate: number;
    average_tokens: number;
  }>;
  tool_usage: {
    [agent_name: string]: Array<{
      tool_name: string;
      usage_count: number;
    }>;
  };
}

export interface UserActivity {
  user_registration_time_series: Array<{
    date: string;
    value: number;
  }>;
  active_users_time_series: Array<{
    date: string;
    value: number;
  }>;
  user_engagement: Array<{
    username: string;
    query_count: number;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiUrl;
  private auth = inject(AuthService);

  private getAuthHeaders() {
    const token = this.auth.getAccessToken();
    return {
      Authorization: `Bearer ${token}`
    };
  }

  async getOverview(days: number = 30): Promise<AnalyticsOverview> {
    try {
      const response = await firstValueFrom(
        this.http.get<AnalyticsOverviewResponse>(`${this.apiUrl}/analytics/overview?days=${days}`, {
          headers: this.getAuthHeaders()
        })
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch analytics overview:', error);
      throw error;
    }
  }

  async getUsageStatistics(days: number = 30): Promise<UsageStatistics> {
    try {
      const response = await firstValueFrom(
        this.http.get<UsageStatisticsResponse>(`${this.apiUrl}/analytics/usage?days=${days}`, {
          headers: this.getAuthHeaders()
        })
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch usage statistics:', error);
      throw error;
    }
  }

  async getAgentPerformance(days: number = 30): Promise<AgentPerformance> {
    try {
      const response = await firstValueFrom(
        this.http.get<AgentPerformanceResponse>(`${this.apiUrl}/analytics/performance?days=${days}`, {
          headers: this.getAuthHeaders()
        })
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch agent performance:', error);
      throw error;
    }
  }

  async getUserActivity(days: number = 30): Promise<UserActivity> {
    try {
      const response = await firstValueFrom(
        this.http.get<UserActivityResponse>(`${this.apiUrl}/analytics/activity?days=${days}`, {
          headers: this.getAuthHeaders()
        })
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user activity:', error);
      throw error;
    }
  }
}