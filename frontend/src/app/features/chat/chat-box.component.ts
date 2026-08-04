import { Component, ElementRef, ViewChild, effect, inject } from '@angular/core';

import { ChatService } from './chat.service';
import { MessageBubbleComponent } from './message-bubble.component';

@Component({
  selector: 'app-chat-box',
  standalone: true,
  imports: [MessageBubbleComponent],
  host: { class: 'flex min-h-0 flex-1 flex-col' },
  template: `
    <div
      #scrollContainer
      data-testid="chat-box-scroll"
      class="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6"
    >
      <div class="flex flex-col gap-2">
        @for (message of chatService.messages(); track message.id) {
          <app-message-bubble [message]="message" />
        }
      </div>
    </div>
  `
})
export class ChatBoxComponent {
  protected readonly chatService = inject(ChatService);

  @ViewChild('scrollContainer') private scrollContainerRef?: ElementRef<HTMLElement>;

  constructor() {
    effect(() => {
      this.chatService.messages();
      const el = this.scrollContainerRef?.nativeElement;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }
}
