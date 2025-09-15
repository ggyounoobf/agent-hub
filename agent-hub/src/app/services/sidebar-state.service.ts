import { Injectable, signal, inject } from '@angular/core';
import { LocalStorage } from '@ngx-templates/shared/services';

const SIDEBAR_STATE_KEY = 'acb-sb-expanded';

@Injectable({
  providedIn: 'root'
})
export class SidebarStateService {
  private _storage = inject(LocalStorage);
  private _expanded = signal<boolean>(false);

  // Read-only signal for consumers
  expanded = this._expanded.asReadonly();

  constructor() {
    // Initialize from localStorage
    const savedState = this._storage.get(SIDEBAR_STATE_KEY) === 'true';
    this._expanded.set(savedState);
  }

  setExpanded(expanded: boolean): void {
    this._expanded.set(expanded);
    this._saveToStorage(expanded);
  }

  toggle(): void {
    this._expanded.update(current => {
      const newValue = !current;
      this._saveToStorage(newValue);
      return newValue;
    });
  }

  private _saveToStorage(expanded: boolean): void {
    this._storage.set(SIDEBAR_STATE_KEY, expanded.toString());
  }
}
