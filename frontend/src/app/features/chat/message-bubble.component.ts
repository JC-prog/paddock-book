import { Component, Input } from '@angular/core';

import { ChatMessage } from './chat-message.model';

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [],
  template: `
    <div
      data-testid="message-bubble"
      [attr.data-sender]="message.sender"
      class="flex flex-col"
      [class.items-end]="message.sender === 'user'"
      [class.items-start]="message.sender === 'assistant'"
    >
      <p
        class="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-4 py-2 sm:max-w-[70%]"
        [class.bg-blue-600]="message.sender === 'user'"
        [class.text-white]="message.sender === 'user'"
        [class.bg-slate-200]="message.sender === 'assistant'"
        [class.text-slate-900]="message.sender === 'assistant'"
      >{{ message.text }}@if (isPending) {<span class="animate-pulse">&hellip;</span>}</p>
      @if (message.status === 'error') {
        <p data-testid="message-error" class="mt-1 text-xs text-red-600">Failed to get a response</p>
      }
    </div>
  `
})
export class MessageBubbleComponent {
  @Input({ required: true }) message!: ChatMessage;

  get isPending(): boolean {
    return this.message.sender === 'assistant' && this.message.status === 'streaming' && !this.message.text;
  }
}
