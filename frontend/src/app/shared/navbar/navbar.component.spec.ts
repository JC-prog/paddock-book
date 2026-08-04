import { TestBed } from '@angular/core/testing';

import { NavbarComponent } from './navbar.component';

describe('NavbarComponent', () => {
  it('renders the application branding', () => {
    TestBed.configureTestingModule({
      imports: [NavbarComponent]
    });

    const fixture = TestBed.createComponent(NavbarComponent);
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('PaddockBook');
  });
});
