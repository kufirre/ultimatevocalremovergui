# UVR PySide6 Architecture Diagrams

This document contains UML diagrams that illustrate the architecture and interactions within the UVR PySide6 application.

## 1. Overall System Architecture

```mermaid
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
        N1[SeparateLogicBase]
        N2[SeparateVRLogic]
        N3[SeparateMDXLogic]
        N4[SeparateMDXCLogic]
        N5[SeparateDemucsLogic]
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
    L --> N1
    L --> N2
    L --> N3
    L --> N4
    L --> N5
    L --> O
    L --> P
    P --> Q
    
    L --> U
    N1 --> S
    N2 --> S
    N3 --> S
    N4 --> S
    N5 --> S
    O --> S
    O --> T
    
    style A fill:#e1f5fe
    style L fill:#f3e5f5
    style N1 fill:#fff3e0
    style N2 fill:#fff3e0
    style N3 fill:#fff3e0
    style N4 fill:#fff3e0
    style N5 fill:#fff3e0
    style O fill:#fff3e0
```

## 2. MVP (Model-View-Presenter) Pattern Implementation

```mermaid
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
```

## 3. Core Processing Pipeline

```mermaid
sequenceDiagram
    participant UI as MainWindowView
    participant EP as ExecutionControlPresenter
    participant CA as UVRCoreAdapter
    participant PT as ProcessingThread
    participant SL as SeparationLogicModule
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
```

## 4. Model Management System

```mermaid
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
```

## 5. Settings and Configuration Management

```mermaid
classDiagram
    class SettingsDialogView {
        -tab_widget: QTabWidget
        -download_tab: QWidget
        -preferences_tab: QWidget
        +show_dialog()
        +setup_download_tab()
    }
    
    class SettingsDialogPresenter {
        -view: SettingsDialogView
        -adapter: UVRCoreAdapter
        +show_dialog()
        +handle_download_request()
        +populate_download_models()
    }
    
    class VRArchSettingsView {
        -aggression_slider: QSlider
        -window_size_combo: QComboBox
        +get_settings()
        +set_settings()
    }
    
    class VRArchSettingsPresenter {
        -view: VRArchSettingsView
        +get_current_settings()
        +validate_settings()
    }
    
    class MDXNetSettingsView {
        -overlap_slider: QSlider
        -segment_size_combo: QComboBox
        +get_settings()
        +set_settings()
    }
    
    class MDXNetSettingsPresenter {
        -view: MDXNetSettingsView
        +get_current_settings()
        +validate_settings()
    }
    
    class ProcessingSettingsView {
        -gpu_checkbox: QCheckBox
        -tta_checkbox: QCheckBox
        -output_format_combo: QComboBox
        +get_settings()
    }
    
    class ProcessingSettingsPresenter {
        -view: ProcessingSettingsView
        +get_current_settings()
        +apply_settings()
    }
    
    SettingsDialogPresenter "1" -- "1" SettingsDialogView
    VRArchSettingsPresenter "1" -- "1" VRArchSettingsView
    MDXNetSettingsPresenter "1" -- "1" MDXNetSettingsView
    ProcessingSettingsPresenter "1" -- "1" ProcessingSettingsView
```

## 6. Audio Processing Components

```mermaid
graph LR
    subgraph "Audio Input"
        A[Audio File]
        B[File Validation]
        C[Format Conversion]
    end
    
    subgraph "Separation Logic Modules"
        D[VR Logic Module]
        E[MDX Logic Module]
        F[MDX-C Logic Module]
        G[Demucs Logic Module]
        H[Base Logic Utils]
        I[Ensemble Processing]
    end
    
    subgraph "Model Processing"
        J[Model Loading]
        K[Inference Engine]
        L[Post-processing]
    end
    
    subgraph "Output Generation"
        M[Stem Combination]
        N[Format Export]
        O[File Writing]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    
    D --> J
    E --> J
    F --> J
    
    J --> K
    K --> L
    L --> M
    
    D --> I
    E --> I
    F --> I
    I --> M
    
    M --> N
    N --> O
    
    style D fill:#ffeb3b
    style E fill:#ffeb3b
    style F fill:#ffeb3b
    style G fill:#ffeb3b
    style H fill:#ffeb3b
    style I fill:#4caf50
```

## 7. Signal/Slot Communication Pattern

```mermaid
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
```

## Key Architecture Principles

### 1. **MVP Pattern**
- **Views**: Pure UI components (Qt widgets)
- **Presenters**: Business logic and event handling
- **Model**: Core adapter and data classes

### 2. **Signal-Slot Communication**
- Loose coupling between components
- Thread-safe communication
- Event-driven architecture

### 3. **Separation of Concerns**
- UI logic separate from business logic
- Processing logic isolated in worker threads
- Model management centralized in adapter

### 4. **Thread Safety**
- Heavy processing in worker threads
- Qt signals for cross-thread communication
- Progress updates via signal/slot mechanism

### 5. **Modular Design**
- Method-specific settings components
- Pluggable audio processing backends
- Extensible model support

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `main.py` | Application entry point, resource loading |
| `MainWindowView` | Main UI container, menu management |
| `UVRCoreAdapter` | Central business logic coordinator |
| `ProcessingWorker` | Audio processing in separate thread |
| `ModelData` | Model configuration and validation |
| **Separation Logic Modules** | **Modular audio separation implementations** |
| `SeparateLogicBase` | Common utilities and base separator class |
| `SeparateVRLogic` | VR architecture audio separation |
| `SeparateMDXLogic` | MDX-Net ONNX model processing |
| `SeparateMDXCLogic` | MDX-C checkpoint model processing |
| `SeparateDemucsLogic` | Demucs v1/v2/v3/v4 processing |
| `DownloadManager` | Model download functionality |
| `Settings Views/Presenters` | Method-specific configuration UI |

This architecture provides a clean, maintainable, and extensible foundation for the UVR PySide6 application. 