import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ModalService } from '@ngx-templates/shared/modal';
import { ToastsService } from '@ngx-templates/shared/toasts';
import { MarketplaceService } from '../services/marketplace.service';
import { Agent, OwnedAgent, UserAgentStats, AgentRequest, Tool } from '../api/marketplace-api.service';
import { AgentRequestModalComponent } from './shared/agent-request-modal/agent-request-modal.component';

interface FilterOptions {
  category: string;
  status: string;
}
// Define the tool interface
interface ToolObject {
  id: string;
  name: string;
}

@Component({
  selector: 'acb-marketplace',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './marketplace.component.html',
  styleUrl: './marketplace.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MarketplaceComponent implements OnInit {
  private readonly _modal = inject(ModalService);
  private readonly _toast = inject(ToastsService);
  private readonly _marketplaceService = inject(MarketplaceService);
  private readonly _router = inject(Router);

  // Signals
  searchQuery = signal<string>('');
  selectedFilters = signal<FilterOptions>({
    category: '',
    status: ''
  });
  agents = signal<Agent[]>([]);
  ownedAgents = signal<OwnedAgent[]>([]);
  userRequests = signal<AgentRequest[]>([]);
  userAgentStats = signal<UserAgentStats | null>(null);
  loading = signal<boolean>(false);
  statsLoading = signal<boolean>(false);
  requestsLoading = signal<boolean>(false);

  // Computed properties for enhanced display
  agentsWithEnhancements = computed(() => {
    const ownedAgentIds = new Set(this.ownedAgents().map(agent => agent.id));
    const requestedAgentIds = new Set(this.userRequests().map(request => request.agent_id));
    
    return this.agents().map(agent => ({
      ...agent,
      // Enhanced properties for display
      category: this.getCategoryFromName(agent.name),
      status: this.getStatusFromName(agent.name),
      description: this.getDescriptionFromAgent(agent),
      icon: this.getIconFromName(agent.name),
      toolCount: agent.tools?.length || 0,
      capabilities: this.getCapabilitiesFromTools(agent.tools || []),
      isOwned: ownedAgentIds.has(agent.id),
      isRequested: requestedAgentIds.has(agent.id) && !ownedAgentIds.has(agent.id)
    }));
  });

  // Computed properties for dynamic filters based on enhanced data
  availableCategories = computed(() => {
    const categories = new Set<string>();
    this.agentsWithEnhancements().forEach(agent => {
      if (agent.category) {
        categories.add(agent.category);
      }
    });
    return Array.from(categories).sort();
  });

  availableStatuses = computed(() => {
    const statuses = new Set<string>();
    this.agentsWithEnhancements().forEach(agent => {
      if (agent.status) {
        statuses.add(agent.status);
      }
    });
    return Array.from(statuses).sort();
  });

  // Updated filtered agents to use enhanced data
  filteredAgents = computed(() => {
    const query = this.searchQuery().toLowerCase();
    const filters = this.selectedFilters();
    
    return this.agentsWithEnhancements().filter(agent => {
      const matchesSearch = !query ||
        agent.name.toLowerCase().includes(query) ||
        (agent.tools && agent.tools.some(tool => tool.name.toLowerCase().includes(query))) ||
        (agent.description && agent.description.toLowerCase().includes(query)) ||
        (agent.capabilities && agent.capabilities.some(cap => cap.toLowerCase().includes(query)));
      
      const matchesCategory = !filters.category || agent.category === filters.category;
      const matchesStatus = !filters.status || agent.status === filters.status;
      
      return matchesSearch && matchesCategory && matchesStatus;
    });
  });

  ngOnInit() {
    this.loadAgents();
    this.loadOwnedAgents();
    this.loadUserStats();
    this.loadUserRequests();
  }

  async loadAgents() {
    try {
      this.loading.set(true);
      this._marketplaceService.getAgents().subscribe({
        next: (agents) => {
          this.agents.set(agents || []);
          this.loading.set(false);
        },
        error: (error) => {
          console.error('Failed to load agents:', error);
          this._toast.create('Failed to load agents.');
          this.loading.set(false);
        }
      });
    } catch (error) {
      console.error('Error loading agents:', error);
      this._toast.create('Failed to load agents.');
      this.loading.set(false);
    }
  }

  async loadOwnedAgents() {
    try {
      this._marketplaceService.getOwnedAgents().subscribe({
        next: (owned) => {
          this.ownedAgents.set(owned || []);
        },
        error: (error) => {
          console.error('Failed to load owned agents:', error);
          this._toast.create('Failed to load owned agents.');
        }
      });
    } catch (error) {
      console.error('Error loading owned agents:', error);
      this._toast.create('Failed to load owned agents.');
    }
  }

  async loadUserStats() {
    try {
      this.statsLoading.set(true);
      this._marketplaceService.getUserAgentStats().subscribe({
        next: (stats) => {
          this.userAgentStats.set(stats);
          this.statsLoading.set(false);
        },
        error: (error) => {
          console.error('Failed to load user stats:', error);
          this._toast.create('Failed to load user stats.');
          this.statsLoading.set(false);
        }
      });
    } catch (error) {
      console.error('Error loading user stats:', error);
      this._toast.create('Failed to load user stats.');
      this.statsLoading.set(false);
    }
  }

  async loadUserRequests() {
    try {
      this.requestsLoading.set(true);
      this._marketplaceService.getMyRequests().subscribe({
        next: (requests) => {
          this.userRequests.set(requests || []);
          this.requestsLoading.set(false);
        },
        error: (error) => {
          console.error('Failed to load user requests:', error);
          this._toast.create('Failed to load user requests.');
          this.requestsLoading.set(false);
        }
      });
    } catch (error) {
      console.error('Error loading user requests:', error);
      this._toast.create('Failed to load user requests.');
      this.requestsLoading.set(false);
    }
  }

  async requestAgent(agent: Agent) {
    // Open the agent request modal
    const modal = this._modal.createModal(AgentRequestModalComponent, {
      agent: agent
    });

    modal.closed.then((result: any) => {
      if (result && result.success) {
        // Refresh data after successful request
        this.loadOwnedAgents();
        this.loadUserStats();
        this.loadUserRequests();
      }
    });
  }

  // Get agent details
  getAgentDetails(agentId: string) {
    return this._marketplaceService.getAgentById(agentId);
  }

  // Filter methods
  clearFilters() {
    this.selectedFilters.set({
      category: '',
      status: ''
    });
    this.searchQuery.set('');
  }

  onFilterChange(filterType: keyof FilterOptions, event: Event) {
    const target = event.target as HTMLSelectElement;
    const currentFilters = this.selectedFilters();
    this.selectedFilters.set({
      ...currentFilters,
      [filterType]: target.value
    });
  }

  onSearchInput(event: Event) {
    const target = event.target as HTMLInputElement;
    this.searchQuery.set(target.value);
  }

  // Helper methods for enhancing agent data
  getCategoryFromName(name: string): string {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('pdf')) return 'Document Processing';
    if (lowerName.includes('scrape') || lowerName.includes('web')) return 'Web Scraping';
    if (lowerName.includes('admin')) return 'Administration';
    if (lowerName.includes('sample') || lowerName.includes('demo')) return 'Sample & Demo';
    if (lowerName.includes('analysis') || lowerName.includes('analyze')) return 'Data Analysis';
    if (lowerName.includes('search')) return 'Search & Query';
    if (lowerName.includes('security')) return 'Security';
    return 'General';
  }

  getStatusFromName(name: string): string {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('admin')) return 'admin-only';
    if (lowerName.includes('sample') || lowerName.includes('demo')) return 'available';
    return 'available';
  }

  getDescriptionFromAgent(agent: Agent): string {
    // Use the description from the API if available
    if (agent.description && agent.description.trim() !== '') {
      return agent.description;
    }
    
    // Fallback to generated descriptions if no API description is provided
    const name = agent.name.toLowerCase();
    const toolCount = agent.tools?.length || 0;
    
    if (name.includes('pdf')) {
      return `Advanced PDF processing agent with ${toolCount} specialized tools for text extraction, metadata analysis, and document indexing.`;
    }
    if (name.includes('scrape') || name.includes('web')) {
      return `Web scraping specialist with ${toolCount} tools for extracting content, metadata, and links from web pages.`;
    }
    if (name.includes('admin')) {
      return `Comprehensive admin agent with access to ${toolCount} tools across multiple categories for system management.`;
    }
    if (name.includes('sample') || name.includes('demo')) {
      return `Sample demonstration agent with ${toolCount} example tools for testing and learning purposes.`;
    }
    if (name.includes('analysis') || name.includes('analyze')) {
      return `Data analysis agent with ${toolCount} tools for processing and interpreting complex datasets.`;
    }
    if (name.includes('search')) {
      return `Search and query agent with ${toolCount} tools for finding and retrieving information.`;
    }
    if (name.includes('security')) {
      return `Security analysis agent with ${toolCount} tools for web security scanning and vulnerability assessment.`;
    }
    return `Specialized AI agent equipped with ${toolCount} tools for various automation tasks.`;
  }

  getIconFromName(name: string): string {
    // Return empty string since we're removing icons
    return '';
  }

  formatAgentName(name: string): string {
    // Replace underscores with spaces and capitalize each word
    return name
      .replace(/_/g, ' ')
      .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
  }

  getCapabilitiesFromTools(tools: Tool[]): string[] {
    const capabilities = new Set<string>();
    
    tools.forEach(tool => {
      const lowerTool = tool.name.toLowerCase();
      if (lowerTool.includes('pdf')) capabilities.add('PDF Processing');
      if (lowerTool.includes('scrape') || lowerTool.includes('extract') || lowerTool.includes('web')) capabilities.add('Web Scraping');
      if (lowerTool.includes('search') || lowerTool.includes('query')) capabilities.add('Search & Query');
      if (lowerTool.includes('metadata')) capabilities.add('Metadata Extraction');
      if (lowerTool.includes('index')) capabilities.add('Document Indexing');
      if (lowerTool.includes('semantic')) capabilities.add('Semantic Analysis');
      if (lowerTool.includes('status') || lowerTool.includes('admin')) capabilities.add('System Management');
      if (lowerTool.includes('sample') || lowerTool.includes('hello') || lowerTool.includes('demo')) capabilities.add('Demo & Testing');
      if (lowerTool.includes('combine') || lowerTool.includes('count') || lowerTool.includes('process')) capabilities.add('Text Processing');
      if (lowerTool.includes('analyze') || lowerTool.includes('analysis')) capabilities.add('Data Analysis');
      if (lowerTool.includes('security') || lowerTool.includes('ssl') || lowerTool.includes('dns')) capabilities.add('Security Analysis');
    });

    return Array.from(capabilities);
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'available': return 'status-available';
      case 'admin-only': return 'status-admin';
      case 'pending': return 'status-pending';
      default: return 'status-default';
    }
  }

  getStatusText(status: string): string {
    switch (status) {
      case 'available': return 'Available';
      case 'admin-only': return 'Admin Only';
      case 'pending': return 'Pending Approval';
      default: return 'Unknown';
    }
  }

  getAgentProperty(agent: any, property: string, defaultValue: any = null): any {
    return agent[property] !== undefined ? agent[property] : defaultValue;
  }

  hasProperty(agent: any, property: string): boolean {
    return agent.hasOwnProperty(property);
  }

  viewDetails(agent: Agent) {
    // Navigate to agent details page or open modal
    console.log('Viewing details for agent:', agent);
  }

  navigateToRequests() {
    // Route to /access-requests
    this._router.navigate(['/access-requests']);
  }
}