import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { MarketplaceApi, Tool } from '../api/marketplace-api.service';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../services/auth.service';

export interface AgentInfo {
  id: string;
  name: string;
  displayName: string;
  description: string;
  tools: Tool[];
  isSelected: boolean;
}

@Injectable({ providedIn: 'root' })
export class AgentService {
  private http = inject(HttpClient);
  private _marketplaceApi = inject(MarketplaceApi);
  private _authService = inject(AuthService);

  private _agents = signal<AgentInfo[]>([]);
  private _loading = signal<boolean>(false);
  private _error = signal<string | null>(null);

  agents = this._agents.asReadonly();
  loading = this._loading.asReadonly();
  error = this._error.asReadonly();

  selectedAgents = computed(() =>
    this._agents().filter(agent => agent.isSelected)
  );

  selectedAgentIds = computed(() =>
    this.selectedAgents().map(agent => agent.id)
  );

  selectedAgentNames = computed(() =>
    this.selectedAgents().map(agent => agent.name)
  );

  // Save selected agent IDs to localStorage
  private saveSelectionToStorage(agentIds: string[]) {
    try {
      localStorage.setItem('selectedAgentIds', JSON.stringify(agentIds));
    } catch (e) {
      console.warn('Could not save agent selection to localStorage', e);
    }
  }

  // Load selected agent IDs from localStorage
  private loadSelectionFromStorage(): string[] {
    try {
      const stored = localStorage.getItem('selectedAgentIds');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.warn('Could not load agent selection from localStorage', e);
      return [];
    }
  }

  async loadAgents() {
    this._loading.set(true);
    this._error.set(null);

    try {
      // Get current selection state before reloading
      // First try to get from current state, then from storage
      let currentSelection = new Set(this.selectedAgentIds());
      let hasStoredSelection = false;
      if (currentSelection.size === 0) {
        // If no current selection, try to load from storage
        const storedSelection = this.loadSelectionFromStorage();
        hasStoredSelection = storedSelection.length > 0;
        currentSelection = new Set(storedSelection);
      }

      // Check if user is admin
      const isAdmin = this._authService.isAdmin();
      
      if (isAdmin) {
        // For admin users, fetch all available agents
        const data: any[] = await firstValueFrom(
          this.http.get<any[]>(`${environment.apiUrl}/marketplace/agents`, {
            withCredentials: true
          })
        );

        console.log('Admin agents data:', data); // Debug log

        // Convert agents to AgentInfo format, preserving selection state
        const agents: AgentInfo[] = data.map((agent: any) => {
          // Handle both possible API response formats
          return {
            id: agent.id,
            name: agent.name,
            displayName: this._formatDisplayName(agent.name),
            description: this._generateDescription(agent.name, agent.tools),
            tools: agent.tools,
            isSelected: currentSelection.has(agent.id) // Preserve selection state
          };
        });

        // For admin users, if no agents are selected and no selection was stored,
        // automatically select all agents
        if (currentSelection.size === 0 && !hasStoredSelection && agents.length > 0) {
          // Select all agents for admin users
          agents.forEach(agent => {
            agent.isSelected = true;
            currentSelection.add(agent.id);
          });
          // Save this automatic selection to storage
          this.saveSelectionToStorage(agents.map(agent => agent.id));
        }

        console.log('Processed agents:', agents); // Debug log
        this._agents.set(agents);
      } else {
        // For regular users, fetch accessible agents (owned agents) using the proper API service
        const data = await firstValueFrom(this._marketplaceApi.getOwnedAgents());

        console.log('User agents data:', data); // Debug log

        // Convert owned agents to AgentInfo format, preserving selection state
        const agents: AgentInfo[] = data.map((agent: any) => ({
          id: agent.id,
          name: agent.name,
          displayName: this._formatDisplayName(agent.name),
          description: this._generateOwnedAgentDescription(agent.name),
          tools: agent.tools,
          isSelected: currentSelection.has(agent.id) // Preserve selection state
        }));

        console.log('Processed user agents:', agents); // Debug log
        this._agents.set(agents);
      }
    } catch (error) {
      console.error('Error loading agents:', error);
      this._error.set(error instanceof Error ? error.message : 'Failed to load agents');
    } finally {
      this._loading.set(false);
    }
  }

  toggleAgent(agentId: string) {
    this._agents.update(agents =>
      agents.map(agent =>
        agent.id === agentId
          ? { ...agent, isSelected: !agent.isSelected }
          : agent
      )
    );
    // Save the new selection to storage
    this.saveSelectionToStorage(this.selectedAgentIds());
  }

  selectAgent(agentId: string) {
    this._agents.update(agents =>
      agents.map(agent =>
        agent.id === agentId
          ? { ...agent, isSelected: true }
          : agent
      )
    );
    // Save the new selection to storage
    this.saveSelectionToStorage(this.selectedAgentIds());
  }

  deselectAgent(agentId: string) {
    this._agents.update(agents =>
      agents.map(agent =>
        agent.id === agentId
          ? { ...agent, isSelected: false }
          : agent
      )
    );
    // Save the new selection to storage
    this.saveSelectionToStorage(this.selectedAgentIds());
  }

  clearSelection() {
    this._agents.update(agents =>
      agents.map(agent => ({ ...agent, isSelected: false }))
    );
    // Save the new selection to storage
    this.saveSelectionToStorage(this.selectedAgentIds());
  }

  selectMultipleAgents(agentIds: string[]) {
    this._agents.update(agents =>
      agents.map(agent => ({
        ...agent,
        isSelected: agentIds.includes(agent.id)
      }))
    );
    // Save the new selection to storage
    this.saveSelectionToStorage(agentIds);
  }

  // Set a single agent as selected (deselecting all others)
  setSelectedAgent(agentId: string) {
    this._agents.update(agents =>
      agents.map(agent => ({
        ...agent,
        isSelected: agent.id === agentId
      }))
    );
    // Save the new selection to storage
    this.saveSelectionToStorage([agentId]);
  }

  // Initialize agents with a specific selection state
  initializeAgentsWithSelection(agentData: any[], selectedAgentIds: string[], isAdmin: boolean = false) {
    const agents: AgentInfo[] = agentData.map((agent: any) => {
      return {
        id: agent.id,
        name: agent.name,
        displayName: this._formatDisplayName(agent.name),
        description: isAdmin 
          ? this._generateDescription(agent.name, agent.tools)
          : this._generateOwnedAgentDescription(agent.name),
        tools: agent.tools,
        isSelected: selectedAgentIds.includes(agent.id)
      };
    });

    this._agents.set(agents);
    // Save the selection to storage
    this.saveSelectionToStorage(selectedAgentIds);
  }

  private _formatDisplayName(agentId: string): string {
    return agentId
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  private _generateDescription(agentId: string, tools: Tool[]): string {
    const descriptions: Record<string, string> = {
      'sample_agent': 'Basic sample tools for testing and demonstration purposes',
      'scraper_agent': 'Web scraping and PDF processing capabilities',
      'general_agent': 'General-purpose tools combining basic and web functionality',
      'admin_agent': 'Full administrative access with all available tools'
    };

    return descriptions[agentId] || `Agent with ${tools.length} available tools`;
  }

  private _generateOwnedAgentDescription(agentId: string): string {
    const descriptions: Record<string, string> = {
      'sample_agent': 'Basic sample tools for testing and demonstration purposes',
      'scraper_agent': 'Web scraping and PDF processing capabilities',
      'general_agent': 'General-purpose tools combining basic and web functionality',
      'admin_agent': 'Full administrative access with all available tools'
    };

    return descriptions[agentId] || 'Owned agent with specialized capabilities';
  }
}