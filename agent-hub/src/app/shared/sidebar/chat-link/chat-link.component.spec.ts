import { Chat } from './../../../../model';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { provideRouter } from '@angular/router';

import { ChatLinkComponent } from './chat-link.component';
import { fetchApiMockProvider } from '../../utils/fetch-mock-provider.test-util';

describe('ChatLinkComponent', () => {
  let component: ChatLinkComponent;
  let fixture: ComponentFixture<ChatLinkComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatLinkComponent],
      providers: [
        provideRouter([]), 
        fetchApiMockProvider,
        {
          provide: HttpClient,
          useValue: {
            get: () => new Observable(),
            post: () => new Observable(),
            delete: () => new Observable(),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatLinkComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('chat', new Chat({}));
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
