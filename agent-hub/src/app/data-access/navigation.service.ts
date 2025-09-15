import { Injectable, inject, signal } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';
import { RoutePrefix } from '../route-prefixes';

@Injectable({
    providedIn: 'root'
})
export class NavigationService {
    private _router = inject(Router);

    // Track if marketplace is currently open
    isMarketplaceOpen = signal<boolean>(false);

    // Track the last chat route to return to
    private _lastChatRoute = signal<string>('/');

    // Current route signal
    private _currentRoute = toSignal(
        this._router.events.pipe(
            filter(event => event instanceof NavigationEnd),
            map(event => (event as NavigationEnd).url)
        )
    );

    constructor() {
        // Watch for route changes to update marketplace state
        this._router.events.pipe(
            filter(event => event instanceof NavigationEnd)
        ).subscribe((event: NavigationEnd) => {
            const isMarketplace = event.url.includes(RoutePrefix.Marketplace);
            this.isMarketplaceOpen.set(isMarketplace);

            // Store last non-marketplace route
            if (!isMarketplace) {
                this._lastChatRoute.set(event.url);
            }
        });
    }

    toggleMarketplace(): void {
        if (this.isMarketplaceOpen()) {
            // If marketplace is open, navigate back to last chat route
            this.navigateToChat();
        } else {
            // If not in marketplace, navigate to marketplace
            this.navigateToMarketplace();
        }
    }

    private navigateToMarketplace(): void {
        this._router.navigate([`/${RoutePrefix.Marketplace}`]);
    }

    private navigateToChat(): void {
        const lastRoute = this._lastChatRoute();
        // If no previous route or it was marketplace, go to home
        if (!lastRoute || lastRoute.includes(RoutePrefix.Marketplace)) {
            this._router.navigate(['/']);
        } else {
            this._router.navigate([lastRoute]);
        }
    }

    getCurrentRoute(): string {
        return this._currentRoute() || '/';
    }

    getLastChatRoute(): string {
        return this._lastChatRoute();
    }
}
