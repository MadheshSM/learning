/**
 * ViewerState - State management with undo/redo support
 */

export interface ViewerStateSnapshot {
  id: string;
  timestamp: number;
  selection: number[];
  hiddenDbIds: number[];
  isolatedDbIds: number[];
  camera: {
    position: [number, number, number];
    target: [number, number, number];
    up: [number, number, number];
    fov: number;
    isPerspective: boolean;
  };
  cutPlanes: Array<{ x: number; y: number; z: number; w: number }>;
  explodeScale: number;
}

export class ViewerState {
  private history: ViewerStateSnapshot[] = [];
  private currentIndex: number = -1;
  private maxHistory: number = 50;

  /**
   * Capture current viewer state
   */
  capture(viewer: Autodesk.Viewing.GuiViewer3D): ViewerStateSnapshot {
    const camera = viewer.getCamera();
    const cutPlanes = viewer.getCutPlanes();

    const snapshot: ViewerStateSnapshot = {
      id: this.generateId(),
      timestamp: Date.now(),
      selection: viewer.getSelection() || [],
      hiddenDbIds: this.getHiddenDbIds(viewer),
      isolatedDbIds: this.getIsolatedDbIds(viewer),
      camera: {
        position: [camera.position.x, camera.position.y, camera.position.z],
        target: [camera.target.x, camera.target.y, camera.target.z],
        up: [camera.up.x, camera.up.y, camera.up.z],
        fov: camera.fov,
        isPerspective: camera.isPerspective
      },
      cutPlanes: cutPlanes.map((p: THREE.Vector4) => ({ x: p.x, y: p.y, z: p.z, w: p.w })),
      explodeScale: viewer.getExplodeScale()
    };

    // Add to history, removing any forward states
    this.history = this.history.slice(0, this.currentIndex + 1);
    this.history.push(snapshot);

    // Trim history if needed
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    } else {
      this.currentIndex++;
    }

    return snapshot;
  }

  /**
   * Restore viewer to a snapshot state
   */
  restore(viewer: Autodesk.Viewing.GuiViewer3D, state: ViewerStateSnapshot): void {
    // Restore camera
    const position = new THREE.Vector3(...state.camera.position);
    const target = new THREE.Vector3(...state.camera.target);
    viewer.navigation.setView(position, target);

    // Restore selection
    viewer.clearSelection();
    if (state.selection.length > 0) {
      viewer.select(state.selection);
    }

    // Restore visibility
    viewer.showAll();
    if (state.isolatedDbIds.length > 0) {
      viewer.isolate(state.isolatedDbIds);
    } else if (state.hiddenDbIds.length > 0) {
      viewer.hide(state.hiddenDbIds);
    }

    // Restore cut planes
    if (state.cutPlanes.length > 0) {
      const planes = state.cutPlanes.map(
        (p) => new THREE.Vector4(p.x, p.y, p.z, p.w)
      );
      viewer.setCutPlanes(planes);
    } else {
      viewer.setCutPlanes(null);
    }

    // Restore explode
    viewer.explode(state.explodeScale);
  }

  /**
   * Undo to previous state
   */
  undo(viewer: Autodesk.Viewing.GuiViewer3D): ViewerStateSnapshot | null {
    if (this.currentIndex <= 0) {
      return null; // Nothing to undo
    }

    this.currentIndex--;
    const state = this.history[this.currentIndex];
    this.restore(viewer, state);
    return state;
  }

  /**
   * Redo to next state
   */
  redo(viewer: Autodesk.Viewing.GuiViewer3D): ViewerStateSnapshot | null {
    if (this.currentIndex >= this.history.length - 1) {
      return null; // Nothing to redo
    }

    this.currentIndex++;
    const state = this.history[this.currentIndex];
    this.restore(viewer, state);
    return state;
  }

  /**
   * Check if undo is available
   */
  canUndo(): boolean {
    return this.currentIndex > 0;
  }

  /**
   * Check if redo is available
   */
  canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  /**
   * Get current state without adding to history
   */
  getCurrentState(): ViewerStateSnapshot | null {
    return this.history[this.currentIndex] || null;
  }

  /**
   * Get state history
   */
  getHistory(): ViewerStateSnapshot[] {
    return [...this.history];
  }

  /**
   * Clear history
   */
  clearHistory(): void {
    this.history = [];
    this.currentIndex = -1;
  }

  /**
   * Save state to localStorage
   */
  saveToStorage(key: string): void {
    try {
      localStorage.setItem(key, JSON.stringify({
        history: this.history,
        currentIndex: this.currentIndex
      }));
    } catch (e) {
      console.warn('Failed to save viewer state to localStorage:', e);
    }
  }

  /**
   * Load state from localStorage
   */
  loadFromStorage(key: string): boolean {
    try {
      const data = localStorage.getItem(key);
      if (data) {
        const parsed = JSON.parse(data);
        this.history = parsed.history || [];
        this.currentIndex = parsed.currentIndex ?? -1;
        return true;
      }
    } catch (e) {
      console.warn('Failed to load viewer state from localStorage:', e);
    }
    return false;
  }

  private generateId(): string {
    return `state_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getHiddenDbIds(viewer: Autodesk.Viewing.GuiViewer3D): number[] {
    // Note: This is a simplified implementation
    // Full implementation would track hidden elements through viewer events
    return [];
  }

  private getIsolatedDbIds(viewer: Autodesk.Viewing.GuiViewer3D): number[] {
    // Note: This is a simplified implementation
    // Full implementation would track isolated elements through viewer events
    return [];
  }
}
