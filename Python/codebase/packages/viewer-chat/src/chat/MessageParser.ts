/**
 * MessageParser - Extracts viewer operations and data from API responses
 */

import { ViewerOperation } from '../viewer/ViewerAPI';

export interface ParsedResponse {
  message: string;
  viewerOperations: ViewerOperation[];
  charts?: any[];
  data?: any;
  success: boolean;
  error?: string;
  metadata?: {
    agentsUsed?: string[];
    routing?: any;
    interactionSummary?: any;
  };
}

export interface ApiResponse {
  success: boolean;
  message?: string;
  response?: string;
  data?: any;
  charts?: any[];
  viewer_actions?: ViewerAction[];
  agents_used?: string[];
  routing?: any;
  interaction_logs?: any[];
  interaction_summary?: any;
  error?: string;
}

export interface ViewerAction {
  operation: string;
  params?: Record<string, any>;
  description?: string;
}

export class MessageParser {
  /**
   * Parse API response to extract viewer operations and message
   */
  parse(response: ApiResponse): ParsedResponse {
    const result: ParsedResponse = {
      message: this.extractMessage(response),
      viewerOperations: this.extractViewerOperations(response),
      charts: response.charts || [],
      data: response.data,
      success: response.success ?? true,
      error: response.error,
      metadata: {
        agentsUsed: response.agents_used,
        routing: response.routing,
        interactionSummary: response.interaction_summary
      }
    };

    return result;
  }

  /**
   * Extract message text from response
   */
  private extractMessage(response: ApiResponse): string {
    // Try different message fields
    if (response.message) {
      return response.message;
    }
    if (response.response) {
      return response.response;
    }
    if (response.error) {
      return `Error: ${response.error}`;
    }
    if (!response.success) {
      return 'An error occurred while processing your request.';
    }
    return 'Request processed successfully.';
  }

  /**
   * Extract viewer operations from response
   */
  private extractViewerOperations(response: ApiResponse): ViewerOperation[] {
    const operations: ViewerOperation[] = [];

    // Check for explicit viewer_actions array
    if (response.viewer_actions && Array.isArray(response.viewer_actions)) {
      for (const action of response.viewer_actions) {
        if (action.operation) {
          operations.push({
            type: action.operation,
            params: action.params || {}
          });
        }
      }
    }

    // Also check in data if it contains viewer operations
    if (response.data && typeof response.data === 'object') {
      // Handle case where data contains a single operation
      if (response.data.operation) {
        operations.push({
          type: response.data.operation,
          params: response.data.params || {}
        });
      }

      // Handle case where data is an array of operations
      if (Array.isArray(response.data)) {
        for (const item of response.data) {
          if (item.operation) {
            operations.push({
              type: item.operation,
              params: item.params || {}
            });
          }
        }
      }
    }

    return operations;
  }

  /**
   * Parse natural language for implicit viewer commands
   * This is a fallback for when the backend doesn't return structured viewer_actions
   */
  parseNaturalLanguage(message: string): ViewerOperation[] {
    const operations: ViewerOperation[] = [];
    const lowerMessage = message.toLowerCase();

    // Selection patterns
    if (lowerMessage.includes('selected') || lowerMessage.includes('selecting')) {
      const dbIdMatch = message.match(/\b(\d+(?:,\s*\d+)*)\b/);
      if (dbIdMatch) {
        const dbIds = dbIdMatch[1].split(/,\s*/).map(Number);
        operations.push({ type: 'select', params: { dbIds } });
      }
    }

    // Isolation patterns
    if (lowerMessage.includes('isolated') || lowerMessage.includes('isolating')) {
      const dbIdMatch = message.match(/\b(\d+(?:,\s*\d+)*)\b/);
      if (dbIdMatch) {
        const dbIds = dbIdMatch[1].split(/,\s*/).map(Number);
        operations.push({ type: 'isolate', params: { dbIds } });
      }
    }

    // Zoom patterns
    if (lowerMessage.includes('zoomed to') || lowerMessage.includes('zooming to')) {
      operations.push({ type: 'fitToView', params: {} });
    }

    // Camera preset patterns
    const presetPatterns: Record<string, string> = {
      'front view': 'front',
      'back view': 'back',
      'top view': 'top',
      'bottom view': 'bottom',
      'left view': 'left',
      'right view': 'right',
      'isometric': 'iso',
      'iso view': 'iso'
    };

    for (const [pattern, preset] of Object.entries(presetPatterns)) {
      if (lowerMessage.includes(pattern)) {
        operations.push({ type: 'setCameraPreset', params: { preset } });
        break;
      }
    }

    // Section patterns
    if (lowerMessage.includes('section') || lowerMessage.includes('cut plane')) {
      if (lowerMessage.includes('x plane') || lowerMessage.includes('x-axis')) {
        operations.push({ type: 'createSection', params: { plane: 'X', offset: 0 } });
      } else if (lowerMessage.includes('y plane') || lowerMessage.includes('y-axis')) {
        operations.push({ type: 'createSection', params: { plane: 'Y', offset: 0 } });
      } else if (lowerMessage.includes('z plane') || lowerMessage.includes('z-axis')) {
        operations.push({ type: 'createSection', params: { plane: 'Z', offset: 0 } });
      }
    }

    // Clear patterns
    if (lowerMessage.includes('cleared section') || lowerMessage.includes('removed section')) {
      operations.push({ type: 'clearSection', params: {} });
    }

    // Explode patterns
    if (lowerMessage.includes('exploded') || lowerMessage.includes('exploding')) {
      const scaleMatch = message.match(/scale[:\s]*(\d+(?:\.\d+)?)/i);
      const scale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;
      operations.push({ type: 'explode', params: { scale } });
    }

    // Show all patterns
    if (lowerMessage.includes('showing all') || lowerMessage.includes('shown all')) {
      operations.push({ type: 'showAll', params: {} });
    }

    // Hide patterns
    if (lowerMessage.includes('hidden') || lowerMessage.includes('hiding')) {
      const dbIdMatch = message.match(/\b(\d+(?:,\s*\d+)*)\b/);
      if (dbIdMatch) {
        const dbIds = dbIdMatch[1].split(/,\s*/).map(Number);
        operations.push({ type: 'hide', params: { dbIds } });
      }
    }

    return operations;
  }

  /**
   * Check if response contains viewer operations
   */
  hasViewerOperations(response: ApiResponse): boolean {
    if (response.viewer_actions && response.viewer_actions.length > 0) {
      return true;
    }
    if (response.data?.operation) {
      return true;
    }
    return false;
  }

  /**
   * Extract chart configurations from response
   */
  extractCharts(response: ApiResponse): any[] {
    return response.charts || [];
  }

  /**
   * Check if response is successful
   */
  isSuccessful(response: ApiResponse): boolean {
    return response.success !== false;
  }
}
