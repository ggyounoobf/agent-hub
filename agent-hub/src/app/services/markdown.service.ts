import { Injectable } from '@angular/core';
import { marked } from 'marked';

@Injectable({
  providedIn: 'root'
})
export class MarkdownService {
  constructor() {
    // Configure marked options
    marked.setOptions({
      gfm: true,
      breaks: true
    });
  }

  render(markdown: string): string {
    if (!markdown) return '';
    return marked.parse(markdown) as string;
  }
}