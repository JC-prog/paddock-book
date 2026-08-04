import { TestBed } from '@angular/core/testing';

import { MessageBubbleComponent } from './message-bubble.component';

describe('MessageBubbleComponent', () => {
  it('renders the message text', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const fixture = TestBed.createComponent(MessageBubbleComponent);
    fixture.componentRef.setInput('message', {
      id: '1',
      text: 'hello there',
      sender: 'user',
      status: 'complete'
    });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('hello there');
  });

  it('preserves line breaks in a multi-line message', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const fixture = TestBed.createComponent(MessageBubbleComponent);
    fixture.componentRef.setInput('message', {
      id: '1',
      text: 'line one\nline two',
      sender: 'user',
      status: 'complete'
    });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('line one\nline two');
  });

  it('marks a user message and an assistant message differently', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const userFixture = TestBed.createComponent(MessageBubbleComponent);
    userFixture.componentRef.setInput('message', {
      id: '1',
      text: 'hi',
      sender: 'user',
      status: 'complete'
    });
    userFixture.detectChanges();

    const assistantFixture = TestBed.createComponent(MessageBubbleComponent);
    assistantFixture.componentRef.setInput('message', {
      id: '2',
      text: 'hello',
      sender: 'assistant',
      status: 'complete'
    });
    assistantFixture.detectChanges();

    const userBubble: HTMLElement = userFixture.nativeElement.querySelector('[data-testid="message-bubble"]');
    const assistantBubble: HTMLElement = assistantFixture.nativeElement.querySelector(
      '[data-testid="message-bubble"]'
    );

    expect(userBubble.getAttribute('data-sender')).toBe('user');
    expect(assistantBubble.getAttribute('data-sender')).toBe('assistant');
    expect(userBubble.className).not.toBe(assistantBubble.className);
  });

  it('shows a visible failure indication for an errored message', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const fixture = TestBed.createComponent(MessageBubbleComponent);
    fixture.componentRef.setInput('message', {
      id: '1',
      text: 'Hello,',
      sender: 'assistant',
      status: 'error'
    });
    fixture.detectChanges();

    const errorIndicator = fixture.nativeElement.querySelector('[data-testid="message-error"]');
    expect(errorIndicator).toBeTruthy();
    // Partial text must remain visible per FR-006.
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Hello,');
  });

  it('does not show a failure indication for a streaming or complete message', () => {
    TestBed.configureTestingModule({ imports: [MessageBubbleComponent] });

    const fixture = TestBed.createComponent(MessageBubbleComponent);
    fixture.componentRef.setInput('message', {
      id: '1',
      text: 'Hello,',
      sender: 'assistant',
      status: 'streaming'
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-testid="message-error"]')).toBeFalsy();
  });
});
