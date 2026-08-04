import { TestBed } from '@angular/core/testing';

import { ChatService } from './chat.service';

describe('ChatService', () => {
  let service: ChatService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [ChatService] });
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

  it('appends a trimmed message for valid text', () => {
    service.sendMessage('  hello  ');

    expect(service.messages().length).toBe(1);
    expect(service.messages()[0].text).toBe('hello');
  });

  it('preserves the order messages were sent in', () => {
    service.sendMessage('first');
    service.sendMessage('second');
    service.sendMessage('third');

    expect(service.messages().map((m) => m.text)).toEqual(['first', 'second', 'third']);
  });

  it('assigns each message a unique id', () => {
    service.sendMessage('first');
    service.sendMessage('second');

    const [first, second] = service.messages();
    expect(first.id).not.toBe(second.id);
  });
});
