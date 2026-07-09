/**
 * @krion/viewer-chat
 * Autodesk Viewer + AI Chat interface widget
 *
 * Main entry point for the package
 */

// Core widget
export { ViewerChat, ViewerChatConfig } from './core/ViewerChat';

// Viewer components
export { ViewerManager, ViewerOptions, ModelLoadOptions } from './viewer/ViewerManager';
export {
  ViewerAPI,
  ViewerOperation,
  ViewerOperationResult,
  CameraPreset,
  MeasurementType,
  MarkupType,
  MarkupOptions,
  WalkthroughWaypoint
} from './viewer/ViewerAPI';
export { ViewerState, ViewerStateSnapshot } from './viewer/ViewerState';

// Chat components
export { ChatInterface, ChatInterfaceOptions, ChatMessage } from './chat/ChatInterface';
export { MessageParser, ParsedResponse, ApiResponse, ViewerAction } from './chat/MessageParser';

// API components
export { ApiClient, ApiClientConfig, QueryRequest, QueryResponse, ApiError } from './api/ApiClient';
export { ResponseHandler, ResponseHandlerOptions } from './api/ResponseHandler';

// Version
export const VERSION = '1.0.0';

// Default export for UMD
import { ViewerChat } from './core/ViewerChat';
export default ViewerChat;
