import { TestBed } from '@angular/core/testing';

import { ChatInputComponent } from './chat-input.component';
import { ChatService } from './chat.service';

describe('ChatInputComponent', () => {
  function setup() {
    const chatServiceSpy = { sendMessage: vi.fn() } satisfies Partial<ChatService>;

    TestBed.configureTestingModule({
      imports: [ChatInputComponent],
      providers: [{ provide: ChatService, useValue: chatServiceSpy }]
    });

    const fixture = TestBed.createComponent(ChatInputComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, chatServiceSpy };
  }

  function enterEvent(shiftKey: boolean): KeyboardEvent {
    return new KeyboardEvent('keydown', { key: 'Enter', shiftKey });
  }

  it('sends the message and clears the textbox on Enter (no shift)', () => {
    const { component, chatServiceSpy } = setup();
    component.draft = 'hello';

    const event = enterEvent(false);
    vi.spyOn(event, 'preventDefault');
    component.onKeydown(event);

    expect(event.preventDefault).toHaveBeenCalled();
    expect(chatServiceSpy.sendMessage).toHaveBeenCalledWith('hello');
    expect(component.draft).toBe('');
  });

  it('inserts a newline instead of sending on Shift+Enter', () => {
    const { component, chatServiceSpy } = setup();
    component.draft = 'hello';

    const event = enterEvent(true);
    vi.spyOn(event, 'preventDefault');
    component.onKeydown(event);

    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(chatServiceSpy.sendMessage).not.toHaveBeenCalled();
    expect(component.draft).toBe('hello');
  });

  it('sends the message via the send button', () => {
    const { fixture, component, chatServiceSpy } = setup();
    component.draft = 'via button';
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('[data-testid="send-button"]');
    button.click();

    expect(chatServiceSpy.sendMessage).toHaveBeenCalledWith('via button');
    expect(component.draft).toBe('');
  });

  it('does not send or clear the textbox for empty/whitespace-only text', () => {
    const { component, chatServiceSpy } = setup();
    component.draft = '   ';

    const event = enterEvent(false);
    vi.spyOn(event, 'preventDefault');
    component.onKeydown(event);

    expect(chatServiceSpy.sendMessage).not.toHaveBeenCalled();
    expect(component.draft).toBe('   ');
  });
});
