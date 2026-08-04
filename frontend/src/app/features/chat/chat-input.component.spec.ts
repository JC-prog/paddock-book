import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { ChatInputComponent } from './chat-input.component';
import { ChatService } from './chat.service';

describe('ChatInputComponent', () => {
  function setup(isSending = false) {
    const isSendingSignal = signal(isSending);
    const chatServiceSpy = {
      sendMessage: vi.fn(),
      isSending: isSendingSignal
    } satisfies Partial<ChatService>;

    TestBed.configureTestingModule({
      imports: [ChatInputComponent],
      providers: [{ provide: ChatService, useValue: chatServiceSpy }]
    });

    const fixture = TestBed.createComponent(ChatInputComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, chatServiceSpy, isSendingSignal };
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

  it('disables the send button and textarea while a reply is in flight', async () => {
    const { fixture } = setup(true);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('[data-testid="send-button"]');
    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');

    expect(button.disabled).toBe(true);
    expect(textarea.disabled).toBe(true);
  });

  it('does not send via Enter while a reply is in flight', () => {
    const { component, chatServiceSpy } = setup(true);
    component.draft = 'hello';

    component.onKeydown(enterEvent(false));

    expect(chatServiceSpy.sendMessage).not.toHaveBeenCalled();
  });

  it('does not send via the button while a reply is in flight', () => {
    const { fixture, component, chatServiceSpy } = setup(true);
    component.draft = 'hello';
    fixture.detectChanges();

    component.submit();

    expect(chatServiceSpy.sendMessage).not.toHaveBeenCalled();
  });

  it('re-enables sending once isSending becomes false', () => {
    const { fixture, isSendingSignal, component, chatServiceSpy } = setup(true);
    component.draft = 'hello';

    isSendingSignal.set(false);
    fixture.detectChanges();
    component.submit();

    expect(chatServiceSpy.sendMessage).toHaveBeenCalledWith('hello');
  });
});
