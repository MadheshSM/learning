/**
 * ViewerAPI - Unified interface for all viewer operations
 * Handles selection, visibility, camera, sectioning, explode, measurement, markup, and walkthrough
 */

import { ViewerManager } from './ViewerManager';

export interface ViewerOperation {
  type: string;
  params: Record<string, any>;
}

export interface ViewerOperationResult {
  success: boolean;
  data?: any;
  error?: string;
}

export type CameraPreset = 'front' | 'back' | 'top' | 'bottom' | 'left' | 'right' | 'iso' | 'iso_front' | 'iso_back';
export type MeasurementType = 'distance' | 'angle' | 'area';
export type MarkupType = 'text' | 'arrow' | 'circle' | 'rectangle' | 'freehand' | 'cloud' | 'polyline';

export interface WalkthroughWaypoint {
  position: [number, number, number];
  target: [number, number, number];
  duration?: number; // ms to reach this waypoint
}

export interface MarkupOptions {
  type: MarkupType;
  text?: string;
  position?: { x: number; y: number };
  style?: {
    color?: string;
    strokeWidth?: number;
    fontSize?: number;
  };
}

export class ViewerAPI {
  private manager: ViewerManager;
  private walkthroughInterval: number | null = null;
  private measureExtension: any = null;
  private markupsExtension: any = null;
  private sectionExtension: any = null;

  constructor(manager: ViewerManager) {
    this.manager = manager;
  }

  /**
   * Execute an operation by type name
   * Called by ResponseHandler to execute viewer actions from chat
   */
  async execute(operation: ViewerOperation): Promise<ViewerOperationResult> {
    const handler = this.operationHandlers[operation.type];
    if (!handler) {
      return { success: false, error: `Unknown operation: ${operation.type}` };
    }

    try {
      return await handler(operation.params);
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  }

  // Operation handlers map
  private operationHandlers: Record<string, (params: any) => Promise<ViewerOperationResult>> = {
    // Selection operations
    select: async (params) => this.select(params.dbIds, params.model),
    clearSelection: async () => this.clearSelection(),
    selectByProperty: async (params) => this.selectByProperty(params.property, params.value, params.category),

    // Visibility operations
    isolate: async (params) => this.isolate(params.dbIds),
    hide: async (params) => this.hide(params.dbIds),
    show: async (params) => this.show(params.dbIds),
    showAll: async () => this.showAll(),

    // Camera operations
    fitToView: async (params) => this.fitToView(params.dbIds),
    setCamera: async (params) => this.setCamera(params.position, params.target, params.up),
    setCameraPreset: async (params) => this.setCameraPreset(params.preset),

    // Section operations
    createSection: async (params) => this.createSection(params.plane, params.offset),
    clearSection: async () => this.clearSection(),

    // Explode operations
    explode: async (params) => this.explode(params.scale),

    // Measurement operations
    measure: async (params) => this.startMeasurement(params.type),
    clearMeasurements: async () => this.clearMeasurements(),

    // Markup operations
    addMarkup: async (params) => this.addMarkup(params),
    clearMarkups: async () => this.clearMarkups(),

    // Property operations
    getProperties: async (params) => this.getProperties(params.dbId),
    searchByProperty: async (params) => this.searchByProperty(params.category, params.property, params.value),

    // Walkthrough operations
    startWalkthrough: async (params) => this.startWalkthrough(params.waypoints),
    stopWalkthrough: async () => this.stopWalkthrough(),

    // Comparison operations
    compareModels: async (params) => this.compareModels(params.model1, params.model2)
  };

  // ============= SELECTION OPERATIONS =============

  /**
   * Select elements by database IDs
   */
  async select(dbIds: number[], model?: number): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    try {
      viewer.select(dbIds);
      return { success: true, data: { selected: dbIds, count: dbIds.length } };
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Clear current selection
   */
  async clearSelection(): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    viewer.clearSelection();
    return { success: true };
  }

  /**
   * Select elements by property value
   */
  async selectByProperty(property: string, value: string, category?: string): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    const model = viewer?.model;
    if (!viewer || !model) return { success: false, error: 'Viewer or model not initialized' };

    return new Promise((resolve) => {
      model.search(
        value,
        (dbIds) => {
          if (dbIds.length > 0) {
            viewer.select(dbIds);
            resolve({ success: true, data: { selected: dbIds, count: dbIds.length } });
          } else {
            resolve({ success: true, data: { selected: [], count: 0, message: 'No matching elements found' } });
          }
        },
        (error) => {
          resolve({ success: false, error: error.message || 'Search failed' });
        },
        property ? [property] : undefined
      );
    });
  }

  // ============= VISIBILITY OPERATIONS =============

  /**
   * Isolate elements (hide everything else)
   */
  async isolate(dbIds?: number[]): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    viewer.isolate(dbIds);
    return { success: true, data: { isolated: dbIds || 'all' } };
  }

  /**
   * Hide specific elements
   */
  async hide(dbIds: number[]): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    viewer.hide(dbIds);
    return { success: true, data: { hidden: dbIds, count: dbIds.length } };
  }

  /**
   * Show specific elements
   */
  async show(dbIds?: number[]): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    if (dbIds && dbIds.length > 0) {
      viewer.show(dbIds);
      return { success: true, data: { shown: dbIds, count: dbIds.length } };
    } else {
      viewer.showAll();
      return { success: true, data: { shown: 'all' } };
    }
  }

  /**
   * Show all elements
   */
  async showAll(): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    viewer.showAll();
    viewer.isolate(); // Clear isolation
    return { success: true };
  }

  // ============= CAMERA OPERATIONS =============

  /**
   * Zoom to fit elements in view
   */
  async fitToView(dbIds?: number[]): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    viewer.fitToView(dbIds, undefined, true);
    return { success: true, data: { fittedTo: dbIds || 'all' } };
  }

  /**
   * Set camera position and target
   */
  async setCamera(
    position: [number, number, number],
    target: [number, number, number],
    up?: [number, number, number]
  ): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    const posVec = new THREE.Vector3(position[0], position[1], position[2]);
    const targetVec = new THREE.Vector3(target[0], target[1], target[2]);

    const upVec = up ? new THREE.Vector3(up[0], up[1], up[2]) : null;
    viewer.navigation.setView(posVec, targetVec, upVec);
    (viewer as any).impl.syncCamera();
    (viewer as any).impl.invalidate(true);

    return { success: true, data: { position, target, up } };
  }

  /**
   * Set camera to preset view
   */
  async setCameraPreset(preset: CameraPreset): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    // Calculate preset camera positions based on model bounds
    const model = viewer.model;
    if (!model) return { success: false, error: 'No model loaded' };

    // Get model bounding box
    const boundingBox = model.getBoundingBox();
    const center = boundingBox.center();
    const size = boundingBox.size();
    const maxDim = Math.max(size.x, size.y, size.z);
    const distance = maxDim * 2;

    let position: THREE.Vector3;
    let up = new THREE.Vector3(0, 0, 1);

    switch (preset) {
      case 'front':
        position = new THREE.Vector3(center.x, center.y - distance, center.z);
        break;
      case 'back':
        position = new THREE.Vector3(center.x, center.y + distance, center.z);
        break;
      case 'top':
        position = new THREE.Vector3(center.x, center.y, center.z + distance);
        up = new THREE.Vector3(0, 1, 0);
        break;
      case 'bottom':
        position = new THREE.Vector3(center.x, center.y, center.z - distance);
        up = new THREE.Vector3(0, -1, 0);
        break;
      case 'left':
        position = new THREE.Vector3(center.x - distance, center.y, center.z);
        break;
      case 'right':
        position = new THREE.Vector3(center.x + distance, center.y, center.z);
        break;
      case 'iso':
      case 'iso_front':
        position = new THREE.Vector3(
          center.x + distance * 0.7,
          center.y - distance * 0.7,
          center.z + distance * 0.7
        );
        break;
      case 'iso_back':
        position = new THREE.Vector3(
          center.x - distance * 0.7,
          center.y + distance * 0.7,
          center.z + distance * 0.7
        );
        break;
      default:
        return { success: false, error: `Unknown preset: ${preset}` };
    }

    viewer.navigation.setView(position, center, up);
    (viewer as any).impl.syncCamera();
    (viewer as any).impl.invalidate(true);

    return { success: true, data: { preset, position: position.toArray(), target: center.toArray() } };
  }

  // ============= SECTION OPERATIONS =============

  /**
   * Create a section cutting plane
   */
  async createSection(plane: 'X' | 'Y' | 'Z', offset: number = 0): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    const model = viewer.model;
    if (!model) return { success: false, error: 'No model loaded' };

    // Calculate section plane based on model center
    const boundingBox = model.getBoundingBox();
    const center = boundingBox.center();

    let sectionPlane: THREE.Vector4;
    switch (plane) {
      case 'X':
        sectionPlane = new THREE.Vector4(1, 0, 0, -(center.x + offset));
        break;
      case 'Y':
        sectionPlane = new THREE.Vector4(0, 1, 0, -(center.y + offset));
        break;
      case 'Z':
        sectionPlane = new THREE.Vector4(0, 0, 1, -(center.z + offset));
        break;
      default:
        return { success: false, error: `Invalid plane: ${plane}` };
    }

    viewer.setCutPlanes([sectionPlane]);
    return { success: true, data: { plane, offset } };
  }

  /**
   * Clear all section planes
   */
  async clearSection(): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    viewer.setCutPlanes(null);
    return { success: true };
  }

  // ============= EXPLODE OPERATIONS =============

  /**
   * Explode the model
   */
  async explode(scale: number = 1): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    // Clamp scale between 0 and 3
    const clampedScale = Math.max(0, Math.min(scale, 3));
    viewer.explode(clampedScale);
    return { success: true, data: { scale: clampedScale } };
  }

  // ============= MEASUREMENT OPERATIONS =============

  /**
   * Start measurement tool
   */
  async startMeasurement(type: MeasurementType = 'distance'): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    try {
      // Load or get measure extension
      if (!this.measureExtension) {
        this.measureExtension = await viewer.loadExtension('Autodesk.Measure');
      }

      // Activate the extension
      this.measureExtension.activate(type);

      return { success: true, data: { measurementType: type, message: 'Click on the model to start measuring' } };
    } catch (error) {
      return { success: false, error: `Failed to start measurement: ${(error as Error).message}` };
    }
  }

  /**
   * Clear all measurements
   */
  async clearMeasurements(): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    try {
      if (this.measureExtension) {
        this.measureExtension.deactivate();
        this.measureExtension.clearMeasurements?.();
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  }

  // ============= MARKUP OPERATIONS =============

  /**
   * Add markup annotation
   */
  async addMarkup(options: MarkupOptions): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    try {
      // Load or get markups extension
      if (!this.markupsExtension) {
        this.markupsExtension = await viewer.loadExtension('Autodesk.Viewing.MarkupsCore');
      }

      this.markupsExtension.enterEditMode();
      this.markupsExtension.show();

      // Note: Full markup creation would require more specific implementation
      // based on the markup type and position
      return {
        success: true,
        data: {
          message: 'Markup mode activated. Click on the model to add annotations.',
          type: options.type
        }
      };
    } catch (error) {
      return { success: false, error: `Failed to add markup: ${(error as Error).message}` };
    }
  }

  /**
   * Clear all markups
   */
  async clearMarkups(): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    try {
      if (this.markupsExtension) {
        this.markupsExtension.leaveEditMode();
        this.markupsExtension.clear();
        this.markupsExtension.hide();
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  }

  // ============= PROPERTY OPERATIONS =============

  /**
   * Get properties of an element
   */
  async getProperties(dbId: number): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    return new Promise((resolve) => {
      viewer.getProperties(
        dbId,
        (result) => {
          resolve({ success: true, data: result });
        },
        (error) => {
          resolve({ success: false, error: error?.message || 'Failed to get properties' });
        }
      );
    });
  }

  /**
   * Search elements by property
   */
  async searchByProperty(
    category?: string,
    property?: string,
    value?: string
  ): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    const model = viewer?.model;
    if (!viewer || !model) return { success: false, error: 'Viewer or model not initialized' };

    const searchText = value || category || '';
    if (!searchText) {
      return { success: false, error: 'Must provide search value' };
    }

    return new Promise((resolve) => {
      model.search(
        searchText,
        (dbIds) => {
          resolve({
            success: true,
            data: {
              dbIds,
              count: dbIds.length,
              searchParams: { category, property, value }
            }
          });
        },
        (error) => {
          resolve({ success: false, error: error?.message || 'Search failed' });
        },
        property ? [property] : undefined
      );
    });
  }

  // ============= WALKTHROUGH OPERATIONS =============

  /**
   * Start camera walkthrough animation
   */
  async startWalkthrough(waypoints: WalkthroughWaypoint[]): Promise<ViewerOperationResult> {
    const viewer = this.manager.getViewer();
    if (!viewer) return { success: false, error: 'Viewer not initialized' };

    if (!waypoints || waypoints.length < 2) {
      return { success: false, error: 'Walkthrough requires at least 2 waypoints' };
    }

    // Stop any existing walkthrough
    this.stopWalkthrough();

    let currentIndex = 0;
    const defaultDuration = 2000; // 2 seconds per waypoint

    const animateToWaypoint = () => {
      if (currentIndex >= waypoints.length) {
        this.walkthroughInterval = null;
        return;
      }

      const waypoint = waypoints[currentIndex];
      const position = new THREE.Vector3(...waypoint.position);
      const target = new THREE.Vector3(...waypoint.target);

      viewer.navigation.setView(position, target);
      (viewer as any).impl.syncCamera();
      (viewer as any).impl.invalidate(true);
      currentIndex++;

      const duration = waypoint.duration || defaultDuration;
      this.walkthroughInterval = window.setTimeout(animateToWaypoint, duration);
    };

    animateToWaypoint();

    return {
      success: true,
      data: {
        message: 'Walkthrough started',
        waypointCount: waypoints.length
      }
    };
  }

  /**
   * Stop camera walkthrough
   */
  async stopWalkthrough(): Promise<ViewerOperationResult> {
    if (this.walkthroughInterval) {
      clearTimeout(this.walkthroughInterval);
      this.walkthroughInterval = null;
    }
    return { success: true };
  }

  // ============= COMPARISON OPERATIONS =============

  /**
   * Compare two models (basic implementation)
   */
  async compareModels(model1Path: string, model2Path: string): Promise<ViewerOperationResult> {
    // This is a placeholder for model comparison
    // Full implementation would require loading both models and using comparison extensions
    return {
      success: false,
      error: 'Model comparison requires multiple models to be loaded. This feature is under development.'
    };
  }

  // ============= UTILITY METHODS =============

  /**
   * Get current selection
   */
  getSelection(): number[] {
    return this.manager.getViewer()?.getSelection() || [];
  }

  /**
   * Get current camera state
   */
  getCameraState(): { position: number[]; target: number[]; up: number[] } | null {
    const viewer = this.manager.getViewer();
    if (!viewer) return null;

    const camera = viewer.getCamera();
    return {
      position: camera.position.toArray(),
      target: camera.target.toArray(),
      up: camera.up.toArray()
    };
  }

  /**
   * Get explode scale
   */
  getExplodeScale(): number {
    return this.manager.getViewer()?.getExplodeScale() || 0;
  }
}
