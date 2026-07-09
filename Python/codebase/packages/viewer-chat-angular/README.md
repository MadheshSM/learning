# Viewer Chat Angular Component

A chat interface component for controlling Autodesk Viewer through natural language commands.

## Installation

Copy the following files to your Angular project (e.g., `src/app/viewer-chat/`):

```
viewer-chat/
├── index.ts
├── viewer-chat.module.ts
├── viewer-chat.component.ts
├── chat-api.service.ts
└── viewer-action-executor.service.ts
```

## Setup

### 1. Import the Module

```typescript
// app.module.ts
import { ViewerChatModule } from './viewer-chat';

@NgModule({
  imports: [
    // ... other modules
    ViewerChatModule
  ]
})
export class AppModule {}
```

### 2. Use in Your Component

```typescript
// your-viewer.component.ts
import { Component, ViewChild, AfterViewInit } from '@angular/core';
import { ViewerChatComponent } from './viewer-chat';

@Component({
  selector: 'app-your-viewer',
  template: `
    <div class="viewer-layout">
      <!-- Your existing viewer -->
      <div class="viewer-container">
        <div #viewerDiv id="forgeViewer"></div>
      </div>

      <!-- Chat component -->
      <div class="chat-container">
        <app-viewer-chat
          #viewerChat
          [apiUrl]="'http://localhost:8080'"
          [darkMode]="false">
        </app-viewer-chat>
      </div>
    </div>
  `,
  styles: [`
    .viewer-layout {
      display: flex;
      height: 100vh;
    }
    .viewer-container {
      flex: 1;
    }
    .chat-container {
      width: 400px;
      border-left: 1px solid #e5e7eb;
    }
  `]
})
export class YourViewerComponent implements AfterViewInit {
  @ViewChild('viewerChat') viewerChat!: ViewerChatComponent;

  private viewer: Autodesk.Viewing.GuiViewer3D;

  ngAfterViewInit() {
    // After your viewer is initialized, connect it to the chat
    this.initializeViewer();
  }

  private initializeViewer() {
    // Your existing viewer initialization code
    Autodesk.Viewing.Initializer({ /* options */ }, () => {
      const viewerDiv = document.getElementById('forgeViewer');
      this.viewer = new Autodesk.Viewing.GuiViewer3D(viewerDiv);
      this.viewer.start();

      // Load your model
      // ...

      // IMPORTANT: Connect viewer to chat component
      this.viewerChat.setViewer(this.viewer);
    });
  }
}
```

## API

### ViewerChatComponent

#### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `apiUrl` | string | `'http://localhost:8080'` | Backend API URL |
| `darkMode` | boolean | `false` | Enable dark theme |
| `exampleQueries` | string[] | `['Show walls', ...]` | Example queries in empty state |

#### Methods

| Method | Description |
|--------|-------------|
| `setViewer(viewer)` | Connect your Autodesk Viewer instance |
| `sendMessage(message)` | Programmatically send a message |

### ViewerActionExecutorService

If you need more control, inject the service directly:

```typescript
import { ViewerActionExecutorService } from './viewer-chat';

constructor(private actionExecutor: ViewerActionExecutorService) {}

// Set viewer
this.actionExecutor.setViewer(this.viewer);

// Execute a single action
await this.actionExecutor.executeAction({
  operation: 'isolate',
  params: { dbIds: [1, 2, 3] }
});

// Execute multiple actions
await this.actionExecutor.executeActions([
  { operation: 'searchByProperty', params: { category: 'Walls' } },
  { operation: 'fitToView', params: {} }
]);
```

## Supported Operations

### Selection
- `select` - Select elements by dbIds
- `clearSelection` - Clear selection
- `searchByProperty` - Search and select by category/property
- `selectByProperty` - Select by property value

### Visibility
- `isolate` - Isolate elements (hide others)
- `hide` - Hide elements
- `show` - Show elements
- `showAll` - Show all, clear isolation

### Camera
- `fitToView` - Zoom to fit elements
- `setCameraPreset` - Set preset view (front, back, top, bottom, left, right, iso)
- `setCamera` - Set custom camera position/target

### Section
- `createSection` - Create cutting plane (X, Y, Z)
- `clearSection` - Remove section planes

### Other
- `explode` - Explode model
- `measure` - Start measurement tool
- `clearMeasurements` - Clear measurements

## Example Queries

Users can say things like:
- "Show all walls"
- "Isolate the doors"
- "Hide MEP systems"
- "Top view"
- "Create a section on Z axis"
- "Explode the model"
- "Zoom to selection"
- "Show everything"

## Backend Requirements

The chat component requires the backend API to be running:

```bash
cd acc-dashboard-poc
python main.py
```

The backend should have the `ViewerAgent` configured to handle viewer commands.

## Styling

The component includes built-in styles. To customize:

```scss
// Override CSS variables or styles
::ng-deep .viewer-chat-container {
  // Your custom styles
}

// Or use the darkMode input for dark theme
<app-viewer-chat [darkMode]="true"></app-viewer-chat>
```

## Troubleshooting

### "Viewer not initialized"
Make sure to call `setViewer()` after your Autodesk Viewer is fully initialized:
```typescript
this.viewerChat.setViewer(this.viewer);
```

### "Cannot connect to backend"
1. Ensure the backend is running on the correct port
2. Check CORS settings in the backend
3. Verify the `apiUrl` input is correct

### "Actions not executing"
Check browser console for errors. Common issues:
- Viewer not connected
- Model not loaded yet
- Invalid element IDs
