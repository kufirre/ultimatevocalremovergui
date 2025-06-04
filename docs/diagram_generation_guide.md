# 🎨 UVR PySide6 Diagram Generation Guide

This guide provides multiple methods to generate high-quality images from the UML diagrams in our architecture documentation.

## 🚀 Quick Start Options

### Option 1: **Mermaid Live Editor** (Recommended - No Installation)
**Best for**: Quick generation, no setup required, highest quality

1. **Go to**: https://mermaid.live/
2. **Copy diagram code** from `docs/architecture_diagrams.md`
3. **Paste** into the editor
4. **Download** as PNG, SVG, or PDF

**✅ Pros**: 
- No installation required
- Real-time preview
- Multiple formats (PNG, SVG, PDF)
- High-quality output
- Free to use

### Option 2: **Local HTML Generator** (Convenient)
**Best for**: Local generation, multiple diagrams, offline use

1. **Open**: `scripts/diagram_generator.html` in your browser
2. **Select** diagram from dropdown
3. **Generate** and right-click to save image
4. **Download SVG** using the download button

**✅ Pros**:
- Works offline
- All diagrams in one place
- Easy switching between diagrams
- SVG download functionality

### Option 3: **Automated Script** (Professional)
**Best for**: Batch generation, automation, consistent output

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Generate all diagrams
./scripts/generate_diagrams.sh
```

**✅ Pros**:
- Generates all diagrams at once
- Multiple formats (PNG, SVG)
- High-resolution output (1920x1080)
- Thumbnails for previews
- Automated index generation

## 📋 Detailed Instructions

### Method 1: Mermaid Live Editor (Easiest)

1. **Navigate** to https://mermaid.live/
2. **Open** `docs/architecture_diagrams.md` in your editor
3. **Copy** any diagram code block (everything between \`\`\`mermaid and \`\`\`)
4. **Paste** into the left panel of Mermaid Live
5. **Click** "Actions" → "Download PNG" (or SVG/PDF)

**Example**: Copy this code for the System Architecture:
```mermaid
graph TB
    subgraph "Application Layer"
        A[main.py]
        A --> B[MainWindowView]
    end
    -- (rest of the diagram code) --
```

### Method 2: Local HTML Generator

1. **Open** `scripts/diagram_generator.html` in any modern browser
2. **Select** desired diagram from the dropdown
3. **Click** "Generate Diagram"
4. **Right-click** on the generated diagram → "Save image as..."
5. **Or use** "Download SVG" button for vector format

**Features**:
- Real-time rendering
- Professional styling
- Easy diagram switching
- Browser zoom for size control

### Method 3: Automated CLI Generation

**Prerequisites**:
```bash
# Install Node.js (if not already installed)
# Visit: https://nodejs.org/

# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
```

**Generate All Diagrams**:
```bash
# Run the script
./scripts/generate_diagrams.sh

# Generated files will be in:
# docs/images/diagrams/*.png (high-res)
# docs/images/diagrams/*.svg (vector)
# docs/images/diagrams/thumbnails/*.png (previews)
```

**Output Structure**:
```
docs/images/diagrams/
├── 01_system_architecture.png
├── 01_system_architecture.svg
├── 02_mvp_pattern.png
├── 02_mvp_pattern.svg
├── 03_processing_pipeline.png
├── 03_processing_pipeline.svg
├── 04_model_management.png
├── 04_model_management.svg
├── 05_audio_processing.png
├── 05_audio_processing.svg
├── 06_signal_slot.png
├── 06_signal_slot.svg
├── thumbnails/
│   ├── 01_system_architecture.png
│   └── ... (smaller versions)
└── README.md (index of all diagrams)
```

## 🎯 Recommended Workflow

### For Documentation:
1. **Use Mermaid Live Editor** for quick, high-quality images
2. **Download as PNG** for general use or SVG for scalable graphics
3. **Add to documentation** with appropriate alt text

### For Presentations:
1. **Use the CLI script** for consistent, professional output
2. **Use high-resolution PNGs** (1920x1080) for presentations
3. **Use SVGs** for web or scalable documents

### For Development:
1. **Use local HTML generator** for quick iteration
2. **Test diagram changes** before updating documentation
3. **Generate final versions** with CLI script

## 📐 Quality Settings

### **High Resolution** (for print/presentations):
- **Format**: PNG
- **Size**: 1920x1080 (or higher)
- **Background**: White
- **Scale**: 2x for crisp rendering

### **Web Optimized** (for documentation):
- **Format**: PNG or SVG
- **Size**: 800x600 for thumbnails
- **Compression**: Moderate
- **Loading**: Lazy loading for web

### **Vector Graphics** (for scalability):
- **Format**: SVG
- **Benefits**: Infinite scalability, small file size
- **Use cases**: Web, high-DPI displays, print

## 🛠 Advanced Options

### Custom Themes:
```javascript
// In Mermaid Live Editor or HTML generator
{
  "theme": "dark",        // or "forest", "neutral"
  "themeVariables": {
    "primaryColor": "#007acc",
    "fontFamily": "Arial"
  }
}
```

### Size Optimization:
```bash
# For CLI generation with custom size
mmdc -i diagram.mmd -o diagram.png -w 1600 -h 1200 --scale 1.5
```

### Batch Processing:
```bash
# Generate multiple formats
for diagram in *.mmd; do
  mmdc -i "$diagram" -o "${diagram%.mmd}.png"
  mmdc -i "$diagram" -o "${diagram%.mmd}.svg"
done
```

## 🔧 Troubleshooting

### Common Issues:

**"Mermaid CLI not found"**:
```bash
# Solution: Install Node.js and Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
```

**"Diagram doesn't render"**:
- Check syntax in Mermaid Live Editor
- Ensure proper indentation
- Verify diagram type (graph, classDiagram, sequenceDiagram)

**"Low quality images"**:
- Increase scale factor: `--scale 2`
- Use higher resolution: `-w 1920 -h 1080`
- Use SVG format for infinite scalability

**"HTML generator not working"**:
- Use modern browser (Chrome, Firefox, Safari, Edge)
- Check browser console for JavaScript errors
- Ensure internet connection for Mermaid library

## 📊 Format Comparison

| Format | Quality | File Size | Use Case | Scalability |
|--------|---------|-----------|----------|-------------|
| **PNG** | High | Medium | Documentation, Print | Fixed |
| **SVG** | Perfect | Small | Web, High-DPI | Infinite |
| **PDF** | High | Large | Print, Archive | Fixed |

## 🎉 Best Practices

1. **Use SVG** for web documentation
2. **Use high-res PNG** for presentations
3. **Include alt text** for accessibility
4. **Optimize file sizes** for web delivery
5. **Version control** generated images
6. **Automate generation** in CI/CD pipeline

## 📚 Resources

- **Mermaid Live Editor**: https://mermaid.live/
- **Mermaid Documentation**: https://mermaid-js.github.io/mermaid/
- **CLI Tool Repository**: https://github.com/mermaid-js/mermaid-cli
- **Syntax Reference**: https://mermaid-js.github.io/mermaid/#/README

---

*This guide provides comprehensive options for generating professional diagrams from your UVR PySide6 architecture documentation. Choose the method that best fits your workflow and requirements.* 