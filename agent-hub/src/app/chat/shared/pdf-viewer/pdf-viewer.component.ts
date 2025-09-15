import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
  inject,
  OnInit,
  effect
} from '@angular/core';
import { IconComponent } from '@ngx-templates/shared/icon';
import { CommonModule } from '@angular/common';
import { FileService } from '../../../services/file.service';
import { SafeUrlPipe } from '../../../shared/pipes/safe-url.pipe';

@Component({
  selector: 'acb-pdf-viewer',
  imports: [IconComponent, CommonModule, SafeUrlPipe],
  templateUrl: './pdf-viewer.component.html',
  styleUrl: './pdf-viewer.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PdfViewerComponent implements OnInit {
  private fileService = inject(FileService);

  fileId = input<string>('');
  fileName = input<string>('');
  isOpen = input<boolean>(false);
  close = output<void>();

  isLoading = signal(true);
  error = signal<string | null>(null);
  fileUrl = signal<string | null>(null);

  constructor() {
    // Effect to load PDF when file ID changes
    effect(() => {
      const fileId = this.fileId();
      if (fileId && this.isOpen()) {
        this.loadPdf(fileId);
      }
    });
  }

  ngOnInit() {
    // Load PDF if file ID is provided
    const fileId = this.fileId();
    if (fileId && this.isOpen()) {
      this.loadPdf(fileId);
    }
  }

  async loadPdf(fileId: string) {
    this.isLoading.set(true);
    this.error.set(null);
    this.fileUrl.set(null);

    try {
      const blob = await this.fileService.getFileContent(fileId);
      const url = URL.createObjectURL(blob);
      this.fileUrl.set(url);
    } catch (err) {
      console.error('Error loading PDF:', err);
      this.error.set('Failed to load PDF file');
    } finally {
      this.isLoading.set(false);
    }
  }

  onClose() {
    // Clean up object URL to prevent memory leaks
    const url = this.fileUrl();
    if (url) {
      URL.revokeObjectURL(url);
      this.fileUrl.set(null);
    }
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
