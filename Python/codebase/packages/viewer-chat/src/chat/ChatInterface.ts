/**
 * ChatInterface - Chat UI component for viewer chat widget
 * Mirrors the existing ACC Dashboard chat design
 */

export interface ChatInterfaceOptions {
  container: HTMLElement;
  onSubmit: (message: string) => void;
  theme?: 'light' | 'dark';
  placeholder?: string;
  sampleQueries?: string[];
  agentName?: string;
  userName?: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'agent' | 'system' | 'error';
  timestamp: Date;
}

export class ChatInterface {
  private container: HTMLElement;
  private messagesContainer: HTMLElement | null = null;
  private inputElement: HTMLInputElement | null = null;
  private sendButton: HTMLButtonElement | null = null;
  private loadingIndicator: HTMLElement | null = null;
  private emptyState: HTMLElement | null = null;
  private options: ChatInterfaceOptions;
  private messages: ChatMessage[] = [];
  private isLoading: boolean = false;

  constructor(options: ChatInterfaceOptions) {
    this.options = {
      theme: 'light',
      placeholder: 'Ask about the model...',
      agentName: 'Agent',
      userName: 'You',
      ...options
    };
    this.container = options.container;
    this.render();
    this.bindEvents();
  }

  /**
   * Render the chat interface
   */
  private render(): void {
    const theme = this.options.theme === 'dark' ? 'krion-chat--dark' : 'krion-chat--light';

    this.container.innerHTML = `
      <div class="krion-chat ${theme}">
        <div class="krion-chat__header">
          <div class="krion-chat__header-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="20" height="20">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z">
              </path>
            </svg>
          </div>
          <span class="krion-chat__header-title">Model Chat</span>
        </div>

        <div class="krion-chat__messages" id="krion-chat-messages">
          <div class="krion-chat__empty-state" id="krion-chat-empty">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="48" height="48">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z">
              </path>
            </svg>
            <p>Ask a question about the model to get started</p>
          </div>
        </div>

        <div class="krion-chat__loading" id="krion-chat-loading" style="display: none;">
          <div class="krion-chat__loading-dots">
            <span></span><span></span><span></span>
          </div>
          <span>Processing...</span>
        </div>

        ${this.renderSampleQueries()}

        <div class="krion-chat__input-area">
          <div class="krion-chat__input-wrapper">
            <input
              type="text"
              class="krion-chat__input"
              id="krion-chat-input"
              placeholder="${this.escapeHtml(this.options.placeholder!)}"
              autocomplete="off"
            />
            <button class="krion-chat__send-btn" id="krion-chat-send" type="button">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="20" height="20">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8">
                </path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;

    // Cache element references
    this.messagesContainer = this.container.querySelector('#krion-chat-messages');
    this.inputElement = this.container.querySelector('#krion-chat-input');
    this.sendButton = this.container.querySelector('#krion-chat-send');
    this.loadingIndicator = this.container.querySelector('#krion-chat-loading');
    this.emptyState = this.container.querySelector('#krion-chat-empty');
  }

  /**
   * Render sample queries dropdown
   */
  private renderSampleQueries(): string {
    if (!this.options.sampleQueries || this.options.sampleQueries.length === 0) {
      return '';
    }

    const queryItems = this.options.sampleQueries
      .map((query) => `<button class="krion-chat__sample-query" type="button">${this.escapeHtml(query)}</button>`)
      .join('');

    return `
      <div class="krion-chat__samples">
        <span class="krion-chat__samples-label">Try asking:</span>
        <div class="krion-chat__samples-list">
          ${queryItems}
        </div>
      </div>
    `;
  }

  /**
   * Bind event listeners
   */
  private bindEvents(): void {
    // Send button click
    this.sendButton?.addEventListener('click', () => this.handleSubmit());

    // Enter key press
    this.inputElement?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSubmit();
      }
    });

    // Sample query clicks
    const sampleButtons = this.container.querySelectorAll('.krion-chat__sample-query');
    sampleButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const query = btn.textContent?.trim();
        if (query && this.inputElement) {
          this.inputElement.value = query;
          this.handleSubmit();
        }
      });
    });
  }

  /**
   * Handle message submit
   */
  private handleSubmit(): void {
    if (this.isLoading) return;

    const message = this.inputElement?.value.trim();
    if (!message) return;

    // Clear input
    if (this.inputElement) {
      this.inputElement.value = '';
    }

    // Call submit callback
    this.options.onSubmit(message);
  }

  /**
   * Add a message to the chat
   */
  addMessage(content: string, type: 'user' | 'agent' | 'system' | 'error'): ChatMessage {
    // Hide empty state
    if (this.emptyState) {
      this.emptyState.style.display = 'none';
    }

    const message: ChatMessage = {
      id: this.generateId(),
      content,
      type,
      timestamp: new Date()
    };

    this.messages.push(message);
    this.renderMessage(message);
    this.scrollToBottom();

    return message;
  }

  /**
   * Render a single message
   */
  private renderMessage(message: ChatMessage): void {
    if (!this.messagesContainer) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `krion-chat__message krion-chat__message--${message.type}`;
    messageDiv.dataset.messageId = message.id;

    if (message.type === 'user') {
      messageDiv.innerHTML = `
        <div class="krion-chat__message-wrapper">
          <span class="krion-chat__message-label">${this.escapeHtml(this.options.userName!)}</span>
          <div class="krion-chat__bubble">
            <p>${this.escapeHtml(message.content)}</p>
          </div>
        </div>
      `;
    } else if (message.type === 'agent') {
      const formatted = this.formatAgentMessage(message.content);
      messageDiv.innerHTML = `
        <div class="krion-chat__avatar">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z">
            </path>
          </svg>
        </div>
        <div class="krion-chat__message-wrapper">
          <span class="krion-chat__message-label">${this.escapeHtml(this.options.agentName!)}</span>
          <div class="krion-chat__bubble">
            <p>${formatted}</p>
          </div>
        </div>
      `;
    } else if (message.type === 'error') {
      messageDiv.innerHTML = `
        <div class="krion-chat__message-wrapper">
          <div class="krion-chat__bubble krion-chat__bubble--error">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="16" height="16">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z">
              </path>
            </svg>
            <p>${this.escapeHtml(message.content)}</p>
          </div>
        </div>
      `;
    } else if (message.type === 'system') {
      messageDiv.innerHTML = `
        <div class="krion-chat__message-wrapper">
          <div class="krion-chat__bubble krion-chat__bubble--system">
            <p>${this.escapeHtml(message.content)}</p>
          </div>
        </div>
      `;
    }

    this.messagesContainer.appendChild(messageDiv);
  }

  /**
   * Format agent message with markdown-like styling
   */
  private formatAgentMessage(content: string): string {
    return String(content)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
  }

  /**
   * Set loading state
   */
  setLoading(loading: boolean): void {
    this.isLoading = loading;

    if (this.loadingIndicator) {
      this.loadingIndicator.style.display = loading ? 'flex' : 'none';
    }

    if (this.inputElement) {
      this.inputElement.disabled = loading;
    }

    if (this.sendButton) {
      this.sendButton.disabled = loading;
    }
  }

  /**
   * Clear all messages
   */
  clearMessages(): void {
    this.messages = [];
    if (this.messagesContainer) {
      // Remove all message elements but keep empty state
      const messageElements = this.messagesContainer.querySelectorAll('.krion-chat__message');
      messageElements.forEach((el) => el.remove());
    }

    // Show empty state
    if (this.emptyState) {
      this.emptyState.style.display = 'flex';
    }
  }

  /**
   * Get all messages
   */
  getMessages(): ChatMessage[] {
    return [...this.messages];
  }

  /**
   * Focus the input field
   */
  focus(): void {
    this.inputElement?.focus();
  }

  /**
   * Set input value
   */
  setInputValue(value: string): void {
    if (this.inputElement) {
      this.inputElement.value = value;
    }
  }

  /**
   * Scroll to bottom of messages
   */
  private scrollToBottom(): void {
    if (this.messagesContainer) {
      setTimeout(() => {
        this.messagesContainer!.scrollTop = this.messagesContainer!.scrollHeight;
      }, 50);
    }
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Update theme
   */
  setTheme(theme: 'light' | 'dark'): void {
    this.options.theme = theme;
    const chatEl = this.container.querySelector('.krion-chat');
    if (chatEl) {
      chatEl.classList.remove('krion-chat--light', 'krion-chat--dark');
      chatEl.classList.add(`krion-chat--${theme}`);
    }
  }

  /**
   * Destroy the chat interface
   */
  destroy(): void {
    this.container.innerHTML = '';
    this.messages = [];
    this.messagesContainer = null;
    this.inputElement = null;
    this.sendButton = null;
    this.loadingIndicator = null;
    this.emptyState = null;
  }
}
