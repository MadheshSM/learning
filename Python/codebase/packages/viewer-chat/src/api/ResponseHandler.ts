/**
 * ResponseHandler - Orchestrates viewer actions and chat updates from API responses
 */

import { ViewerAPI, ViewerOperation, ViewerOperationResult } from '../viewer/ViewerAPI';
import { ChatInterface } from '../chat/ChatInterface';
import { MessageParser, ParsedResponse, ApiResponse } from '../chat/MessageParser';

export interface ResponseHandlerOptions {
  onViewerAction?: (operation: ViewerOperation, result: ViewerOperationResult) => void;
  onCharts?: (charts: any[]) => void;
  onData?: (data: any) => void;
  onError?: (error: Error) => void;
  executeOperationsSequentially?: boolean;
}

export class ResponseHandler {
  private viewerAPI: ViewerAPI;
  private chatInterface: ChatInterface;
  private messageParser: MessageParser;
  private options: ResponseHandlerOptions;

  constructor(
    viewerAPI: ViewerAPI,
    chatInterface: ChatInterface,
    messageParser: MessageParser,
    options: ResponseHandlerOptions = {}
  ) {
    this.viewerAPI = viewerAPI;
    this.chatInterface = chatInterface;
    this.messageParser = messageParser;
    this.options = {
      executeOperationsSequentially: true,
      ...options
    };
  }

  /**
   * Handle API response - parse, display message, and execute viewer operations
   */
  async handleResponse(response: ApiResponse): Promise<ParsedResponse> {
    // 1. Parse the response
    const parsed = this.messageParser.parse(response);

    // 2. Display message in chat
    if (parsed.message) {
      const messageType = parsed.success ? 'agent' : 'error';
      this.chatInterface.addMessage(parsed.message, messageType);
    }

    // 3. Execute viewer operations
    if (parsed.viewerOperations.length > 0) {
      await this.executeViewerOperations(parsed.viewerOperations);
    }

    // 4. Handle charts if callback is provided
    if (parsed.charts && parsed.charts.length > 0 && this.options.onCharts) {
      this.options.onCharts(parsed.charts);
    }

    // 5. Handle data if callback is provided
    if (parsed.data && this.options.onData) {
      this.options.onData(parsed.data);
    }

    // 6. Emit custom event for external handling
    this.emitEvent('response', parsed);

    return parsed;
  }

  /**
   * Handle error response
   */
  handleError(error: Error): void {
    this.chatInterface.addMessage(error.message, 'error');

    if (this.options.onError) {
      this.options.onError(error);
    }

    this.emitEvent('error', { error: error.message });
  }

  /**
   * Execute viewer operations
   */
  private async executeViewerOperations(operations: ViewerOperation[]): Promise<void> {
    if (this.options.executeOperationsSequentially) {
      // Execute sequentially
      for (const operation of operations) {
        await this.executeSingleOperation(operation);
      }
    } else {
      // Execute in parallel
      await Promise.all(
        operations.map((op) => this.executeSingleOperation(op))
      );
    }
  }

  /**
   * Execute a single viewer operation
   */
  private async executeSingleOperation(operation: ViewerOperation): Promise<ViewerOperationResult> {
    try {
      const result = await this.viewerAPI.execute(operation);

      // Call callback if provided
      if (this.options.onViewerAction) {
        this.options.onViewerAction(operation, result);
      }

      // Emit event
      this.emitEvent('viewerAction', { operation, result });

      if (!result.success) {
        console.warn(`Viewer operation failed: ${operation.type}`, result.error);
      }

      return result;
    } catch (error) {
      const errorResult: ViewerOperationResult = {
        success: false,
        error: (error as Error).message
      };

      if (this.options.onViewerAction) {
        this.options.onViewerAction(operation, errorResult);
      }

      return errorResult;
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

  /**
   * Update options
   */
  updateOptions(options: Partial<ResponseHandlerOptions>): void {
    this.options = { ...this.options, ...options };
  }
}
