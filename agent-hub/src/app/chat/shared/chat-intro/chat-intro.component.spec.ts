import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChatIntroComponent } from './chat-intro.component';
import { fetchApiMockProvider } from '../../../shared/utils/fetch-mock-provider.test-util';

describe('ChatIntroComponent', () => {
  let component: ChatIntroComponent;
  let fixture: ComponentFixture<ChatIntroComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatIntroComponent],
      providers: [fetchApiMockProvider]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ChatIntroComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
