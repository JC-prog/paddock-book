import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ChatService } from './chat.service';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="flex items-end gap-2 border-t border-slate-200 bg-white px-4 py-3 sm:px-6">
      <textarea
        [(ngModel)]="draft"
        (keydown)="onKeydown($event)"
        rows="1"
        placeholder="Type a message..."
        class="max-h-32 flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      ></textarea>
      <button
        type="button"
        data-testid="send-button"
        (click)="submit()"
        class="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >Send</button>
    </div>
  `
})
export class ChatInputComponent {
  private readonly chatService = inject(ChatService);

  draft = '';

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.submit();
    }
  }

  submit(): void {
    const trimmed = this.draft.trim();
    if (!trimmed) {
      return;
    }

    this.chatService.sendMessage(trimmed);
    this.draft = '';
  }
}
