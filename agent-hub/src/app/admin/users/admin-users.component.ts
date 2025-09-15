import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../services/admin.service';
// Reuse exported interfaces/enums from AuthService instead of non-existent user.model
import { User, UserRole } from '../../services/auth.service';
import { EditUserModalComponent } from './edit-user-modal/edit-user-modal.component';
import { CreateUserModalComponent } from './create-user-modal/create-user-modal.component';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule, EditUserModalComponent, CreateUserModalComponent],
  templateUrl: './admin-users.component.html',
  styleUrl: './admin-users.component.scss'
})
export class AdminUsersComponent implements OnInit {
  allUsers = signal<User[]>([]);
  users = signal<User[]>([]);
  isLoading = signal(true);
  searchTerm = '';
  roleFilter = '';

  // Modal states
  showCreateModal = signal(false);
  showEditModal = signal(false);
  selectedUser = signal<User | null>(null);

  // Expose enum to template
  readonly UserRole = UserRole;

  constructor(private adminService: AdminService) { }

  ngOnInit() {
    this.loadUsers();
  }

  async loadUsers() {
    try {
      this.isLoading.set(true);
      const list = await this.adminService.getUsers();
      this.allUsers.set(list as any);
      this.applyFilters();
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      this.isLoading.set(false);
    }
  }

  applyFilters() {
    let filtered = this.allUsers();

    // Apply role filter - using lowercase values to match API response
    if (this.roleFilter) {
      filtered = filtered.filter(user => user.role === this.roleFilter);
    }

    // Apply search filter
    if (this.searchTerm.trim()) {
      const term = this.searchTerm.toLowerCase();
      filtered = filtered.filter(user =>
        (user.full_name || '').toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term)
      );
    }

    this.users.set(filtered);
  }

  filterUsers() {
    this.applyFilters();
  }

  openCreateUserModal() {
    this.showCreateModal.set(true);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
  }

  onUserCreated() {
    this.loadUsers();
  }

  editUser(user: User) {
    // Create a copy to avoid reference issues
    this.selectedUser.set({...user});
    this.showEditModal.set(true);
  }

  closeEditModal() {
    this.showEditModal.set(false);
    this.selectedUser.set(null);
  }

  onUserUpdated() {
    this.loadUsers();
  }

  async promoteToAdmin(userId: string) {
    if (confirm('Are you sure you want to promote this user to admin?')) {
      try {
        // Using lowercase "admin" to match API response format
        const success = await this.adminService.updateUserRole(userId, 'admin');
        if (success) {
          await this.loadUsers(); // Refresh the list
        } else {
          alert('Failed to promote user. Please try again.');
        }
      } catch (error) {
        console.error('Failed to promote user:', error);
        alert('Failed to promote user. Please try again.');
      }
    }
  }

  async demoteToUser(userId: string) {
    if (confirm('Are you sure you want to demote this admin to user?')) {
      try {
        // Using lowercase "user" to match API response format
        const success = await this.adminService.updateUserRole(userId, 'user');
        if (success) {
          await this.loadUsers(); // Refresh the list
        } else {
          alert('Failed to demote user. Please try again.');
        }
      } catch (error) {
        console.error('Failed to demote user:', error);
        alert('Failed to demote user. Please try again.');
      }
    }
  }

  async deleteUser(userId: string) {
    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      try {
        const success = await this.adminService.deleteUser(userId);
        if (success) {
          await this.loadUsers(); // Refresh the list
        } else {
          alert('Failed to delete user. Please try again.');
        }
      } catch (error) {
        console.error('Failed to delete user:', error);
        alert('Failed to delete user. Please try again.');
      }
    }
  }

  getUserInitials(fullName: string | undefined): string {
    if (!fullName) return 'NA';
    return (fullName || '')
      .split(' ')
      .map(name => name.charAt(0))
      .join('')
      .substring(0, 2)
      .toUpperCase();
  }

  getRoleClass(role: string): string {
    return role.toLowerCase();
  }

  formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
}
