import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { provideRouter } from '@angular/router';

import { SidebarComponent } from './sidebar.component';
import { fetchApiMockProvider } from '../utils/fetch-mock-provider.test-util';

describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent],
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

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
