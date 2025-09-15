import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'acb-agent-status',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (selectedAgents().length > 0) {
      <!-- Hidden main status for now -->
      <div class="agent-status" [class.hidden]="!showStatus">

        <div class="selected-agents">
          @for (agent of selectedAgents(); track agent) {
            <span class="agent-badge">{{ formatAgentName(agent) }}</span>
          }
        </div>
      </div>

      <!-- Small floating button to show selected agents -->
      <button class="floating-status-button" (click)="toggleStatus()">
        {{ selectedAgents().length }}
      </button>
    }
  `,
  styles: [`
    .agent-status {
      background: rgba(139, 92, 246, 0.1);
      border: 1px solid rgba(139, 92, 246, 0.3);
      border-radius: 12px;
      padding: 16px 20px;
      margin: 16px 0;
      margin-top: 20px; // Add extra top margin to account for header
      transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      transform-origin: top;
      animation: expandIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

      @media (min-width: 769px) {
        padding: 20px 24px;
        margin: 20px 0;
        margin-top: 24px; // Add extra top margin for desktop
        border-radius: 16px;
      }



      .selected-agents {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;

        @media (min-width: 769px) {
          gap: 10px;
        }

        .agent-badge {
          background: rgba(139, 92, 246, 0.2);
          color: #e0e0e0;
          padding: 6px 10px;
          border-radius: 14px;
          font-size: 12px;
          font-weight: 500;

          @media (min-width: 769px) {
            padding: 8px 12px;
            border-radius: 16px;
            font-size: 14px;
          }
        }
      }

      &.hidden {
        opacity: 0;
        transform: scaleY(0);
        height: 0;
        margin: 0;
        padding: 0;
        overflow: hidden;
      }
    }

    @keyframes expandIn {
      from {
        opacity: 0;
        transform: scaleY(0);
      }
      to {
        opacity: 1;
        transform: scaleY(1);
      }
    }

    .floating-status-button {
      position: fixed;
      top: 80px; // Position below the header (60px + 20px margin)
      right: 24px;
      width: 24px;
      height: 24px;
      background: rgba(139, 92, 246, 0.9);
      backdrop-filter: blur(10px);
      border: none;
      border-radius: 50%;
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
      transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
      z-index: 999; // Lower z-index than header to avoid conflicts
      display: block;
      line-height: 24px;
      text-align: center;
      animation: slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

      /* Badge positioning in top-right corner */
      transform-origin: center;

      &:hover {
        background: rgba(124, 58, 237, 0.95);
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
        animation: pulse 0.6s ease-in-out;
      }

      &:active {
        transform: scale(0.9);
        transition: all 0.1s ease;
      }

      @media (min-width: 769px) {
        top: 88px; // Position below the header (60px + 28px margin)
        right: 32px;
        width: 28px;
        height: 28px;
        font-size: 11px;
        line-height: 28px;
      }
    }

    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateX(10px) scale(0.7);
      }
      to {
        opacity: 1;
        transform: translateX(0) scale(1);
      }
    }

    @keyframes pulse {
      0% {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
      }
      50% {
        transform: scale(1.1);
        box-shadow: 0 6px 16px rgba(139, 92, 246, 0.6);
      }
      100% {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AgentStatusComponent {
  selectedAgents = input.required<string[]>();
  showStatus = false; // Hidden by default

  formatAgentName(agentId: string): string {
    return agentId
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  toggleStatus(): void {
    this.showStatus = !this.showStatus;
  }
}
