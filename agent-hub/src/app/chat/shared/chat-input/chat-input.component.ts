import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  inject,
  input,
  output,
  Renderer2,
  signal,
  viewChild,
  computed,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { IconComponent } from '@ngx-templates/shared/icon';
import { AgentService, AgentInfo } from '../../../data-access/agent.service';
import { AuthService } from '../../../services/auth.service';
import { Router } from '@angular/router';

export type InputEvent = {
  message: string;
  files: File[];
  complete: () => void;
};

@Component({
  selector: 'acb-chat-input',
  imports: [ReactiveFormsModule, FormsModule, CommonModule, IconComponent],
  templateUrl: './chat-input.component.html',
  styleUrl: './chat-input.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatInputComponent implements AfterViewInit, OnInit, OnDestroy {
  private _renderer = inject(Renderer2);
  private _formBuilder = inject(FormBuilder);
  private _agentService = inject(AgentService);
  private _router = inject(Router);
  protected _authService = inject(AuthService); // Make it protected so template can access it

  form = this._formBuilder.group({
    message: [''],
  });

  textarea = viewChild.required<ElementRef>('textarea');
  searchInput = viewChild<ElementRef>('searchInput');
  
  readonly disabled = input(false);
  readonly label = input('');
  readonly error = input<string | null>(null); // Add error input
  
  send = output<InputEvent>();
  abort = output<void>();
  agentSelectionChanged = output<string[]>();
  clearError = output<void>();
  
  processing = signal(false);
  selectedFiles = signal<File[]>([]);
  dragOver = signal(false);
  showAgentSelector = signal(false);
  agentError = signal<string | null>(null);
  loadingAgents = signal(false);
  searchQuery = signal<string>('');
  
  // Make agents and selectedAgents computed properties so they react to changes
  agents = this._agentService.agents;
  selectedAgents = this._agentService.selectedAgents;
  
  // Computed property for filtered agents based on search
  filteredAgents = computed(() => {
    const agents = this.agents();
    const query = this.searchQuery().toLowerCase();
    
    if (!query) {
      return agents;
    }
    
    return agents.filter(agent => 
      agent.name.toLowerCase().includes(query) || 
      agent.description.toLowerCase().includes(query)
    );
  });

  ngOnInit() {
    // Only load agents if they haven't been loaded yet
    if (this.agents().length === 0) {
      this.loadAgents();
    } else {
      // If agents are already loaded, emit the current selection
      const selectedAgentNames = this._agentService.selectedAgentNames();
      console.log('Agents already loaded, emitting current selection:', selectedAgentNames);
      this.agentSelectionChanged.emit(selectedAgentNames);
    }
  }

  ngAfterViewInit() {
    this.focus();
    
    // Add padding to body on mobile to account for fixed input
    if (window.innerWidth <= 768) {
      const inputHeight = 80; // Approximate height of input container on mobile
      document.body.style.paddingBottom = `${inputHeight}px`;
    }
  }

  ngOnDestroy() {
    if (this.showAgentSelector()) {
      document.body.style.overflow = '';
    }
    
    // Remove padding from body
    document.body.style.paddingBottom = '';
  }

  @HostListener('window:resize', ['$event'])
  onResize(event: Event) {
    // Adjust body padding based on screen size
    if (window.innerWidth <= 768) {
      const inputHeight = 80; // Approximate height of input container on mobile
      document.body.style.paddingBottom = `${inputHeight}px`;
    } else {
      document.body.style.paddingBottom = '';
    }
  }

  @HostListener('document:keydown.enter', ['$event'])
  onEnterPress(e: Event) {
    // Cast to KeyboardEvent since we know it's a keyboard event
    const keyEvent = e as KeyboardEvent;
    
    // Check if the target is our textarea
    const isTargetTextarea = keyEvent.target === this.textarea().nativeElement;
    
    // Don't handle if not from our textarea or if shift is held (for multiline)
    if (!isTargetTextarea || keyEvent.shiftKey) {
      return;
    }

    // Prevent the default behavior (adding newline)
    keyEvent.preventDefault();
    keyEvent.stopPropagation();

    this.sendMessage();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event) {
    // Close modal if click is outside of it
    if (this.showAgentSelector() && event.target instanceof HTMLElement) {
      const modal = document.querySelector('.agent-modal');
      if (modal && !modal.contains(event.target)) {
        this.closeAgentSelector();
      }
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      const newFiles = Array.from(input.files);
      this.selectedFiles.update(files => [...files, ...newFiles]);
    }
    // Clear the input so the same file can be selected again
    input.value = '';
  }

  removeFile(fileToRemove: File) {
    this.selectedFiles.update(files => 
      files.filter(file => file !== fileToRemove)
    );
  }

  sendMessage() {
    if (this.processing()) {
      return;
    }

    const message = this.form.value.message?.trim() || '';
    const files = this.selectedFiles();

    // Check if we have either a message or files
    if (!message && files.length === 0) {
      return;
    }

    this.processing.set(true);

    this.send.emit({
      message,
      files,
      complete: () => this.processing.set(false),
    });

    // Reset the form and clear selected files
    this.form.reset();
    this.selectedFiles.set([]);
    
    // Explicitly clear the textarea value and reset its height
    const textareaEl = this.textarea().nativeElement;
    textareaEl.value = '';
    this._renderer.setStyle(textareaEl, 'height', 'auto');
    
    // Focus the textarea
    this.focus();
  }

  abortProcessing() {
    this.abort.emit();
    this.focus();
  }

  focus() {
    // Only focus on non-mobile devices or when not processing
    if (window.innerWidth > 768 || !this.processing()) {
      const textareaEl = this.textarea().nativeElement;
      textareaEl.focus();
      // Set cursor to the end of text (in case there's any remaining text)
      textareaEl.setSelectionRange(textareaEl.value.length, textareaEl.value.length);
    }
  }

  // Agent-related methods
  async loadAgents() {
    try {
      this.loadingAgents.set(true);
      this.agentError.set(null);
      await this._agentService.loadAgents();
      // Emit the selected agent names when agents are loaded
      const selectedAgentNames = this._agentService.selectedAgentNames();
      console.log('Selected agent names:', selectedAgentNames); // Debug log
      this.agentSelectionChanged.emit(selectedAgentNames);
    } catch (err) {
      this.agentError.set('Failed to load agents. Please try again.');
      console.error('Error loading agents:', err);
    } finally {
      this.loadingAgents.set(false);
    }
  }

  toggleAgentSelector() {
    const newState = !this.showAgentSelector();
    this.showAgentSelector.set(newState);
    
    // Prevent body scroll when modal is open
    document.body.style.overflow = newState ? 'hidden' : '';
    
    // Focus search input when modal opens
    if (newState && this.searchInput()) {
      setTimeout(() => {
        this.searchInput()?.nativeElement.focus();
      }, 100);
    }
    
    // Clear search when opening modal
    if (newState) {
      this.searchQuery.set('');
    }
  }

  closeAgentSelector() {
    this.showAgentSelector.set(false);
    document.body.style.overflow = '';
  }

  toggleAgent(agentId: string) {
    console.log('Toggling agent:', agentId);
    this._agentService.toggleAgent(agentId);
    // Emit the selected agent names, not IDs
    const selectedAgentNames = this._agentService.selectedAgentNames();
    console.log('Selected agent names after toggle:', selectedAgentNames);
    this.agentSelectionChanged.emit(selectedAgentNames);
  }

  removeAgent(agentId: string) {
    this._agentService.toggleAgent(agentId);
    // Emit the selected agent names, not IDs
    const selectedAgentNames = this._agentService.selectedAgentNames();
    console.log('Selected agent names after remove:', selectedAgentNames);
    this.agentSelectionChanged.emit(selectedAgentNames);
  }

  clearAllAgents() {
    this._agentService.clearSelection();
    this.agentSelectionChanged.emit([]);
  }

  isAgentSelected(agentId: string): boolean {
    return this.selectedAgents().some(agent => agent.id === agentId);
  }

  formatAgentName(agentId: string): string {
    return agentId
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  getAgentButtonTitle(): string {
    const count = this.selectedAgents().length;
    if (count === 0) return 'Select agents to use in chat';
    if (this._authService.isAdmin()) {
      return `Admin mode: ${count} agent${count > 1 ? 's' : ''} selected`;
    }
    return `${count} agent${count > 1 ? 's' : ''} selected`;
  }

  setHeight() {
    const element = this.textarea().nativeElement;

    this._renderer.setStyle(element, 'height', null);
    this._renderer.setStyle(
      element,
      'height',
      Math.min(element.scrollHeight, 200) + 2.5 + 'px' // Limit to 200px max height
    );
  }
  
  onSearchInput(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
  }
  
  goToMarketplace() {
    this.closeAgentSelector();
    this._router.navigate(['/marketplace']);
  }
}