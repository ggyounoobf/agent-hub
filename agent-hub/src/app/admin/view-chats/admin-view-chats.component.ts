import { Component, OnInit, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService, Chat, ChatQuery } from '../services/admin.service';

@Component({
    selector: 'app-admin-view-chats',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './admin-view-chats.component.html',
    styleUrl: './admin-view-chats.component.scss'
})
export class AdminViewChatsComponent implements OnInit {
    allChats = signal<Chat[]>([]);
    isLoading = signal(true);
    searchTerm = signal('');
    sortBy = signal('createdAt');
    selectedChat = signal<Chat | null>(null);
    chatQueries = signal<ChatQuery[]>([]);
    isLoadingQueries = signal(false);
    
    // Pagination
    currentPage = signal(1);
    itemsPerPage = signal(12);
    totalPages = signal(1);

    filteredChats = computed(() => {
        let filtered = this.allChats();

        // Apply search filter
        const term = this.searchTerm().toLowerCase().trim();
        if (term) {
            filtered = filtered.filter(chat =>
                chat.userEmail.toLowerCase().includes(term) ||
                chat.userName.toLowerCase().includes(term) ||
                (chat.title && chat.title.toLowerCase().includes(term))
            );
        }

        // Apply sorting
        const sortField = this.sortBy();
        filtered.sort((a, b) => {
            switch (sortField) {
                case 'createdAt':
                    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
                case 'updatedAt':
                    return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
                case 'messageCount':
                    return b.messageCount - a.messageCount;
                case 'userName':
                    return a.userName.localeCompare(b.userName);
                default:
                    return 0;
            }
        });

        return filtered;
    });
    
    // Paginated chats
    paginatedChats = computed(() => {
        const filtered = this.filteredChats();
        return filtered.slice(
            (this.currentPage() - 1) * this.itemsPerPage(),
            this.currentPage() * this.itemsPerPage()
        );
    });

    constructor(private adminService: AdminService) {
        // Update total pages when filtered chats change
        effect(() => {
            const filtered = this.filteredChats();
            const totalPages = Math.ceil(filtered.length / this.itemsPerPage());
            this.totalPages.set(totalPages);
            
            // Reset to first page if current page is out of bounds
            if (this.currentPage() > totalPages && totalPages > 0) {
                this.currentPage.set(1);
            }
        });
    }

    ngOnInit() {
        this.loadChats();
    }

    async loadChats() {
        try {
            this.isLoading.set(true);
            const chats = await this.adminService.getAllChats();
            this.allChats.set(chats);
        } catch (error) {
            console.error('Failed to load chats:', error);
        } finally {
            this.isLoading.set(false);
        }
    }

    onSearchChange(event: Event) {
        const target = event.target as HTMLInputElement;
        this.searchTerm.set(target.value);
        this.filterChats();
    }

    onSortChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        this.sortBy.set(target.value);
        this.sortChats();
    }

    filterChats() {
        // Reset to first page when filtering
        this.currentPage.set(1);
    }

    sortChats() {
        // Reset to first page when sorting
        this.currentPage.set(1);
    }

    async viewChatDetails(chatId: string) {
        const chat = this.allChats().find(c => c.id === chatId);
        if (chat) {
            this.selectedChat.set(chat);
            this.isLoadingQueries.set(true);
            this.chatQueries.set(await this.adminService.getChatQueries(chatId));
            this.isLoadingQueries.set(false);
        }
    }

    closeModal() {
        this.selectedChat.set(null);
    }

    async deleteChat(chatId: string) {
        if (confirm('Are you sure you want to delete this chat? This action cannot be undone.')) {
            const ok = await this.adminService.deleteChat(chatId);
            if (ok) {
                await this.loadChats();
                if (this.selectedChat()?.id === chatId) this.closeModal();
            } else {
                alert('Failed to delete chat.');
            }
        }
    }
    
    // Pagination methods
    goToPage(page: number) {
        if (page >= 1 && page <= this.totalPages()) {
            this.currentPage.set(page);
            // Scroll to top of chat grid
            const chatGrid = document.querySelector('.chats-grid');
            if (chatGrid) {
                chatGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }
    
    goToPreviousPage() {
        if (this.currentPage() > 1) {
            this.goToPage(this.currentPage() - 1);
        }
    }
    
    goToNextPage() {
        if (this.currentPage() < this.totalPages()) {
            this.goToPage(this.currentPage() + 1);
        }
    }

    formatDate(date: Date | string): string {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getRelativeTime(date: Date | string): string {
        const now = new Date();
        const diff = now.getTime() - new Date(date).getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return 'Just now';
    }
}
