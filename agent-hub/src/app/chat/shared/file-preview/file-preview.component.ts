import { 
  ChangeDetectionStrategy, 
  Component, 
  input, 
  output, 
  inject
} from '@angular/core';
import { IconComponent } from '@ngx-templates/shared/icon';
import { CommonModule } from '@angular/common';
import { FileService, FileInfo } from '../../../services/file.service';
import { FileUploaded } from '../../../../model/query';

@Component({
  selector: 'acb-file-preview',
  imports: [IconComponent, CommonModule],
  templateUrl: './file-preview.component.html',
  styleUrl: './file-preview.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FilePreviewComponent {
  private fileService = inject(FileService);
  
  chatId = input<string>('');
  queryId = input<string>('');
  filesUploaded = input<FileUploaded[]>([]);
  filePreview = output<FileInfo>();
  
  async onFileClick(file: FileUploaded) {
    try {
      // Fetch the full file info using the file ID
      const fileInfo = await this.fileService.getFileDetails(file.id);
      // Emit the file info for preview
      this.filePreview.emit(fileInfo);
    } catch (error) {
      console.error('Error fetching file details:', error);
      alert(`Failed to load file "${file.name}". Please try again.`);
    }
  }
  
  isPdfFile(fileName: string): boolean {
    return fileName.toLowerCase().endsWith('.pdf');
  }
}