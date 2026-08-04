import { Component } from '@angular/core';

import { ChatBoxComponent } from './chat-box.component';
import { ChatInputComponent } from './chat-input.component';

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [ChatBoxComponent, ChatInputComponent],
  host: { class: 'flex min-h-0 flex-1 flex-col' },
  template: `
    <app-chat-box></app-chat-box>
    <app-chat-input></app-chat-input>
  `
})
export class ChatPageComponent {}
