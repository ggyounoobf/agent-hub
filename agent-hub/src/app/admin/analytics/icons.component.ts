import { Component } from '@angular/core';

@Component({
  selector: 'app-analytics-icons',
  template: `
    <svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
      <symbol id="icon-users" viewBox="0 0 24 24">
        <path fill="currentColor" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4s-4 1.79-4 4s1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
      </symbol>
      <symbol id="icon-message-circle" viewBox="0 0 24 24">
        <path fill="currentColor" d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
      </symbol>
      <symbol id="icon-file-text" viewBox="0 0 24 24">
        <path fill="currentColor" d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
      </symbol>
      <symbol id="icon-cpu" viewBox="0 0 24 24">
        <path fill="currentColor" d="M6 4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1s1-.45 1-1V6h3c.55 0 1-.45 1-1s-.45-1-1-1H6zm12 0c-.55 0-1 .45-1 1s.45 1 1 1h3v3c0 .55.45 1 1 1s1-.45 1-1V5c0-.55-.45-1-1-1h-4zm1 14c0 .55-.45 1-1 1h-3c-.55 0-1 .45-1 1s.45 1 1 1h4c.55 0 1-.45 1-1v-4c0-.55-.45-1-1-1s-1 .45-1 1v3zM5 16c-.55 0-1 .45-1 1v3c0 .55.45 1 1 1h4c.55 0 1-.45 1-1s-.45-1-1-1H6v-3c0-.55-.45-1-1-1zm3-8c0-.55-.45-1-1-1H5c-.55 0-1 .45-1 1s.45 1 1 1h2c.55 0 1-.45 1-1z"/>
        <path fill="currentColor" d="M7 10h10c.55 0 1-.45 1-1s-.45-1-1-1H7c-.55 0-1 .45-1 1s.45 1 1 1z"/>
      </symbol>
      <symbol id="icon-check-circle" viewBox="0 0 24 24">
        <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10s10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5l1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </symbol>
      <symbol id="icon-file" viewBox="0 0 24 24">
        <path fill="currentColor" d="M6 2c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6H6zm7 7V3.5L18.5 9H13z"/>
      </symbol>
    </svg>
  `,
  standalone: true
})
export class AnalyticsIconsComponent {}