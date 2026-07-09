import { Injectable } from '@angular/core';
import { ViewerAction } from './chat-api.service';

/**
 * Service to execute viewer actions from chat responses.
 *
 * IMPORTANT: You need to provide your existing viewer instance to this service.
 * Call setViewer() with your Autodesk.Viewing.GuiViewer3D instance after it's initialized.
 *
 * Example:
 *   constructor(private viewerActionExecutor: ViewerActionExecutorService) {}
 *
 *   ngAfterViewInit() {
 *     // After your viewer is initialized
 *     this.viewerActionExecutor.setViewer(this.yourViewer);
 *   }
 */
@Injectable({
  providedIn: 'root'
})
export class ViewerActionExecutorService {
  private viewer: any = null; // Autodesk.Viewing.GuiViewer3D

  /**
   * Set the viewer instance. Call this after your viewer is initialized.
   */
  setViewer(viewer: any): void {
    this.viewer = viewer;
    console.log('ViewerActionExecutor: Viewer instance set');
  }

  /**
   * Get the current viewer instance
   */
  getViewer(): any {
    return this.viewer;
  }

  /**
   * Execute a single viewer action
   */
  async executeAction(action: ViewerAction): Promise<{ success: boolean; error?: string }> {
    if (!this.viewer) {
      console.error('Viewer not set. Call setViewer() first.');
      return { success: false, error: 'Viewer not initialized' };
    }

    const { operation, params } = action;
    console.log(`Executing viewer action: ${operation}`, params);

    try {
      switch (operation) {
        // ============= SELECTION =============
        case 'select':
          this.viewer.select(params.dbIds || []);
          break;

        case 'clearSelection':
          this.viewer.clearSelection();
          break;

        case 'searchByProperty':
        case 'selectByProperty':
          await this.searchAndSelect(params);
          break;

        // ============= VISIBILITY =============
        case 'isolate':
          this.viewer.isolate(params.dbIds || []);
          break;

        case 'hide':
          this.viewer.hide(params.dbIds || []);
          break;

        case 'show':
          if (params.dbIds && params.dbIds.length > 0) {
            this.viewer.show(params.dbIds);
          } else {
            this.viewer.showAll();
          }
          break;

        case 'showAll':
          this.viewer.showAll();
          this.viewer.isolate(); // Clear isolation
          break;

        // ============= CAMERA =============
        case 'fitToView':
          this.viewer.fitToView(params.dbIds || undefined);
          break;

        case 'setCameraPreset':
          this.setCameraPreset(params.preset);
          break;

        case 'setCamera':
          this.setCamera(params.position, params.target, params.up);
          break;

        // ============= SECTION =============
        case 'createSection':
          this.createSection(params.plane, params.offset || 0);
          break;

        case 'clearSection':
          this.viewer.setCutPlanes(null);
          break;

        // ============= EXPLODE =============
        case 'explode':
          this.viewer.explode(params.scale || 1);
          break;

        case 'resetExplode':
          this.viewer.explode(0);
          break;

        // ============= MEASUREMENT =============
        case 'measure':
        case 'startMeasurement':
          await this.startMeasurement(params.type || params.measure_type || 'distance');
          break;

        case 'clearMeasurements':
          const measureExt = this.viewer.getExtension('Autodesk.Measure');
          if (measureExt) measureExt.deactivate();
          break;

        // ============= MARKUP =============
        case 'addMarkup':
        case 'startMarkup':
          await this.startMarkup(params.markup_type || params.type || 'text');
          break;

        case 'clearMarkups':
          const markupExt = this.viewer.getExtension('Autodesk.Viewing.MarkupsCore');
          if (markupExt) markupExt.leaveEditMode();
          break;

        default:
          console.warn('Unknown viewer operation:', operation);
          return { success: false, error: `Unknown operation: ${operation}` };
      }

      return { success: true };
    } catch (error: any) {
      console.error('Viewer action error:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Execute multiple viewer actions in sequence
   */
  async executeActions(actions: ViewerAction[]): Promise<void> {
    for (const action of actions) {
      await this.executeAction(action);
    }
  }

  // ============= PRIVATE METHODS =============

  private async searchAndSelect(params: any): Promise<void> {
    const searchTerm = params.category || params.value || '';

    return new Promise((resolve) => {
      this.viewer.search(
        searchTerm,
        (dbIds: number[]) => {
          console.log(`Found ${dbIds.length} elements for "${searchTerm}"`);
          if (dbIds && dbIds.length > 0) {
            // Isolate, select, and zoom to found elements
            this.viewer.isolate(dbIds);
            this.viewer.select(dbIds);
            this.viewer.fitToView(dbIds);
          }
          resolve();
        },
        (err: any) => {
          console.error('Search error:', err);
          resolve();
        }
      );
    });
  }

  private setCameraPreset(preset: string): void {
    if (!this.viewer?.model) return;

    const bbox = this.viewer.model.getBoundingBox();
    const center = bbox.getCenter(new (window as any).THREE.Vector3());
    const size = bbox.getSize(new (window as any).THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const distance = maxDim * 2;

    let position: any;
    let up = new (window as any).THREE.Vector3(0, 0, 1);
    const THREE = (window as any).THREE;

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
        console.warn('Unknown camera preset:', preset);
        return;
    }

    this.viewer.navigation.setView(position, center);
    this.viewer.navigation.setCameraUpVector(up);
  }

  private setCamera(position: number[], target: number[], up?: number[]): void {
    const THREE = (window as any).THREE;
    const pos = new THREE.Vector3(...position);
    const tgt = new THREE.Vector3(...target);
    this.viewer.navigation.setView(pos, tgt);

    if (up) {
      const upVec = new THREE.Vector3(...up);
      this.viewer.navigation.setCameraUpVector(upVec);
    }
  }

  private createSection(plane: string, offset: number = 0): void {
    if (!this.viewer?.model) return;

    const THREE = (window as any).THREE;
    const bbox = this.viewer.model.getBoundingBox();
    const center = bbox.getCenter(new THREE.Vector3());

    let sectionPlane: any;
    switch (plane.toUpperCase()) {
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
        console.warn('Unknown section plane:', plane);
        return;
    }

    this.viewer.setCutPlanes([sectionPlane]);
  }

  private async startMeasurement(type: string): Promise<void> {
    const ext = await this.viewer.loadExtension('Autodesk.Measure');
    if (ext) {
      ext.activate(type);
    }
  }

  private async startMarkup(type: string): Promise<void> {
    const ext = await this.viewer.loadExtension('Autodesk.Viewing.MarkupsCore');
    if (ext) {
      ext.enterEditMode();
      // Set markup style based on type
      // ext.changeEditMode(new Autodesk.Viewing.Extensions.Markups.Core.EditModeText(ext));
    }
  }
}
