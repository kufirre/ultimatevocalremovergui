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
