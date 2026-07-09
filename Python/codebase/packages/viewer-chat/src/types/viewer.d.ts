// Autodesk Viewer Type Declarations
declare namespace Autodesk {
  namespace Viewing {
    interface InitializerOptions {
      env?: string;
      api?: string;
      getAccessToken?: (callback: (token: string, expires: number) => void) => void;
      useADP?: boolean;
      useConsolidation?: boolean;
      language?: string;
    }

    function Initializer(
      options: InitializerOptions,
      callback: () => void
    ): void;

    interface ViewerConfig {
      extensions?: string[];
      disabledExtensions?: { [key: string]: boolean };
      theme?: string;
    }

    interface Model {
      id: number;
      getDocumentNode(): any;
      getData(): any;
      getInstanceTree(): any;
      getBulkProperties(
        dbIds: number[],
        options: any,
        onSuccess: (results: any[]) => void,
        onError: (err: any) => void
      ): void;
      search(
        text: string,
        onSuccess: (dbIds: number[]) => void,
        onError: (err: any) => void,
        attributeNames?: string[]
      ): void;
    }

    interface Camera {
      position: THREE.Vector3;
      target: THREE.Vector3;
      up: THREE.Vector3;
      fov: number;
      isPerspective: boolean;
    }

    interface SelectionChangedEvent {
      dbIdArray: number[];
      fragIdsArray: number[];
      model: Model;
    }

    class GuiViewer3D {
      constructor(container: HTMLElement, config?: ViewerConfig);

      start(): number;
      finish(): void;
      uninitialize(): void;

      loadModel(
        url: string,
        options?: any,
        onSuccess?: (model: Model) => void,
        onError?: (errorCode: number, errorMessage: string, messages: any) => void
      ): void;

      unloadModel(model: Model): void;

      // Selection
      select(dbIds: number | number[], model?: Model, selectionType?: number): void;
      clearSelection(): void;
      getSelection(): number[];
      getAggregateSelection(): { model: Model; selection: number[] }[];

      // Visibility
      isolate(dbIds?: number | number[], model?: Model): void;
      hide(dbIds: number | number[], model?: Model): void;
      show(dbIds: number | number[], model?: Model): void;
      showAll(): void;
      setGhosting(value: boolean): void;

      // Camera
      fitToView(dbIds?: number[], model?: Model, immediate?: boolean): void;
      setViewFromArray(params: number[]): void;
      getState(filter?: any): any;
      restoreState(state: any, filter?: any, immediate?: boolean): void;
      navigation: Navigation;
      getCamera(): Camera;

      // Section
      setCutPlanes(planes: THREE.Vector4[] | null): void;
      getCutPlanes(): THREE.Vector4[];

      // Explode
      explode(scale: number): void;
      getExplodeScale(): number;

      // Properties
      getProperties(
        dbId: number,
        onSuccess: (result: PropertyResult) => void,
        onError?: (err: any) => void
      ): void;

      // Model info
      model: Model;
      getAllModels(): Model[];

      // Extensions
      loadExtension(extensionId: string, options?: any): Promise<Extension>;
      unloadExtension(extensionId: string): boolean;
      getExtension(extensionId: string): Extension | null;

      // Events
      addEventListener(event: string, callback: (e: any) => void): void;
      removeEventListener(event: string, callback: (e: any) => void): void;

      // Canvas/Container
      container: HTMLElement;
      canvas: HTMLCanvasElement;
      impl: any;
    }

    interface Navigation {
      setPosition(position: THREE.Vector3): void;
      setTarget(target: THREE.Vector3): void;
      getPosition(): THREE.Vector3;
      getTarget(): THREE.Vector3;
      getCamera(): Camera;
      setCamera(camera: Camera): void;
      setView(position: THREE.Vector3, target: THREE.Vector3): void;
      setVerticalFov(fov: number): void;
      setWorldUpVector(up: THREE.Vector3): void;
      getWorldUpVector(): THREE.Vector3;
      setCameraUpVector(up: THREE.Vector3): void;
      toPerspective(): void;
      toOrthographic(): void;
      setOrbitPastWorldPoles(value: boolean): void;
    }

    interface PropertyResult {
      dbId: number;
      name: string;
      externalId: string;
      properties: PropertyItem[];
    }

    interface PropertyItem {
      attributeName: string;
      displayCategory: string;
      displayName: string;
      displayValue: string | number;
      hidden: boolean;
      type: number;
      units: string | null;
    }

    class Extension {
      viewer: GuiViewer3D;
      load(): boolean | Promise<boolean>;
      unload(): boolean;
      activate(mode?: string): boolean;
      deactivate(): boolean;
    }

    // Events
    const SELECTION_CHANGED_EVENT: string;
    const ISOLATE_EVENT: string;
    const HIDE_EVENT: string;
    const SHOW_EVENT: string;
    const CAMERA_CHANGE_EVENT: string;
    const EXPLODE_CHANGE_EVENT: string;
    const CUTPLANES_CHANGE_EVENT: string;
    const MODEL_ROOT_LOADED_EVENT: string;
    const GEOMETRY_LOADED_EVENT: string;
    const OBJECT_TREE_CREATED_EVENT: string;
    const EXTENSION_LOADED_EVENT: string;

    // MarkupsCore Extension
    namespace Extensions {
      namespace Markups {
        namespace Core {
          class MarkupsCore extends Extension {
            enterEditMode(): void;
            leaveEditMode(): void;
            show(): void;
            hide(): void;
            clear(): void;
            generateData(): string;
            loadMarkups(markupsData: string, layerId?: string): boolean;
          }
        }
      }
    }
  }
}

// THREE.js Vector types (minimal)
declare namespace THREE {
  class Vector3 {
    constructor(x?: number, y?: number, z?: number);
    x: number;
    y: number;
    z: number;
    set(x: number, y: number, z: number): Vector3;
    copy(v: Vector3): Vector3;
    clone(): Vector3;
    add(v: Vector3): Vector3;
    sub(v: Vector3): Vector3;
    multiplyScalar(s: number): Vector3;
    normalize(): Vector3;
    length(): number;
    distanceTo(v: Vector3): number;
    toArray(): [number, number, number];
    fromArray(array: number[]): Vector3;
  }

  class Vector4 {
    constructor(x?: number, y?: number, z?: number, w?: number);
    x: number;
    y: number;
    z: number;
    w: number;
    set(x: number, y: number, z: number, w: number): Vector4;
  }
}
