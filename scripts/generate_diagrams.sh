#!/bin/bash
# Generate diagram images from Mermaid code in documentation
# Requires: npm install -g @mermaid-js/mermaid-cli

set -e

echo "🎨 Generating UML diagrams from documentation..."

# Create output directory
mkdir -p docs/images/diagrams

# Extract and create individual diagram files
echo "📝 Extracting diagram code from documentation..."

# Create temporary directory for mermaid files
TMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TMP_DIR"

# Extract System Architecture diagram
cat > "$TMP_DIR/01_system_architecture.mmd" << 'EOF'
graph TB
    subgraph "Application Layer"
        A[main.py]
        A --> B[MainWindowView]
    end
    
    subgraph "UI Layer (MVP Pattern)"
        B --> C[Model Selection View/Presenter]
        B --> D[File I/O View/Presenter]
        B --> E[Processing Settings View/Presenter]
        B --> F[Execution Control View/Presenter]
        B --> G[Settings Dialog View/Presenter]
        
        subgraph "Method-Specific UI"
            H[VR Arch Settings]
            I[MDX-Net Settings]
            J[Demucs Settings]
            K[Ensemble Settings]
        end
        
        C --> H
        C --> I
        C --> J
        C --> K
    end
    
    subgraph "Core Business Logic"
        L[UVRCoreAdapter]
        M[ModelData]
        N[SeparateLogic]
        O[ProcessingWorker]
        P[ModelDownloader]
        Q[DownloadWorker]
    end
    
    subgraph "External Dependencies"
        R[Qt Framework]
        S[Audio Processing Libraries]
        T[ML Models]
        U[File System]
    end
    
    B --> L
    F --> L
    G --> L
    L --> M
    L --> N
    L --> O
    L --> P
    P --> Q
    
    L --> U
    N --> S
    O --> S
    O --> T
    
    style A fill:#e1f5fe
    style L fill:#f3e5f5
    style N fill:#fff3e0
    style O fill:#fff3e0
EOF

# Extract MVP Pattern diagram
cat > "$TMP_DIR/02_mvp_pattern.mmd" << 'EOF'
classDiagram
    class MainWindowView {
        -presenters: dict
        -adapter: UVRCoreAdapter
        -settings_dialog_presenter: SettingsDialogPresenter
        +__init__()
        +show_status_message()
        +_create_menu_bar()
        +_open_download_center_tab()
    }
    
    class ModelSelectionView {
        -method_combo: QComboBox
        -model_combo: QComboBox
        -settings_stack: QStackedWidget
        +add_settings_panel()
        +get_selected_method()
        +get_selected_model()
    }
    
    class ModelSelectionPresenter {
        -view: ModelSelectionView
        -adapter: UVRCoreAdapter
        +handle_method_change()
        +handle_model_change()
        +refresh_models()
        +request_show_download_center: Signal
    }
    
    class ExecutionControlView {
        -start_button: QPushButton
        -stop_button: QPushButton
        -progress_bar: QProgressBar
        +update_progress()
        +set_processing_state()
    }
    
    class ExecutionControlPresenter {
        -view: ExecutionControlView
        -main_window_presenters: dict
        -adapter: UVRCoreAdapter
        +start_processing()
        +stop_processing()
        +on_progress_updated()
    }
    
    class UVRCoreAdapter {
        +progress_updated: Signal
        +processing_finished: Signal
        +download_progress: Signal
        +model_download_completed: Signal
        -processing_thread: ProcessingThread
        -download_manager: DownloadManager
        +get_available_methods()
        +get_available_models()
        +start_processing()
        +download_model()
    }
    
    MainWindowView "1" -- "1..*" ModelSelectionPresenter
    MainWindowView "1" -- "1" ExecutionControlPresenter
    MainWindowView "1" -- "1" UVRCoreAdapter
    
    ModelSelectionPresenter "1" -- "1" ModelSelectionView
    ModelSelectionPresenter "1" -- "1" UVRCoreAdapter
    
    ExecutionControlPresenter "1" -- "1" ExecutionControlView
    ExecutionControlPresenter "1" -- "1" UVRCoreAdapter
EOF

# Extract Processing Pipeline diagram
cat > "$TMP_DIR/03_processing_pipeline.mmd" << 'EOF'
sequenceDiagram
    participant UI as MainWindowView
    participant EP as ExecutionControlPresenter
    participant CA as UVRCoreAdapter
    participant PT as ProcessingThread
    participant SL as SeparateLogic
    participant MD as ModelData
    
    UI->>EP: User clicks Start
    EP->>EP: Gather settings from all presenters
    EP->>CA: start_processing(settings_dict)
    
    CA->>PT: Create ProcessingThread
    CA->>PT: Connect signals
    PT->>PT: start()
    
    PT->>MD: Load model data
    MD-->>PT: Model configuration
    
    PT->>SL: Initialize separation logic
    PT->>SL: Process audio files
    
    loop For each audio chunk
        SL->>SL: Separate audio
        SL->>PT: Progress update
        PT->>CA: progress_updated signal
        CA->>EP: progress_updated signal
        EP->>UI: Update progress bar
    end
    
    SL-->>PT: Processing complete
    PT->>CA: processing_finished signal
    CA->>EP: processing_finished signal
    EP->>UI: Reset UI state
EOF

# Extract Model Management diagram
cat > "$TMP_DIR/04_model_management.mmd" << 'EOF'
classDiagram
    class UVRCoreAdapter {
        -_online_catalog_data_cache: dict
        -download_manager: DownloadManager
        +get_online_catalog()
        +get_available_models()
        +get_downloadable_models_for_type()
        +download_model()
    }
    
    class ModelDownloader {
        +fetch_online_model_catalog()
        +get_cache_file_path()
        +is_cache_valid()
    }
    
    class DownloadManager {
        +download_progress: Signal
        +download_finished: Signal
        +download_model()
        +_download_file()
    }
    
    class ModelData {
        -model_name: str
        -selected_process_method: str
        -is_secondary_model: bool
        +get_model_path()
        +get_model_data()
        +validate_model()
    }
    
    class ProcessingWorker {
        +progress_updated: Signal
        +processing_finished: Signal
        -model_data: ModelData
        +run()
        +process_audio()
    }
    
    UVRCoreAdapter "1" -- "1" DownloadManager
    UVRCoreAdapter "1" -- "*" ModelData
    UVRCoreAdapter --> ModelDownloader : uses
    
    ProcessingWorker "1" -- "1" ModelData
    DownloadManager --> ModelDownloader : uses
EOF

# Extract Audio Processing diagram
cat > "$TMP_DIR/05_audio_processing.mmd" << 'EOF'
graph LR
    subgraph "Audio Input"
        A[Audio File]
        B[File Validation]
        C[Format Conversion]
    end
    
    subgraph "Separation Logic"
        D[VR Architecture]
        E[MDX-Net]
        F[Demucs]
        G[Ensemble Processing]
    end
    
    subgraph "Model Processing"
        H[Model Loading]
        I[Inference Engine]
        J[Post-processing]
    end
    
    subgraph "Output Generation"
        K[Stem Combination]
        L[Format Export]
        M[File Writing]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    
    D --> H
    E --> H
    F --> H
    
    H --> I
    I --> J
    J --> K
    
    D --> G
    E --> G
    F --> G
    G --> K
    
    K --> L
    L --> M
    
    style D fill:#ffeb3b
    style E fill:#ffeb3b
    style F fill:#ffeb3b
    style G fill:#4caf50
EOF

# Extract Signal/Slot diagram
cat > "$TMP_DIR/06_signal_slot.mmd" << 'EOF'
graph TD
    subgraph "UI Events"
        A[User Actions]
        B[Menu Selections]
        C[Button Clicks]
    end
    
    subgraph "Presenter Layer"
        D[Method Change]
        E[Model Selection]
        F[Start Processing]
        G[Download Request]
    end
    
    subgraph "Core Adapter Signals"
        H[progress_updated]
        I[processing_finished]
        J[download_progress]
        K[model_download_completed]
    end
    
    subgraph "Worker Threads"
        L[ProcessingThread]
        M[DownloadManager]
    end
    
    subgraph "UI Updates"
        N[Progress Bar]
        O[Status Messages]
        P[Model Lists]
        Q[Button States]
    end
    
    A --> D
    B --> E
    C --> F
    
    D --> H
    E --> I
    F --> J
    G --> K
    
    H --> L
    I --> L
    J --> M
    K --> M
    
    L --> N
    L --> O
    M --> P
    M --> Q
    
    style H fill:#e3f2fd
    style I fill:#e3f2fd
    style J fill:#e3f2fd
    style K fill:#e3f2fd
EOF

# Check if mermaid CLI is available
if ! command -v mmdc &> /dev/null; then
    echo "❌ Mermaid CLI not found. Please install it:"
    echo "   npm install -g @mermaid-js/mermaid-cli"
    echo ""
    echo "📋 Alternative options:"
    echo "   1. Use Mermaid Live Editor: https://mermaid.live/"
    echo "   2. Copy diagram code from $TMP_DIR/ and paste online"
    echo ""
    echo "📁 Diagram files created in: $TMP_DIR"
    echo "   You can manually convert these using online tools."
    exit 1
fi

# Generate images using mermaid CLI
echo "🖼️ Generating PNG images..."

# Configuration for high-quality output
CONFIG_FILE="$TMP_DIR/config.json"
cat > "$CONFIG_FILE" << 'EOF'
{
  "theme": "default",
  "width": 1920,
  "height": 1080,
  "backgroundColor": "white",
  "scale": 2
}
EOF

# Generate each diagram
declare -a diagrams=(
    "01_system_architecture:System Architecture"
    "02_mvp_pattern:MVP Pattern Implementation" 
    "03_processing_pipeline:Processing Pipeline"
    "04_model_management:Model Management System"
    "05_audio_processing:Audio Processing Components"
    "06_signal_slot:Signal-Slot Communication"
)

for diagram in "${diagrams[@]}"; do
    IFS=':' read -r filename title <<< "$diagram"
    echo "   Generating: $title..."
    
    mmdc -i "$TMP_DIR/$filename.mmd" \
         -o "docs/images/diagrams/$filename.png" \
         -c "$CONFIG_FILE" \
         --quiet
    
    # Also generate SVG for scalability
    mmdc -i "$TMP_DIR/$filename.mmd" \
         -o "docs/images/diagrams/$filename.svg" \
         -c "$CONFIG_FILE" \
         --quiet
done

# Generate a thumbnail version for README
echo "🖼️ Generating thumbnail images..."
mkdir -p docs/images/diagrams/thumbnails

for diagram in "${diagrams[@]}"; do
    IFS=':' read -r filename title <<< "$diagram"
    
    # Create smaller version for README/previews - fix parameter format
    mmdc -i "$TMP_DIR/$filename.mmd" \
         -o "docs/images/diagrams/thumbnails/$filename.png" \
         -w 800 -H 600 \
         -s 1 \
         --quiet
done

# Create index file with all diagrams
echo "📋 Creating diagram index..."
cat > "docs/images/diagrams/README.md" << 'EOF'
# UVR PySide6 Architecture Diagrams

This directory contains auto-generated diagrams from the architecture documentation.

## Available Diagrams

### 1. System Architecture
![System Architecture](01_system_architecture.png)

### 2. MVP Pattern Implementation
![MVP Pattern](02_mvp_pattern.png)

### 3. Processing Pipeline
![Processing Pipeline](03_processing_pipeline.png)

### 4. Model Management System
![Model Management](04_model_management.png)

### 5. Audio Processing Components
![Audio Processing](05_audio_processing.png)

### 6. Signal/Slot Communication
![Signal-Slot Communication](06_signal_slot.png)

## File Formats

- **PNG**: High-resolution images (1920x1080)
- **SVG**: Vector graphics (scalable)
- **Thumbnails**: Smaller versions (800x600) for previews

## Regenerating Diagrams

To regenerate these diagrams:

```bash
# Install Mermaid CLI (if not already installed)
npm install -g @mermaid-js/mermaid-cli

# Run the generation script
./scripts/generate_diagrams.sh
```

## Source

All diagrams are generated from the Mermaid code in `docs/architecture_diagrams.md`.
EOF

# Cleanup
rm -rf "$TMP_DIR"

echo "✅ Diagram generation complete!"
echo ""
echo "📁 Generated files:"
echo "   - PNG images: docs/images/diagrams/*.png"
echo "   - SVG images: docs/images/diagrams/*.svg" 
echo "   - Thumbnails: docs/images/diagrams/thumbnails/*.png"
echo "   - Index: docs/images/diagrams/README.md"
echo ""
echo "🌐 For manual generation, visit: https://mermaid.live/" 