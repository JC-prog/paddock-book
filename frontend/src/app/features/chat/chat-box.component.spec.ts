import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { ChatBoxComponent } from './chat-box.component';
import { ChatService } from './chat.service';
import { ChatMessage } from './chat-message.model';

describe('ChatBoxComponent', () => {
  function setup(initialMessages: ChatMessage[]) {
    const messages = signal<ChatMessage[]>(initialMessages);
    const chatServiceStub: Partial<ChatService> = { messages };

    TestBed.configureTestingModule({
      imports: [ChatBoxComponent],
      providers: [{ provide: ChatService, useValue: chatServiceStub }]
    });

    const fixture = TestBed.createComponent(ChatBoxComponent);
    return { fixture, messages };
  }

  it('renders bubbles in the order messages were added', () => {
    const { fixture } = setup([
      { id: '1', text: 'first' },
      { id: '2', text: 'second' },
      { id: '3', text: 'third' }
    ]);

    fixture.detectChanges();

    const bubbles = (fixture.nativeElement as HTMLElement).querySelectorAll('app-message-bubble');
    expect(bubbles.length).toBe(3);
    expect(bubbles[0].textContent).toContain('first');
    expect(bubbles[1].textContent).toContain('second');
    expect(bubbles[2].textContent).toContain('third');
  });

  it('scrolls the container when a new message is added', async () => {
    const { fixture, messages } = setup([{ id: '1', text: 'first' }]);
    fixture.detectChanges();

    const container: HTMLElement = fixture.nativeElement.querySelector('[data-testid="chat-box-scroll"]');
    const scrollTopSpy = vi.spyOn(container, 'scrollTop', 'set');

    messages.set([...messages(), { id: '2', text: 'second' }]);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(scrollTopSpy).toHaveBeenCalled();
  });
});
