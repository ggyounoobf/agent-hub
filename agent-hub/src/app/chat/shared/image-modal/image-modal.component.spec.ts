import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { IconComponent } from '@ngx-templates/shared/icon';

import { ImageModalComponent } from './image-modal.component';

describe('ImageModalComponent', () => {
  let component: ImageModalComponent;
  let fixture: ComponentFixture<ImageModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImageModalComponent, CommonModule, IconComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ImageModalComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should not show modal when isOpen is false', () => {
    fixture.componentRef.setInput('isOpen', false);
    fixture.detectChanges();

    const modalElement = fixture.nativeElement.querySelector('.image-modal-overlay');
    expect(modalElement).toBeFalsy();
  });

  it('should show modal when isOpen is true', () => {
    fixture.componentRef.setInput('isOpen', true);
    fixture.componentRef.setInput('imageUrl', 'test-image.jpg');
    fixture.detectChanges();

    const modalElement = fixture.nativeElement.querySelector('.image-modal-overlay');
    expect(modalElement).toBeTruthy();
  });

  it('should emit close event when close button is clicked', () => {
    spyOn(component.close, 'emit');

    fixture.componentRef.setInput('isOpen', true);
    fixture.componentRef.setInput('imageUrl', 'test-image.jpg');
    fixture.detectChanges();

    const closeButton = fixture.nativeElement.querySelector('.close-button');
    closeButton.click();

    expect(component.close.emit).toHaveBeenCalled();
  });

  it('should emit close event when escape key is pressed', () => {
    spyOn(component.close, 'emit');

    fixture.componentRef.setInput('isOpen', true);
    component.onEscapePressed();

    expect(component.close.emit).toHaveBeenCalled();
  });

  it('should generate appropriate filename for download', () => {
    fixture.componentRef.setInput('imageTitle', 'My Chart');
    fixture.detectChanges();

    const result = (component as any).generateFileName();
    expect(result).toContain('my_chart');
    expect(result).toContain('.png');
  });
});
