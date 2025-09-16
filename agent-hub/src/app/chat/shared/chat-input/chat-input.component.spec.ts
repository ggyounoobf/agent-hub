import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { FETCH_MOCK_STATE } from '@ngx-templates/shared/fetch';

import { ChatInputComponent } from './chat-input.component';
import { fetchApiMockProvider } from '../../../shared/utils/fetch-mock-provider.test-util';

describe('ChatInputComponent', () => {
  let component: ChatInputComponent;
  let fixture: ComponentFixture<ChatInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatInputComponent],
      providers: [
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

    fixture = TestBed.createComponent(ChatInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
