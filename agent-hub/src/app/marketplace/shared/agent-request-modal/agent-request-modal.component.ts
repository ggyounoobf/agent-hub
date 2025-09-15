import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import {
  MODAL_DATA,
  ModalContentComponent,
  ModalController
} from '@ngx-templates/shared/modal';
import { ToastsService } from '@ngx-templates/shared/toasts';

import { Agent, Tool } from '../../../api/marketplace-api.service';
import { MarketplaceService } from '../../../services/marketplace.service';

export interface AgentRequestModalData {
  agent: Agent;
}

@Component({
  selector: 'acb-agent-request-modal',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ModalContentComponent
  ],
  templateUrl: './agent-request-modal.component.html',
  styleUrl: './agent-request-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AgentRequestModalComponent {
  private _fb = inject(FormBuilder);
  private _marketplaceService = inject(MarketplaceService);
  private _toast = inject(ToastsService);

  data = inject<AgentRequestModalData>(MODAL_DATA);
  ctrl = inject(ModalController);

  submitting = signal(false);

  requestForm = this._fb.group({
    justification: ['', [Validators.required, Validators.minLength(10)]],
  });

  async onSubmit() {
    if (this.requestForm.valid && !this.submitting()) {
      this.submitting.set(true);

      try {
        const formValue = this.requestForm.value;
        const justification = formValue.justification || '';
        
        // Request agent access with justification using the marketplace API
        this._marketplaceService.requestAgentWithJustification(this.data.agent.id, justification).subscribe({
          next: (response) => {
            if (response?.status === 'success' || response?.status === 'already_requested') {
              this._toast.create(`Access request submitted for ${this.data.agent.name}`);
              this.ctrl.close({ success: true, response });
            } else {
              this._toast.create(response?.message || 'Failed to request agent access.');
              this.submitting.set(false);
            }
          },
          error: (error) => {
            console.error('Error submitting access request:', error);
            this._toast.create('Failed to submit access request.');
            this.submitting.set(false);
          }
        });
      } catch (error) {
        console.error('Error submitting access request:', error);
        this._toast.create('Failed to submit access request.');
        this.submitting.set(false);
      }
    }
  }

  onCancel() {
    this.ctrl.close(null);
  }

  getAgentDescription(agent: Agent): string {
    const toolCount = agent.tools?.length || 0;
    if (toolCount === 0) return 'Agent with no tools available.';
    
    return `Agent with ${toolCount} specialized tool${toolCount > 1 ? 's' : ''} for various automation tasks.`;
  }

  getAgentCategory(agent: Agent): string {
    const name = agent.name.toLowerCase();
    if (name.includes('pdf')) return 'Document Processing';
    if (name.includes('scrape') || name.includes('web')) return 'Web Scraping';
    if (name.includes('admin')) return 'Administration';
    if (name.includes('sample') || name.includes('demo')) return 'Sample & Demo';
    if (name.includes('analysis') || name.includes('analyze')) return 'Data Analysis';
    if (name.includes('search')) return 'Search & Query';
    return 'General';
  }
}