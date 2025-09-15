import { Routes } from '@angular/router';
import { ChatComponent } from './chat/chat.component';
import { MarketplaceComponent } from './marketplace/marketplace.component';
import { RequestManagementComponent } from './marketplace/request-management/request-management.component';
import { LoginComponent } from './components/login/login.component';
import { OAuthCallbackComponent } from './components/oauth-callback/oauth-callback.component';
import { RoutePrefix } from './route-prefixes';
import { authGuard, guestGuard } from './guards/auth.guard';

export const APP_ROUTES: Routes = [
  {
    path: '',
    children: [
      {
        path: '',
        redirectTo: 'chat',
        pathMatch: 'full',
      },
      {
        path: 'login',
        component: LoginComponent,
        canActivate: [guestGuard],
      },
      {
        path: 'auth/callback',
        component: OAuthCallbackComponent,
      },
      {
        path: RoutePrefix.Home,
        component: ChatComponent,
        canActivate: [authGuard],
      },
      {
        path: RoutePrefix.Marketplace,
        component: MarketplaceComponent,
        canActivate: [authGuard],
      },
      {
        path: 'access-requests',
        component: RequestManagementComponent,
        canActivate: [authGuard],
      },
      {
        path: 'admin',
        loadChildren: () => import('./admin/admin.routes').then(m => m.ADMIN_ROUTES),
        canActivate: [authGuard],
      },
      {
        path: RoutePrefix.Chat + '/:id',
        component: ChatComponent,
        canActivate: [authGuard],
      },
      {
        path: '**',
        redirectTo: 'chat',
      },
    ],
  },
];
