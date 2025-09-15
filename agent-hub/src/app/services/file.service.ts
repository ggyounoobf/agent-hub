import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { firstValueFrom } from 'rxjs';

export interface FileInfo {
  id: string;
  name: string;
  content_type: string;
  size: number;
  uploaded_at: string;
}

export interface FileDetails extends FileInfo {
  chat_id: string | null;
  query_id: string | null;
}

@Injectable({ providedIn: 'root' })
export class FileService {
  private http = inject(HttpClient);

  /**
   * Get all files for the current user
   */
  async getFiles(chatId?: string, queryId?: string): Promise<FileInfo[]> {
    let url = `${environment.apiUrl}/files/`;
    
    const params = new URLSearchParams();
    if (chatId) params.append('chat_id', chatId);
    if (queryId) params.append('query_id', queryId);
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const data = await firstValueFrom(
      this.http.get<any>(url, { withCredentials: true })
    );
    
    return data.items || data;
  }

  /**
   * Get detailed information about a specific file
   */
  async getFileDetails(fileId: string): Promise<FileDetails> {
    const data = await firstValueFrom(
      this.http.get<any>(`${environment.apiUrl}/files/${fileId}`, { withCredentials: true })
    );
    
    return data;
  }

  /**
   * Get file content for preview
   */
  async getFileContent(fileId: string): Promise<Blob> {
    const blob = await firstValueFrom(
      this.http.get(`${environment.apiUrl}/files/${fileId}/content`, { 
        responseType: 'blob',
        withCredentials: true
      })
    );
    
    return blob;
  }

  /**
   * Download a file
   */
  async downloadFile(fileId: string, fileName: string): Promise<void> {
    const blob = await firstValueFrom(
      this.http.get(`${environment.apiUrl}/files/${fileId}/download`, { 
        responseType: 'blob',
        withCredentials: true
      })
    );
    
    // Create a download link and trigger download
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Delete a file
   */
  async deleteFile(fileId: string): Promise<void> {
    await firstValueFrom(
      this.http.delete(`${environment.apiUrl}/files/${fileId}`, { withCredentials: true })
    );
  }
}