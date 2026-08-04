import { Component, Input } from '@angular/core';

import { ChatMessage } from './chat-message.model';

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [],
  template: `
    <p
      class="max-w-[85%] self-end whitespace-pre-wrap break-words rounded-2xl bg-blue-600 px-4 py-2 text-white sm:max-w-[70%]"
    >{{ message.text }}</p>
  `
})
export class MessageBubbleComponent {
  @Input({ required: true }) message!: ChatMessage;
}
