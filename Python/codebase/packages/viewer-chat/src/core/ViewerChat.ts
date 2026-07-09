/**
 * ViewerChat - Main widget class that combines Autodesk Viewer with AI Chat interface
 * This is the primary entry point for the @krion/viewer-chat package
 */

import { ViewerManager, ViewerOptions, ModelLoadOptions } from '../viewer/ViewerManager';
import { ViewerAPI, ViewerOperation, ViewerOperationResult } from '../viewer/ViewerAPI';
import { ViewerState, ViewerStateSnapshot } from '../viewer/ViewerState';
import { ChatInterface, ChatMessage } from '../chat/ChatInterface';
import { MessageParser } from '../chat/MessageParser';
import { ApiClient, QueryRequest, QueryResponse, ApiError } from '../api/ApiClient';
import { ResponseHandler } from '../api/ResponseHandler';

export interface ViewerChatConfig {
  // Container elements (required)
  viewerContainer: HTMLElement | string;
  chatContainer: HTMLElement | string;

  // API configuration (required)
  apiUrl: string;
  apiHeaders?: Record<string, string>;
  apiTimeout?: number;

  // Model configuration (optional)
  svfPath?: string;
  modelLoadOptions?: ModelLoadOptions;

  // Viewer configuration (optional)
  viewerOptions?: ViewerOptions;

  // Chat configuration (optional)
  theme?: 'light' | 'dark';
  chatPlaceholder?: string;
  sampleQueries?: string[];
  agentName?: string;
  userName?: string;

  // Project context (optional)
  projectId?: string;

  // State management (optional)
  enableStateHistory?: boolean;
  stateStorageKey?: string;

  // Callbacks (optional)
  onReady?: () => void;
  onError?: (error: Error) => void;
  onViewerAction?: (operation: ViewerOperation, result: ViewerOperationResult) => void;
  onMessage?: (message: ChatMessage) => void;
  onModelLoaded?: (model: Autodesk.Viewing.Model) => void;
  onCharts?: (charts: any[]) => void;
  onData?: (data: any) => void;
}

export class ViewerChat {
  // Components
  private viewerManager: ViewerManager;
  private viewerAPI: ViewerAPI;
  private viewerState: ViewerState;
  private chatInterface: ChatInterface;
  private apiClient: ApiClient;
  private responseHandler: ResponseHandler;
  private messageParser: MessageParser;

  // Config
  private config: ViewerChatConfig;

  // State
  private isInitialized: boolean = false;
  private isModelLoaded: boolean = false;

  constructor(config: ViewerChatConfig) {
    this.config = config;
    this.validateConfig();
    this.initialize();
  }

  /**
   * Validate configuration
   */
  private validateConfig(): void {
    if (!this.config.viewerContainer) {
      throw new Error('ViewerChat: viewerContainer is required');
    }
    if (!this.config.chatContainer) {
      throw new Error('ViewerChat: chatContainer is required');
    }
    if (!this.config.apiUrl) {
      throw new Error('ViewerChat: apiUrl is required');
    }
  }

  /**
   * Initialize the widget
   */
  private async initialize(): Promise<void> {
    try {
      // Get container elements
      const viewerEl = this.resolveContainer(this.config.viewerContainer);
      const chatEl = this.resolveContainer(this.config.chatContainer);

      if (!viewerEl || !chatEl) {
        throw new Error('ViewerChat: Could not find container elements');
      }

      // Initialize viewer
      this.viewerManager = new ViewerManager();
      await this.viewerManager.initialize(viewerEl, this.config.viewerOptions || {});

      this.viewerAPI = new ViewerAPI(this.viewerManager);
      this.viewerState = new ViewerState();

      // Load state from storage if enabled
      if (this.config.enableStateHistory && this.config.stateStorageKey) {
        this.viewerState.loadFromStorage(this.config.stateStorageKey);
      }

      // Load model if provided
      if (this.config.svfPath) {
        await this.loadModel(this.config.svfPath, this.config.modelLoadOptions);
      }

      // Initialize chat
      this.chatInterface = new ChatInterface({
        container: chatEl,
        onSubmit: (message) => this.handleUserMessage(message),
        theme: this.config.theme,
        placeholder: this.config.chatPlaceholder,
        sampleQueries: this.config.sampleQueries,
        agentName: this.config.agentName,
        userName: this.config.userName
      });

      // Initialize API client
      this.apiClient = new ApiClient({
        baseUrl: this.config.apiUrl,
        headers: this.config.apiHeaders,
        timeout: this.config.apiTimeout
      });

      // Initialize response handler
      this.messageParser = new MessageParser();
      this.responseHandler = new ResponseHandler(
        this.viewerAPI,
        this.chatInterface,
        this.messageParser,
        {
          onViewerAction: this.config.onViewerAction,
          onCharts: this.config.onCharts,
          onData: this.config.onData,
          onError: this.config.onError
        }
      );

      // Setup keyboard shortcuts
      this.setupKeyboardShortcuts();

      // Setup resize observer
      this.setupResizeObserver(viewerEl);

      this.isInitialized = true;

      // Emit ready event
      this.config.onReady?.();
      this.emitEvent('ready', { widget: this });

    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.config.onError?.(err);
      throw err;
    }
  }

  /**
   * Handle user message submission
   */
  private async handleUserMessage(message: string): Promise<void> {
    // Add user message to chat
    const userMsg = this.chatInterface.addMessage(message, 'user');
    this.config.onMessage?.(userMsg);

    // Show loading state
    this.chatInterface.setLoading(true);

    try {
      // Capture current viewer state for context
      const modelContext = this.buildModelContext();

      // Send to backend
      const response = await this.apiClient.query({
        query: message,
        project_id: this.config.projectId,
        model_context: modelContext
      });

      // Handle response
      const parsed = await this.responseHandler.handleResponse(response);

      // Capture state after successful operation (if viewer operations were executed)
      if (parsed.viewerOperations.length > 0 && this.config.enableStateHistory) {
        const viewer = this.viewerManager.getViewer();
        if (viewer) {
          this.viewerState.capture(viewer);
          if (this.config.stateStorageKey) {
            this.viewerState.saveToStorage(this.config.stateStorageKey);
          }
        }
      }

    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.responseHandler.handleError(err);
    } finally {
      this.chatInterface.setLoading(false);
    }
  }

  /**
   * Build model context for API requests
   */
  private buildModelContext(): QueryRequest['model_context'] {
    const viewer = this.viewerManager.getViewer();
    if (!viewer) return undefined;

    return {
      selected_ids: viewer.getSelection() || [],
      camera_state: this.viewerAPI.getCameraState(),
      model_path: this.config.svfPath
    };
  }

  /**
   * Resolve container from string selector or element
   */
  private resolveContainer(container: HTMLElement | string): HTMLElement | null {
    if (typeof container === 'string') {
      return document.querySelector(container);
    }
    return container;
  }

  /**
   * Setup keyboard shortcuts
   */
  private setupKeyboardShortcuts(): void {
    document.addEventListener('keydown', (e) => {
      // Ctrl+Z for undo
      if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
        const viewer = this.viewerManager.getViewer();
        if (viewer && this.viewerState.canUndo()) {
          e.preventDefault();
          this.viewerState.undo(viewer);
        }
      }

      // Ctrl+Shift+Z or Ctrl+Y for redo
      if ((e.ctrlKey && e.shiftKey && e.key === 'z') || (e.ctrlKey && e.key === 'y')) {
        const viewer = this.viewerManager.getViewer();
        if (viewer && this.viewerState.canRedo()) {
          e.preventDefault();
          this.viewerState.redo(viewer);
        }
      }

      // Escape to clear selection
      if (e.key === 'Escape') {
        this.viewerAPI.clearSelection();
      }
    });
  }

  /**
   * Setup resize observer for viewer
   */
  private setupResizeObserver(container: HTMLElement): void {
    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(() => {
        this.viewerManager.resize();
      });
      observer.observe(container);
    }
  }

  /**
   * Emit custom event
   */
  private emitEvent(type: string, detail: any): void {
    const event = new CustomEvent(`krion:${type}`, {
      detail,
      bubbles: true,
      cancelable: true
    });
    document.dispatchEvent(event);
  }

  // ============= PUBLIC API =============

  /**
   * Load a model from SVF path
   */
  async loadModel(svfPath: string, options?: ModelLoadOptions): Promise<Autodesk.Viewing.Model> {
    const model = await this.viewerManager.loadModel(svfPath, options);
    this.isModelLoaded = true;
    this.config.onModelLoaded?.(model);
    this.emitEvent('modelLoaded', { model, path: svfPath });
    return model;
  }

  /**
   * Unload current model
   */
  unloadModel(svfPath?: string): boolean {
    if (svfPath) {
      return this.viewerManager.unloadModel(svfPath);
    }
    this.viewerManager.unloadAllModels();
    this.isModelLoaded = false;
    return true;
  }

  /**
   * Execute a viewer operation programmatically
   */
  async executeViewerOperation(operation: ViewerOperation): Promise<ViewerOperationResult> {
    return this.viewerAPI.execute(operation);
  }

  /**
   * Send a message programmatically
   */
  sendMessage(message: string): void {
    this.handleUserMessage(message);
  }

  /**
   * Add a message to chat without sending to backend
   */
  addChatMessage(content: string, type: 'user' | 'agent' | 'system' | 'error'): ChatMessage {
    return this.chatInterface.addMessage(content, type);
  }

  /**
   * Clear chat messages
   */
  clearChat(): void {
    this.chatInterface.clearMessages();
  }

  /**
   * Get the Autodesk Viewer instance
   */
  getViewer(): Autodesk.Viewing.GuiViewer3D | null {
    return this.viewerManager.getViewer();
  }

  /**
   * Get the ViewerAPI instance for direct operations
   */
  getViewerAPI(): ViewerAPI {
    return this.viewerAPI;
  }

  /**
   * Get the ViewerManager instance
   */
  getViewerManager(): ViewerManager {
    return this.viewerManager;
  }

  /**
   * Get current selection
   */
  getSelection(): number[] {
    return this.viewerAPI.getSelection();
  }

  /**
   * Get chat messages
   */
  getChatMessages(): ChatMessage[] {
    return this.chatInterface.getMessages();
  }

  /**
   * Get viewer state history
   */
  getStateHistory(): ViewerStateSnapshot[] {
    return this.viewerState.getHistory();
  }

  /**
   * Undo viewer state
   */
  undo(): ViewerStateSnapshot | null {
    const viewer = this.viewerManager.getViewer();
    if (viewer) {
      return this.viewerState.undo(viewer);
    }
    return null;
  }

  /**
   * Redo viewer state
   */
  redo(): ViewerStateSnapshot | null {
    const viewer = this.viewerManager.getViewer();
    if (viewer) {
      return this.viewerState.redo(viewer);
    }
    return null;
  }

  /**
   * Check if undo is available
   */
  canUndo(): boolean {
    return this.viewerState.canUndo();
  }

  /**
   * Check if redo is available
   */
  canRedo(): boolean {
    return this.viewerState.canRedo();
  }

  /**
   * Set theme
   */
  setTheme(theme: 'light' | 'dark'): void {
    this.config.theme = theme;
    this.chatInterface.setTheme(theme);
  }

  /**
   * Update project ID
   */
  setProjectId(projectId: string): void {
    this.config.projectId = projectId;
  }

  /**
   * Take a screenshot
   */
  async getScreenshot(width?: number, height?: number): Promise<string> {
    return this.viewerManager.getScreenshot(width, height);
  }

  /**
   * Check if widget is ready
   */
  isReady(): boolean {
    return this.isInitialized;
  }

  /**
   * Check if model is loaded
   */
  hasModel(): boolean {
    return this.isModelLoaded;
  }

  /**
   * Focus the chat input
   */
  focusChat(): void {
    this.chatInterface.focus();
  }

  /**
   * Resize viewer
   */
  resize(): void {
    this.viewerManager.resize();
  }

  /**
   * Cancel pending API request
   */
  cancelRequest(): void {
    this.apiClient.cancel();
    this.chatInterface.setLoading(false);
  }

  /**
   * Destroy the widget and cleanup resources
   */
  destroy(): void {
    // Save state if enabled
    if (this.config.enableStateHistory && this.config.stateStorageKey) {
      this.viewerState.saveToStorage(this.config.stateStorageKey);
    }

    // Cancel pending requests
    this.apiClient.cancel();

    // Destroy components
    this.viewerManager.destroy();
    this.chatInterface.destroy();

    this.isInitialized = false;
    this.isModelLoaded = false;

    this.emitEvent('destroyed', {});
  }
}
