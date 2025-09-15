import { ChangeDetectionStrategy, Component, input, signal, output } from '@angular/core';
import { IconComponent } from '@ngx-templates/shared/icon';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'acb-pdf-preview',
  imports: [IconComponent, CommonModule],
  templateUrl: './pdf-preview.component.html',
  styleUrl: './pdf-preview.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PdfPreviewComponent {
  fileName = input<string>('');
  isOpen = input<boolean>(false);
  close = output<void>();

  isLoading = signal(true);
  error = signal<string | null>(null);

  onClose() {
    this.close.emit();
  }

  onLoad() {
    this.isLoading.set(false);
  }

  onError() {
    this.isLoading.set(false);
    this.error.set('Failed to load PDF preview');
  }
}
