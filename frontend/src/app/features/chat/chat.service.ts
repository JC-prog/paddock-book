import { Injectable, signal } from '@angular/core';

import { ChatMessage } from './chat-message.model';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly _messages = signal<ChatMessage[]>([]);
  readonly messages = this._messages.asReadonly();

  sendMessage(text: string): void {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }

    this._messages.update((messages) => [...messages, { id: crypto.randomUUID(), text: trimmed }]);
  }
}
