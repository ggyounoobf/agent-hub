import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../services/admin.service';
import { UserRole } from '../../../services/auth.service';

interface CreateUserFormData {
  full_name: string;
  email: string;
  username: string;
  password: string;
  role: UserRole;
}

@Component({
  selector: 'app-create-user-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './create-user-modal.component.html',
  styleUrl: './create-user-modal.component.scss'
})
export class CreateUserModalComponent {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() userCreated = new EventEmitter<void>();

  isLoading = signal(false);
  errorMessage = signal<string | null>(null);
  
  formData: CreateUserFormData = {
    full_name: '',
    email: '',
    username: '',
    password: '',
    role: UserRole.USER
  };

  // Expose enum to template
  readonly UserRole = UserRole;

  constructor(private adminService: AdminService) {}

  onClose() {
    this.resetForm();
    this.errorMessage.set(null);
    this.close.emit();
  }

  resetForm() {
    this.formData = {
      full_name: '',
      email: '',
      username: '',
      password: '',
      role: UserRole.USER
    };
  }

  generateUsername() {
    if (this.formData.email) {
      this.formData.username = this.formData.email.split('@')[0];
    }
  }

  async onSubmit() {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    try {
      await this.adminService.createUser(this.formData);
      this.userCreated.emit();
      this.onClose();
    } catch (error: any) {
      console.error('Failed to create user:', error);
      this.errorMessage.set(
        error.error?.detail || 
        error.message || 
        'Failed to create user. Please try again.'
      );
    } finally {
      this.isLoading.set(false);
    }
  }

  isFormValid(): boolean {
    return this.formData.full_name.trim() !== '' && 
           this.formData.email.trim() !== '' &&
           this.formData.email.includes('@') &&
           this.formData.username.trim() !== '' &&
           this.formData.password.length >= 6;
  }
}
