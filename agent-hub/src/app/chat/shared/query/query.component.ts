import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  input,
  signal,
  OnDestroy,
} from '@angular/core';
import { IconComponent } from '@ngx-templates/shared/icon';

import { Query } from '../../../../model';
import { QuerySkeletonComponent } from '../query-skeleton/query-skeleton.component';
import { MarkdownPipe } from '../../../shared/pipes/markdown.pipe';
import { FilePreviewComponent } from '../file-preview/file-preview.component';
import { PdfViewerComponent } from '../pdf-viewer/pdf-viewer.component';
import { ImageModalComponent } from '../image-modal/image-modal.component';
import { FileInfo } from '../../../services/file.service';

@Component({
  selector: 'acb-query',
  imports: [
    IconComponent, 
    QuerySkeletonComponent, 
    MarkdownPipe,
    FilePreviewComponent,
    PdfViewerComponent,
    ImageModalComponent
  ],
  templateUrl: './query.component.html',
  styleUrl: './query.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QueryComponent implements AfterViewInit, OnDestroy {
  private _elRef = inject(ElementRef);

  query = input.required<Query>();
  isNew = input<boolean>();
  
  showPdfViewer = signal(false);
  selectedFile = signal<FileInfo | null>(null);
  
  // Image modal state
  showImageModal = signal(false);
  selectedImageUrl = signal('');
  selectedImageTitle = signal('');
  selectedImageAlt = signal('');

  ngAfterViewInit() {
    // Scroll into the view newly created queries.
    if (this.isNew()) {
      this._elRef.nativeElement.scrollIntoView();
    }
    
    // Set up image click handlers using event delegation
    this.setupImageClickHandlers();
  }
  
  onFilePreview(file: FileInfo) {
    this.selectedFile.set(file);
    this.showPdfViewer.set(true);
  }
  
  closePdfViewer() {
    this.showPdfViewer.set(false);
    this.selectedFile.set(null);
  }
  
  onImageClick(imageUrl: string, imageTitle?: string, imageAlt?: string) {
    console.log('Image clicked:', { imageUrl, imageTitle, imageAlt }); // Debug log
    this.selectedImageUrl.set(imageUrl);
    this.selectedImageTitle.set(imageTitle || 'Chart/Image Preview');
    this.selectedImageAlt.set(imageAlt || 'Full size image');
    this.showImageModal.set(true);
    
    // Only prevent body scroll when modal is actually open
    setTimeout(() => {
      if (this.showImageModal()) {
        document.body.style.overflow = 'hidden';
      }
    }, 0);
    console.log('Image modal should be open now'); // Debug log
  }
  
  closeImageModal() {
    console.log('Closing image modal from query component'); // Debug log
    this.showImageModal.set(false);
    this.selectedImageUrl.set('');
    this.selectedImageTitle.set('');
    this.selectedImageAlt.set('');
    
    // Always restore body scroll when closing modal
    document.body.style.overflow = '';
  }
  
  ngOnDestroy() {
    // Clean up event listeners
    this.removeImageClickHandlers();
    
    // Ensure body scroll is restored when component is destroyed
    document.body.style.overflow = '';
  }
  
  private setupImageClickHandlers() {
    // Use event delegation - add one handler to the container that handles all image clicks
    const container = this._elRef.nativeElement;
    
    // Remove any existing handler
    if ((container as any)._imageClickHandler) {
      container.removeEventListener('click', (container as any)._imageClickHandler);
    }
    
    // Create the delegated click handler
    const imageClickHandler = (event: Event) => {
      const target = event.target as HTMLElement;
      
      // Check if the clicked element is an image inside the chat message
      if (target.tagName === 'IMG' && target.closest('.acb-chat-msg')) {
        console.log('Image click event triggered via delegation:', event); // Debug log
        event.preventDefault();
        event.stopPropagation();
        
        const img = target as HTMLImageElement;
        const src = img.src;
        const alt = img.alt || '';
        const title = img.title || this.extractImageTitle(src);
        
        console.log('Calling onImageClick with:', { src, title, alt }); // Debug log
        this.onImageClick(src, title, alt);
      }
    };
    
    // Store the handler for later removal
    (container as any)._imageClickHandler = imageClickHandler;
    
    // Add the delegated event listener
    container.addEventListener('click', imageClickHandler);
    
    // Style all images to indicate they're clickable
    const images = container.querySelectorAll('.acb-chat-msg img');
    console.log('Styling', images.length, 'images as clickable'); // Debug log
    
    images.forEach((img: HTMLImageElement, index: number) => {
      // Add visual indicators
      img.style.cursor = 'pointer';
      img.title = 'Click to view full size';
      
      // Add loading and error handlers
      img.addEventListener('load', () => {
        img.removeAttribute('data-loading');
        img.removeAttribute('data-error');
      });
      
      img.addEventListener('error', () => {
        img.removeAttribute('data-loading');
        img.setAttribute('data-error', 'true');
      });
      
      // Set initial loading state
      if (!img.complete) {
        img.setAttribute('data-loading', 'true');
      }
      
      // Add hover effect with overlay
      this.addImageOverlay(img);
    });
  }
  
  private addImageOverlay(img: HTMLImageElement) {
    // Only add overlay if not already present
    if (img.parentElement?.classList.contains('image-container-wrapper')) {
      return;
    }
    
    // Create a container to hold both image and overlay
    const container = document.createElement('div');
    container.className = 'image-container-wrapper';
    container.style.cssText = `
      position: relative;
      display: inline-block;
      max-width: 100%;
    `;
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'image-overlay';
    overlay.innerHTML = '🔍';
    overlay.style.cssText = `
      position: absolute;
      top: 8px;
      right: 8px;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      border-radius: 50%;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      opacity: 0;
      transition: opacity 0.3s ease;
      pointer-events: none;
      z-index: 10;
    `;
    
    // Wrap the image in the container
    img.parentNode?.insertBefore(container, img);
    container.appendChild(img);
    container.appendChild(overlay);
    
    // Show overlay on hover
    container.addEventListener('mouseenter', () => {
      overlay.style.opacity = '1';
    });
    
    container.addEventListener('mouseleave', () => {
      overlay.style.opacity = '0';
    });
  }
  
  private removeImageClickHandlers() {
    const container = this._elRef.nativeElement;
    const handler = (container as any)._imageClickHandler;
    if (handler) {
      container.removeEventListener('click', handler);
      delete (container as any)._imageClickHandler;
    }
  }
  
  private extractImageTitle(url: string): string {
    // Extract a meaningful title from the URL
    if (url.includes('chart')) return 'Chart Preview';
    if (url.includes('graph')) return 'Graph Preview';
    if (url.includes('diagram')) return 'Diagram Preview';
    if (url.includes('mdn.alipayobjects.com')) return 'Chart Preview';
    
    // Extract filename from URL
    const urlParts = url.split('/');
    const filename = urlParts[urlParts.length - 1];
    const nameWithoutExtension = filename.split('.')[0];
    
    return nameWithoutExtension || 'Image Preview';
  }
}
