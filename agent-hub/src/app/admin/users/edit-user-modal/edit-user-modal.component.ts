import { Component, Input, Output, EventEmitter, OnInit, OnChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../services/admin.service';
import { User, UserRole } from '../../../services/auth.service';

interface UserFormData {
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

@Component({
  selector: 'app-edit-user-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './edit-user-modal.component.html',
  styleUrl: './edit-user-modal.component.scss'
})
export class EditUserModalComponent implements OnInit, OnChanges {
  @Input() user: User | null = null;
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() userUpdated = new EventEmitter<void>();

  isLoading = signal(false);
  errorMessage = signal<string | null>(null);
  
  formData: UserFormData = {
    full_name: '',
    email: '',
    role: UserRole.USER,
    is_active: true
  };

  // Expose enum to template
  readonly UserRole = UserRole;

  constructor(private adminService: AdminService) {}

  ngOnInit() {
    this.initializeForm();
  }

  ngOnChanges() {
    this.initializeForm();
  }

  private initializeForm() {
    if (this.user) {
      console.log('Initializing form with user:', this.user);
      this.formData = {
        full_name: this.user.full_name || '',
        email: this.user.email || '',
        role: this.user.role || UserRole.USER,
        is_active: this.user.is_active !== false // Default to true if undefined
      };
      console.log('Form data initialized:', this.formData);
    }
  }

  onClose() {
    this.errorMessage.set(null);
    this.close.emit();
  }

  async onSubmit() {
    if (!this.user) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    try {
      await this.adminService.updateUser(this.user.id, this.formData);
      this.userUpdated.emit();
      this.onClose();
    } catch (error: any) {
      console.error('Failed to update user:', error);
      this.errorMessage.set(
        error.error?.detail || 
        error.message || 
        'Failed to update user. Please try again.'
      );
    } finally {
      this.isLoading.set(false);
    }
  }

  isFormValid(): boolean {
    return this.formData.full_name.trim() !== '' && 
           this.formData.email.trim() !== '' &&
           this.formData.email.includes('@');
  }
}
