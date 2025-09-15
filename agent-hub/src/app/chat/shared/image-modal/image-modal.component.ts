import {
  Component,
  input,
  output,
  signal,
  ChangeDetectionStrategy,
  HostListener,
  OnDestroy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { IconComponent } from '@ngx-templates/shared/icon';

@Component({
  selector: 'acb-image-modal',
  standalone: true,
  imports: [CommonModule, IconComponent],
  templateUrl: './image-modal.component.html',
  styleUrl: './image-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class.modal-open]': 'isOpen()'
  }
})
export class ImageModalComponent implements OnDestroy {
  // Inputs
  isOpen = input<boolean>(false);
  imageUrl = input<string>('');
  imageTitle = input<string>('');
  imageAlt = input<string>('');

  // Outputs
  close = output<void>();

  // Internal state
  imageLoading = signal<boolean>(true);

  @HostListener('document:keydown.escape')
  onEscapePressed() {
    if (this.isOpen()) {
      this.closeModal();
    }
  }

  @HostListener('document:keydown.enter')
  onEnterPressed() {
    if (this.isOpen()) {
      this.downloadImage();
    }
  }

  ngOnDestroy() {
    // Cleanup any potential memory leaks and ensure scroll is restored
    document.body.style.overflow = '';
  }

  closeModal() {
    console.log('Closing image modal'); // Debug log
    this.close.emit();
    // Always restore body scroll
    document.body.style.overflow = '';
  }

  onImageLoad() {
    console.log('Image loaded successfully'); // Debug log
    this.imageLoading.set(false);
  }

  onImageError() {
    console.log('Image failed to load'); // Debug log
    this.imageLoading.set(false);
    console.error('Failed to load image:', this.imageUrl());
  }

  downloadImage() {
    console.log('Download button clicked'); // Debug log
    const url = this.imageUrl();
    if (url) {
      try {
        // Create a temporary anchor element to trigger download
        const link = document.createElement('a');
        link.href = url;
        link.download = this.generateFileName();
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        
        // Append to body, click, and remove
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log('Download initiated'); // Debug log
      } catch (error) {
        console.error('Failed to download image:', error);
        // Fallback: open in new tab
        this.openInNewTab();
      }
    }
  }

  openInNewTab() {
    console.log('Open in new tab button clicked'); // Debug log
    const url = this.imageUrl();
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
      console.log('Opened in new tab'); // Debug log
    }
  }

  private generateFileName(): string {
    const title = this.imageTitle() || 'image';
    const timestamp = new Date().toISOString().slice(0, 10);
    const cleanTitle = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    return `${cleanTitle}_${timestamp}.png`;
  }
}
