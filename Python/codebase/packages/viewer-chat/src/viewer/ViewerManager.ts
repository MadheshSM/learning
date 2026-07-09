/**
 * ViewerManager - Manages Autodesk Viewer lifecycle and model loading
 * Supports static SVF file loading without Forge API authentication
 */

export interface ViewerOptions {
  extensions?: string[];
  theme?: 'light' | 'dark';
  disableDefaultTools?: boolean;
}

export interface ModelLoadOptions {
  globalOffset?: { x: number; y: number; z: number };
  placementTransform?: number[];
  sharedPropertyDbPath?: string;
}

export class ViewerManager {
  private viewer: Autodesk.Viewing.GuiViewer3D | null = null;
  private container: HTMLElement | null = null;
  private isInitialized: boolean = false;
  private loadedModels: Map<string, Autodesk.Viewing.Model> = new Map();
  private eventListeners: Map<string, Set<(e: any) => void>> = new Map();

  /**
   * Initialize the Autodesk Viewer
   * @param container - HTML element to host the viewer
   * @param options - Viewer configuration options
   */
  async initialize(container: HTMLElement, options: ViewerOptions = {}): Promise<void> {
    if (this.isInitialized) {
      console.warn('ViewerManager: Already initialized');
      return;
    }

    this.container = container;

    return new Promise((resolve, reject) => {
      // Initialize viewer runtime for local/static SVF mode
      Autodesk.Viewing.Initializer(
        {
          env: 'Local', // Key: enables static SVF loading without authentication
          useConsolidation: true,
          useADP: false
        },
        () => {
          try {
            // Default extensions for full functionality
            const defaultExtensions = [
              'Autodesk.Viewing.MarkupsCore',
              'Autodesk.Viewing.MarkupsGui',
              'Autodesk.Measure',
              'Autodesk.Section'
            ];

            const extensions = options.extensions
              ? [...defaultExtensions, ...options.extensions]
              : defaultExtensions;

            // Create viewer instance
            this.viewer = new Autodesk.Viewing.GuiViewer3D(container, {
              extensions: extensions,
              theme: options.theme === 'dark' ? 'dark-theme' : 'light-theme'
            });

            const startCode = this.viewer.start();
            if (startCode !== 0) {
              reject(new Error(`Viewer start failed with code: ${startCode}`));
              return;
            }

            this.isInitialized = true;
            this.setupDefaultEventListeners();
            resolve();
          } catch (error) {
            reject(error);
          }
        }
      );
    });
  }

  /**
   * Load a model from SVF path
   * @param svfPath - Path to the SVF file (local or URL)
   * @param options - Model load options
   */
  async loadModel(svfPath: string, options: ModelLoadOptions = {}): Promise<Autodesk.Viewing.Model> {
    if (!this.viewer) {
      throw new Error('Viewer not initialized. Call initialize() first.');
    }

    // Check if model is already loaded
    if (this.loadedModels.has(svfPath)) {
      console.warn(`Model already loaded: ${svfPath}`);
      return this.loadedModels.get(svfPath)!;
    }

    return new Promise((resolve, reject) => {
      this.viewer!.loadModel(
        svfPath,
        options,
        (model) => {
          this.loadedModels.set(svfPath, model);
          resolve(model);
        },
        (errorCode, errorMessage, messages) => {
          console.error('Model load error:', { errorCode, errorMessage, messages });
          reject(new Error(`Failed to load model: ${errorMessage || errorCode}`));
        }
      );
    });
  }

  /**
   * Unload a model
   * @param svfPath - Path of the model to unload
   */
  unloadModel(svfPath: string): boolean {
    if (!this.viewer) return false;

    const model = this.loadedModels.get(svfPath);
    if (model) {
      this.viewer.unloadModel(model);
      this.loadedModels.delete(svfPath);
      return true;
    }
    return false;
  }

  /**
   * Unload all models
   */
  unloadAllModels(): void {
    this.loadedModels.forEach((model, path) => {
      this.unloadModel(path);
    });
  }

  /**
   * Get the viewer instance
   */
  getViewer(): Autodesk.Viewing.GuiViewer3D | null {
    return this.viewer;
  }

  /**
   * Get the current model
   */
  getCurrentModel(): Autodesk.Viewing.Model | null {
    return this.viewer?.model || null;
  }

  /**
   * Get all loaded models
   */
  getAllModels(): Autodesk.Viewing.Model[] {
    return this.viewer?.getAllModels() || [];
  }

  /**
   * Check if viewer is ready
   */
  isReady(): boolean {
    return this.isInitialized && this.viewer !== null;
  }

  /**
   * Add event listener
   */
  addEventListener(event: string, callback: (e: any) => void): void {
    if (!this.viewer) {
      console.warn('Viewer not initialized');
      return;
    }

    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
    this.viewer.addEventListener(event, callback);
  }

  /**
   * Remove event listener
   */
  removeEventListener(event: string, callback: (e: any) => void): void {
    if (!this.viewer) return;

    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.delete(callback);
      this.viewer.removeEventListener(event, callback);
    }
  }

  /**
   * Setup default event listeners for internal tracking
   */
  private setupDefaultEventListeners(): void {
    if (!this.viewer) return;

    // Track geometry loaded for model ready state
    this.viewer.addEventListener(
      Autodesk.Viewing.GEOMETRY_LOADED_EVENT,
      () => {
        this.emitCustomEvent('viewerReady', { model: this.getCurrentModel() });
      }
    );
  }

  /**
   * Emit custom event
   */
  private emitCustomEvent(type: string, detail: any): void {
    const event = new CustomEvent(`krion:viewer:${type}`, { detail });
    document.dispatchEvent(event);
  }

  /**
   * Resize viewer to fit container
   */
  resize(): void {
    if (this.viewer) {
      this.viewer.impl?.resize(
        this.container?.clientWidth || 0,
        this.container?.clientHeight || 0
      );
    }
  }

  /**
   * Take a screenshot of the current view
   */
  async getScreenshot(width?: number, height?: number): Promise<string> {
    if (!this.viewer) {
      throw new Error('Viewer not initialized');
    }

    return new Promise((resolve) => {
      this.viewer!.getScreenShot(width || 1920, height || 1080, (blob: string) => {
        resolve(blob);
      });
    });
  }

  /**
   * Destroy the viewer and cleanup resources
   */
  destroy(): void {
    if (!this.viewer) return;

    // Remove all event listeners
    this.eventListeners.forEach((callbacks, event) => {
      callbacks.forEach((callback) => {
        this.viewer!.removeEventListener(event, callback);
      });
    });
    this.eventListeners.clear();

    // Unload all models
    this.unloadAllModels();

    // Finish and cleanup viewer
    this.viewer.finish();
    this.viewer.uninitialize();
    this.viewer = null;
    this.container = null;
    this.isInitialized = false;
  }
}
