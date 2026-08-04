import { TestBed } from '@angular/core/testing';

import { MessageBubbleComponent } from './message-bubble.component';

describe('MessageBubbleComponent', () => {
  it('renders the message text', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const fixture = TestBed.createComponent(MessageBubbleComponent);
    fixture.componentRef.setInput('message', { id: '1', text: 'hello there' });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('hello there');
  });

  it('preserves line breaks in a multi-line message', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const fixture = TestBed.createComponent(MessageBubbleComponent);
    fixture.componentRef.setInput('message', { id: '1', text: 'line one\nline two' });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('line one\nline two');
  });
});
