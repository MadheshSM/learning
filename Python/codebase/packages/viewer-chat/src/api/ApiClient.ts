/**
 * ApiClient - Backend communication for viewer chat
 */

export interface ApiClientConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
  retries?: number;
  retryDelay?: number;
}

export interface QueryRequest {
  query: string;
  project_id?: string;
  model_context?: {
    selected_ids?: number[];
    visible_ids?: number[];
    camera_state?: any;
    model_path?: string;
  };
}

export interface QueryResponse {
  success: boolean;
  message?: string;
  response?: string;
  data?: any;
  charts?: any[];
  viewer_actions?: Array<{
    operation: string;
    params?: Record<string, any>;
    description?: string;
  }>;
  agents_used?: string[];
  routing?: {
    intent?: string;
    agents?: string[];
    reasoning?: string;
  };
  interaction_logs?: any[];
  interaction_summary?: {
    total_steps?: number;
    agents_involved?: string[];
    tool_calls?: number;
    errors?: number;
    total_duration_ms?: number;
  };
  error?: string;
}

export interface HealthResponse {
  status: string;
  data_loaded: boolean;
  orchestrator_ready: boolean;
}

export class ApiClient {
  private config: Required<ApiClientConfig>;
  private abortController: AbortController | null = null;

  constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 120000, // 2 minutes default
      headers: {},
      retries: 2,
      retryDelay: 1000,
      ...config
    };
  }

  /**
   * Send a query to the backend
   */
  async query(request: QueryRequest): Promise<QueryResponse> {
    return this.post<QueryResponse>('/api/query', request);
  }

  /**
   * Check backend health
   */
  async health(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/api/health');
  }

  /**
   * Get data summary
   */
  async getDataSummary(): Promise<any> {
    return this.get('/api/data/summary');
  }

  /**
   * Reload backend data
   */
  async reloadData(): Promise<any> {
    return this.post('/api/data/reload', {});
  }

  /**
   * Cancel current request
   */
  cancel(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Make a GET request
   */
  private async get<T>(endpoint: string): Promise<T> {
    return this.request<T>('GET', endpoint);
  }

  /**
   * Make a POST request
   */
  private async post<T>(endpoint: string, body: any): Promise<T> {
    return this.request<T>('POST', endpoint, body);
  }

  /**
   * Make an HTTP request with retries
   */
  private async request<T>(
    method: string,
    endpoint: string,
    body?: any,
    retryCount: number = 0
  ): Promise<T> {
    // Cancel any existing request
    this.cancel();
    this.abortController = new AbortController();

    const url = `${this.config.baseUrl}${endpoint}`;

    const fetchOptions: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...this.config.headers
      },
      signal: this.abortController.signal
    };

    if (body) {
      fetchOptions.body = JSON.stringify(body);
    }

    // Create timeout promise
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => {
        this.cancel();
        reject(new Error(`Request timeout after ${this.config.timeout}ms`));
      }, this.config.timeout);
    });

    try {
      const response = await Promise.race([
        fetch(url, fetchOptions),
        timeoutPromise
      ]);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
        throw new ApiError(
          errorBody.detail || errorBody.message || `HTTP ${response.status}`,
          response.status,
          errorBody
        );
      }

      return await response.json();
    } catch (error) {
      // Don't retry on abort
      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiError('Request cancelled', 0);
      }

      // Retry on network errors
      if (retryCount < this.config.retries && this.shouldRetry(error)) {
        await this.delay(this.config.retryDelay * (retryCount + 1));
        return this.request<T>(method, endpoint, body, retryCount + 1);
      }

      // Convert to ApiError if not already
      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError(
        error instanceof Error ? error.message : 'Unknown error',
        0
      );
    }
  }

  /**
   * Check if error is retryable
   */
  private shouldRetry(error: any): boolean {
    // Retry on network errors and 5xx errors
    if (error instanceof ApiError) {
      return error.status >= 500 || error.status === 0;
    }
    // Retry on generic errors (likely network issues)
    return error instanceof Error && error.name !== 'AbortError';
  }

  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<ApiClientConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current base URL
   */
  getBaseUrl(): string {
    return this.config.baseUrl;
  }
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
