import { Component, ChangeDetectionStrategy, inject, OnInit, OnDestroy, output, ElementRef, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgentService, AgentInfo } from '../../../data-access/agent.service';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'acb-agent-selecwtor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './agent-selector.component.html',
  styleUrl: './agent-selector.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AgentSelectorComponent implements OnInit, OnDestroy {
  private _agentService = inject(AgentService);
  private _authService = inject(AuthService);

  @ViewChild('selectorButton', { static: false }) selectorButton?: ElementRef<HTMLButtonElement>;
  @ViewChild('dropdownPanel', { static: false }) dropdownPanel?: ElementRef<HTMLDivElement>;

  agents = this._agentService.agents;
  selectedAgents = this._agentService.selectedAgents;
  loading = this._agentService.loading;
  error = this._agentService.error;

  isOpen = false;
  searchTerm = '';
  isDesktop = false;

  agentSelectionChanged = output<string[]>();

  get filteredAgents(): AgentInfo[] {
    const agents = this.agents();
    if (!this.searchTerm) {
      return agents;
    }
    return agents.filter((agent: AgentInfo) =>
      agent.displayName.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      agent.description.toLowerCase().includes(this.searchTerm.toLowerCase())
    );
  }

  get selectedAgentNames(): string {
    const selected = this.selectedAgents();
    if (selected.length === 0) {
      return 'Select agents';
    }
    if (selected.length === 1) {
      return selected[0].displayName;
    }
    return `${selected.length} agents selected`;
  }

  get isAdmin(): boolean {
    return this._authService.isAdmin();
  }

  async ngOnInit() {
    await this._agentService.loadAgents();
    this.checkScreenSize();
    
    // For admin users, if no agents are selected, automatically select all agents
    if (this.isAdmin && this.selectedAgents().length === 0 && this.agents().length > 0) {
      this.selectAllAgents();
    }
  }

  @HostListener('window:resize')
  onResize() {
    this.checkScreenSize();
    if (this.isOpen) {
      this.positionDropdown();
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event) {
    // Only handle clicks for desktop dropdown
    if (!this.isDesktop || !this.isOpen) {
      return;
    }

    const target = event.target as HTMLElement;
    const element = this.selectorButton?.nativeElement;
    const dropdown = this.dropdownPanel?.nativeElement;
    
    if (element && dropdown && !element.contains(target) && !dropdown.contains(target)) {
      this.closeDropdown();
    }
  }

  private checkScreenSize() {
    this.isDesktop = window.innerWidth >= 768;
  }

  private positionDropdown() {
    if (!this.isDesktop || !this.selectorButton?.nativeElement || !this.dropdownPanel?.nativeElement) {
      return;
    }

    const button = this.selectorButton.nativeElement;
    const dropdown = this.dropdownPanel.nativeElement;
    const rect = button.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const dropdownHeight = 400; // Max height from CSS

    // Position dropdown intelligently
    const spaceBelow = viewportHeight - rect.bottom;
    const spaceAbove = rect.top;

    if (spaceBelow >= dropdownHeight || spaceBelow >= spaceAbove) {
      // Position below button
      dropdown.style.top = `${rect.bottom + 8}px`;
    } else {
      // Position above button
      dropdown.style.top = `${rect.top - dropdownHeight - 8}px`;
    }

    // Horizontal positioning
    dropdown.style.left = `${rect.left}px`;
    dropdown.style.width = `${Math.max(rect.width, 420)}px`;
  }

  toggleDropdown() {
    this.isOpen = !this.isOpen;
    
    if (this.isOpen) {
      if (this.isDesktop) {
        // Position dropdown after it's rendered
        setTimeout(() => this.positionDropdown(), 0);
      } else {
        // Prevent body scroll on mobile when modal is open
        document.body.style.overflow = 'hidden';
      }
    } else {
      // Restore body scroll when modal is closed
      document.body.style.overflow = '';
    }
  }

  onAgentToggle(agentId: string) {
    this._agentService.toggleAgent(agentId);
    this.agentSelectionChanged.emit(this._agentService.selectedAgentNames());
  }

  clearSelection() {
    this._agentService.clearSelection();
    this.agentSelectionChanged.emit([]);
  }

  applySelection() {
    this.agentSelectionChanged.emit(this._agentService.selectedAgentNames());
    this.closeDropdown();
  }

  showSelectedAgents() {
    // For mobile, open the modal to show selected agents
    this.toggleDropdown();
  }

  selectAllAgents() {
    // Select all available agents
    this._agentService.selectMultipleAgents(this.agents().map(agent => agent.id));
    this.agentSelectionChanged.emit(this._agentService.selectedAgentNames());
  }

  onSearchChange(event: Event) {
    const target = event.target as HTMLInputElement;
    this.searchTerm = target.value;
  }

  ngOnDestroy() {
    // Ensure body scroll is restored when component is destroyed
    document.body.style.overflow = '';
  }

  closeDropdown() {
    this.isOpen = false;
    // Always restore body scroll when closing
    document.body.style.overflow = '';
  }
}
