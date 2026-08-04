export type ChatMessageSender = 'user' | 'assistant';
export type ChatMessageStatus = 'complete' | 'streaming' | 'error';

export interface ChatMessage {
  id: string;
  text: string;
  sender: ChatMessageSender;
  status: ChatMessageStatus;
}
