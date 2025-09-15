import { Routes } from '@angular/router';
import { adminGuard } from '../guards/admin.guard';

export const ADMIN_ROUTES: Routes = [
    {
        path: '',
        loadComponent: () => import('./admin.component').then(m => m.AdminComponent),
        canActivate: [adminGuard],
        children: [
            {
                path: '',
                redirectTo: 'overview',
                pathMatch: 'full'
            },
            {
                path: 'overview',
                loadComponent: () => import('./overview/admin-overview.component').then(m => m.AdminOverviewComponent)
            },
            {
                path: 'analytics',
                loadComponent: () => import('./analytics/analytics-dashboard.component').then(m => m.AnalyticsDashboardComponent)
            },
            {
                path: 'view-chats',
                loadComponent: () => import('./view-chats/admin-view-chats.component').then(m => m.AdminViewChatsComponent)
            },
            {
                path: 'agents',
                loadComponent: () => import('./agents/admin-agents.component').then(m => m.AdminAgentsComponent)
            },
            {
                path: 'users',
                loadComponent: () => import('./users/admin-users.component').then(m => m.AdminUsersComponent)
            },
            {
                path: 'system',
                loadComponent: () => import('./system/admin-system.component').then(m => m.AdminSystemComponent)
            },
            {
                path: 'activity',
                loadComponent: () => import('./activity/activity-logs.component').then(m => m.ActivityLogsComponent)
            }
        ]
    }
];
