import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';

import { QueryComponent } from './query.component';
import { Query } from '../../../../model';

describe('QueryComponent', () => {
  let component: QueryComponent;
  let fixture: ComponentFixture<QueryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QueryComponent],
      providers: [
        provideHttpClient(),
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

    fixture = TestBed.createComponent(QueryComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('query', new Query({}));
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
