import { Pipe, PipeTransform, inject } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MarkdownService } from '../../services/markdown.service';

@Pipe({
  name: 'markdown',
  standalone: true
})
export class MarkdownPipe implements PipeTransform {
  private _sanitizer = inject(DomSanitizer);
  private _markdownService = inject(MarkdownService);

  transform(value: string): SafeHtml {
    if (!value) return '';
    const html = this._markdownService.render(value);
    return this._sanitizer.bypassSecurityTrustHtml(html);
  }
}