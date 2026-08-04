import { Injectable, inject, signal } from '@angular/core';

import { ChatApiService } from './chat-api.service';
import { ChatMessage } from './chat-message.model';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly chatApiService = inject(ChatApiService);

  private readonly _messages = signal<ChatMessage[]>([]);
  readonly messages = this._messages.asReadonly();

  private readonly _isSending = signal(false);
  readonly isSending = this._isSending.asReadonly();

  sendMessage(text: string): void {
    const trimmed = text.trim();
    if (!trimmed || this._isSending()) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      text: trimmed,
      sender: 'user',
      status: 'complete'
    };
    const assistantMessageId = crypto.randomUUID();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      text: '',
      sender: 'assistant',
      status: 'streaming'
    };

    this._messages.update((messages) => [...messages, userMessage, assistantMessage]);
    this._isSending.set(true);

    this.chatApiService.streamReply(trimmed).subscribe({
      next: (word) => this.appendWord(assistantMessageId, word),
      complete: () => {
        this.finalizeMessage(assistantMessageId, 'complete');
        this._isSending.set(false);
      },
      error: () => {
        this.finalizeMessage(assistantMessageId, 'error');
        this._isSending.set(false);
      }
    });
  }

  private appendWord(messageId: string, word: string): void {
    this._messages.update((messages) =>
      messages.map((message) =>
        message.id === messageId
          ? { ...message, text: message.text ? `${message.text} ${word}` : word }
          : message
      )
    );
  }

  private finalizeMessage(messageId: string, status: 'complete' | 'error'): void {
    this._messages.update((messages) =>
      messages.map((message) => (message.id === messageId ? { ...message, status } : message))
    );
  }
}
