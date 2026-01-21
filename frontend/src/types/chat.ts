export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  requestId?: string | null;
}
