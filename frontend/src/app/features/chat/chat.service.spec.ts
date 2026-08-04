import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';

import { ChatService } from './chat.service';
import { ChatApiService } from './chat-api.service';

describe('ChatService', () => {
  let service: ChatService;
  let reply$: Subject<string>;
  let chatApiServiceStub: Partial<ChatApiService>;

  beforeEach(() => {
    reply$ = new Subject<string>();
    chatApiServiceStub = { streamReply: () => reply$.asObservable() };

    TestBed.configureTestingModule({
      providers: [ChatService, { provide: ChatApiService, useValue: chatApiServiceStub }]
    });
    service = TestBed.inject(ChatService);
  });

  it('starts with no messages', () => {
    expect(service.messages()).toEqual([]);
  });

  it('does not add a message for empty text', () => {
    service.sendMessage('');

    expect(service.messages().length).toBe(0);
  });

  it('does not add a message for whitespace-only text', () => {
    service.sendMessage('   \n  ');

    expect(service.messages().length).toBe(0);
  });

  it('appends a trimmed, complete user message for valid text', () => {
    service.sendMessage('  hello  ');

    const [userMessage] = service.messages();
    expect(userMessage.text).toBe('hello');
    expect(userMessage.sender).toBe('user');
    expect(userMessage.status).toBe('complete');
  });

  it('appends a streaming assistant message alongside the user message', () => {
    service.sendMessage('hi');

    expect(service.messages().length).toBe(2);
    const [, assistantMessage] = service.messages();
    expect(assistantMessage.sender).toBe('assistant');
    expect(assistantMessage.status).toBe('streaming');
    expect(assistantMessage.text).toBe('');
  });

  it('grows the assistant message text as words arrive', () => {
    service.sendMessage('hi');

    reply$.next('Hello,');
    reply$.next('there');

    const [, assistantMessage] = service.messages();
    expect(assistantMessage.text).toBe('Hello, there');
  });

  it('marks the assistant message complete when the stream ends cleanly', () => {
    service.sendMessage('hi');
    reply$.next('Hello,');
    reply$.complete();

    const [, assistantMessage] = service.messages();
    expect(assistantMessage.status).toBe('complete');
  });

  it('marks the assistant message as error when the stream errors, keeping partial text', () => {
    service.sendMessage('hi');
    reply$.next('Hello,');
    reply$.error(new Error('dropped'));

    const [, assistantMessage] = service.messages();
    expect(assistantMessage.status).toBe('error');
    expect(assistantMessage.text).toBe('Hello,');
  });

  it('assigns the user and assistant messages distinct ids', () => {
    service.sendMessage('hi');

    const [userMessage, assistantMessage] = service.messages();
    expect(userMessage.id).not.toBe(assistantMessage.id);
  });

  it('sets isSending true while a reply is in flight and false once it completes', () => {
    expect(service.isSending()).toBe(false);

    service.sendMessage('hi');
    expect(service.isSending()).toBe(true);

    reply$.complete();
    expect(service.isSending()).toBe(false);
  });

  it('sets isSending false once a reply errors', () => {
    service.sendMessage('hi');
    reply$.error(new Error('dropped'));

    expect(service.isSending()).toBe(false);
  });

  it('does not start a new exchange while a reply is still in flight', () => {
    service.sendMessage('first');
    service.sendMessage('second');

    const userMessages = service.messages().filter((m) => m.sender === 'user');
    expect(userMessages.length).toBe(1);
    expect(userMessages[0].text).toBe('first');
  });

  it('allows sending again once the previous reply has completed', () => {
    service.sendMessage('first');
    reply$.complete();

    reply$ = new Subject<string>();
    chatApiServiceStub.streamReply = () => reply$.asObservable();
    service.sendMessage('second');

    const userMessages = service.messages().filter((m) => m.sender === 'user');
    expect(userMessages.map((m) => m.text)).toEqual(['first', 'second']);
  });
});
