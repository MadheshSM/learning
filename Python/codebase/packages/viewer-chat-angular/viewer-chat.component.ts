import { Component, OnInit, OnDestroy, Input, ViewChild, ElementRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { ChatApiService, ViewerAction } from './chat-api.service';
import { ViewerActionExecutorService } from './viewer-action-executor.service';

interface ChatMessage {
  content: string;
  type: 'user' | 'agent';
  timestamp: Date;
  actions?: ViewerAction[];
}

@Component({
  selector: 'app-viewer-chat',
  template: `
    <div class="viewer-chat-container" [class.dark]="darkMode">
      <!-- Header -->
      <div class="chat-header">
        <div class="header-left">
          <svg class="header-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          <span class="header-title">Model Assistant</span>
        </div>
        <div class="header-right">
          <span class="status-dot" [class.connected]="isConnected"></span>
          <span class="status-text">{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
        </div>
      </div>

      <!-- Messages -->
      <div #messagesContainer class="chat-messages">
        <!-- Empty State -->
        <div *ngIf="messages.length === 0" class="empty-state">
          <div class="empty-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
            </svg>
          </div>
          <h3>Control the 3D Model</h3>
          <p>Ask me to show, hide, isolate elements, change views, create sections, and more.</p>
          <div class="example-queries">
            <button *ngFor="let example of exampleQueries" (click)="sendMessage(example)" class="example-btn">
              {{ example }}
            </button>
          </div>
        </div>

        <!-- Message List -->
        <div *ngFor="let msg of messages" class="chat-message" [class.user]="msg.type === 'user'" [class.agent]="msg.type === 'agent'">
          <div *ngIf="msg.type === 'agent'" class="agent-avatar">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
          </div>
          <div class="message-wrapper">
            <span class="message-label">{{ msg.type === 'user' ? 'You' : 'Agent' }}</span>
            <div class="chat-bubble" [innerHTML]="formatMessage(msg.content)"></div>
            <div *ngIf="msg.actions?.length" class="actions-badge">
              {{ msg.actions.length }} action(s) executed
            </div>
          </div>
        </div>

        <!-- Loading Indicator -->
        <div *ngIf="isLoading" class="chat-message agent">
          <div class="agent-avatar">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
          </div>
          <div class="message-wrapper">
            <span class="message-label">Agent</span>
            <div class="chat-bubble typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="chat-input-area">
        <input
          type="text"
          [(ngModel)]="inputValue"
          (keypress)="onKeyPress($event)"
          placeholder="Ask about the model..."
          [disabled]="isLoading"
          #chatInput
        />
        <button
          (click)="sendMessage()"
          [disabled]="isLoading || !inputValue.trim()"
          class="send-btn"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
          </svg>
        </button>
      </div>
    </div>
  `,
  styles: [`
    .viewer-chat-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Dark Mode */
    .viewer-chat-container.dark {
      background: #1f2937;
      color: #f9fafb;
    }

    /* Header */
    .chat-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem;
      border-bottom: 1px solid #e5e7eb;
      background: #f9fafb;
    }

    .dark .chat-header {
      background: #111827;
      border-color: #374151;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .header-icon {
      width: 24px;
      height: 24px;
      color: #3b82f6;
    }

    .header-title {
      font-weight: 600;
      font-size: 1rem;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      color: #6b7280;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #9ca3af;
    }

    .status-dot.connected {
      background: #10b981;
    }

    /* Messages Container */
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
    }

    /* Empty State */
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2rem;
      color: #6b7280;
    }

    .empty-icon {
      width: 64px;
      height: 64px;
      margin-bottom: 1rem;
      color: #d1d5db;
    }

    .empty-icon svg {
      width: 100%;
      height: 100%;
    }

    .empty-state h3 {
      margin: 0 0 0.5rem;
      font-size: 1.125rem;
      font-weight: 600;
      color: #374151;
    }

    .dark .empty-state h3 {
      color: #e5e7eb;
    }

    .empty-state p {
      margin: 0 0 1.5rem;
      font-size: 0.875rem;
    }

    .example-queries {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      justify-content: center;
    }

    .example-btn {
      padding: 0.5rem 0.75rem;
      font-size: 0.75rem;
      border: 1px solid #d1d5db;
      border-radius: 1rem;
      background: white;
      color: #374151;
      cursor: pointer;
      transition: all 0.15s;
    }

    .example-btn:hover {
      border-color: #3b82f6;
      color: #3b82f6;
    }

    .dark .example-btn {
      background: #374151;
      border-color: #4b5563;
      color: #e5e7eb;
    }

    /* Messages */
    .chat-message {
      display: flex;
      margin-bottom: 1rem;
      gap: 0.75rem;
    }

    .chat-message.user {
      justify-content: flex-end;
    }

    .chat-message.agent {
      justify-content: flex-start;
    }

    .agent-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #eff6ff;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .agent-avatar svg {
      width: 18px;
      height: 18px;
      color: #3b82f6;
    }

    .dark .agent-avatar {
      background: #1e3a5f;
    }

    .message-wrapper {
      max-width: 80%;
    }

    .message-label {
      display: block;
      font-size: 0.75rem;
      color: #6b7280;
      margin-bottom: 0.25rem;
    }

    .chat-message.user .message-label {
      text-align: right;
    }

    .chat-bubble {
      padding: 0.75rem 1rem;
      border-radius: 1rem;
      line-height: 1.5;
      font-size: 0.875rem;
    }

    .chat-message.user .chat-bubble {
      background: #3b82f6;
      color: white;
      border-bottom-right-radius: 0.25rem;
    }

    .chat-message.agent .chat-bubble {
      background: #f3f4f6;
      color: #1f2937;
      border-bottom-left-radius: 0.25rem;
    }

    .dark .chat-message.agent .chat-bubble {
      background: #374151;
      color: #f9fafb;
    }

    .actions-badge {
      font-size: 0.675rem;
      color: #10b981;
      margin-top: 0.25rem;
    }

    /* Typing Indicator */
    .chat-bubble.typing {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 1rem;
    }

    .chat-bubble.typing span {
      width: 8px;
      height: 8px;
      background: #9ca3af;
      border-radius: 50%;
      animation: bounce 1.4s infinite ease-in-out;
    }

    .chat-bubble.typing span:nth-child(1) { animation-delay: -0.32s; }
    .chat-bubble.typing span:nth-child(2) { animation-delay: -0.16s; }

    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }

    /* Input Area */
    .chat-input-area {
      display: flex;
      gap: 0.5rem;
      padding: 1rem;
      border-top: 1px solid #e5e7eb;
      background: #f9fafb;
    }

    .dark .chat-input-area {
      background: #111827;
      border-color: #374151;
    }

    .chat-input-area input {
      flex: 1;
      padding: 0.75rem 1rem;
      border: 1px solid #d1d5db;
      border-radius: 0.5rem;
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    .chat-input-area input:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    .dark .chat-input-area input {
      background: #374151;
      border-color: #4b5563;
      color: #f9fafb;
    }

    .send-btn {
      width: 44px;
      height: 44px;
      border: none;
      border-radius: 0.5rem;
      background: #3b82f6;
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }

    .send-btn:hover:not(:disabled) {
      background: #2563eb;
    }

    .send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .send-btn svg {
      width: 20px;
      height: 20px;
    }
  `]
})
export class ViewerChatComponent implements OnInit, OnDestroy {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('chatInput') chatInput!: ElementRef;

  /** API URL for the backend */
  @Input() apiUrl: string = 'http://localhost:8080';

  /** Enable dark mode */
  @Input() darkMode: boolean = false;

  /** Example queries shown in empty state */
  @Input() exampleQueries: string[] = [
    'Show walls',
    'Top view',
    'Isolate doors',
    'Explode model',
    'Create section'
  ];

  messages: ChatMessage[] = [];
  inputValue: string = '';
  isLoading: boolean = false;
  isConnected: boolean = false;

  private subscription = new Subscription();

  constructor(
    private chatApiService: ChatApiService,
    private viewerActionExecutor: ViewerActionExecutorService
  ) {}

  ngOnInit(): void {
    // Set API URL
    this.chatApiService.setApiUrl(this.apiUrl);

    // Check backend health
    this.checkConnection();
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  /**
   * Set the viewer instance for executing actions
   */
  setViewer(viewer: any): void {
    this.viewerActionExecutor.setViewer(viewer);
  }

  /**
   * Send a message to the backend
   */
  async sendMessage(message?: string): Promise<void> {
    const content = message || this.inputValue.trim();
    if (!content || this.isLoading) return;

    // Clear input
    this.inputValue = '';

    // Add user message
    this.addMessage(content, 'user');

    // Set loading
    this.isLoading = true;

    try {
      // Get selected elements from viewer
      const viewer = this.viewerActionExecutor.getViewer();
      const selectedIds = viewer?.getSelection() || [];

      // Send query
      const response = await this.chatApiService.sendQuery(content, {
        selectedIds
      }).toPromise();

      // Add agent response
      this.addMessage(
        response?.message || 'Operation completed.',
        'agent',
        response?.viewer_actions
      );

      // Execute viewer actions
      if (response?.viewer_actions?.length) {
        await this.viewerActionExecutor.executeActions(response.viewer_actions);
      }

    } catch (error: any) {
      console.error('Chat error:', error);
      this.addMessage(
        `Error: ${error.message || 'Failed to process request'}`,
        'agent'
      );
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Handle key press in input
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  /**
   * Format message content (basic markdown support)
   */
  formatMessage(content: string): string {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  private addMessage(content: string, type: 'user' | 'agent', actions?: ViewerAction[]): void {
    this.messages.push({
      content,
      type,
      timestamp: new Date(),
      actions
    });

    // Scroll to bottom
    setTimeout(() => {
      if (this.messagesContainer) {
        const el = this.messagesContainer.nativeElement;
        el.scrollTop = el.scrollHeight;
      }
    });
  }

  private checkConnection(): void {
    this.chatApiService.checkHealth().subscribe({
      next: () => this.isConnected = true,
      error: () => this.isConnected = false
    });
  }
}
