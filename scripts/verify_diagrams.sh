#!/bin/bash
# Verify that all diagram images exist and have reasonable file sizes

set -e

echo "🔍 Verifying diagram images..."

DIAGRAM_DIR="docs/images/diagrams"
THUMBNAIL_DIR="$DIAGRAM_DIR/thumbnails"

# Check if directories exist
if [ ! -d "$DIAGRAM_DIR" ]; then
    echo "❌ Diagram directory not found: $DIAGRAM_DIR"
    exit 1
fi

if [ ! -d "$THUMBNAIL_DIR" ]; then
    echo "❌ Thumbnail directory not found: $THUMBNAIL_DIR"
    exit 1
fi

# Expected diagrams
declare -a diagrams=(
    "01_system_architecture"
    "02_mvp_pattern"
    "03_processing_pipeline"
    "04_model_management"
    "05_audio_processing"
    "06_signal_slot"
)

echo "📋 Checking main diagrams..."

# Verify main diagrams
for diagram in "${diagrams[@]}"; do
    png_file="$DIAGRAM_DIR/$diagram.png"
    svg_file="$DIAGRAM_DIR/$diagram.svg"
    thumb_file="$THUMBNAIL_DIR/$diagram.png"
    
    # Check PNG
    if [ -f "$png_file" ]; then
        size=$(du -h "$png_file" | cut -f1)
        echo "  ✅ $diagram.png ($size)"
    else
        echo "  ❌ Missing: $png_file"
    fi
    
    # Check SVG
    if [ -f "$svg_file" ]; then
        size=$(du -h "$svg_file" | cut -f1)
        echo "  ✅ $diagram.svg ($size)"
    else
        echo "  ❌ Missing: $svg_file"
    fi
    
    # Check Thumbnail
    if [ -f "$thumb_file" ]; then
        size=$(du -h "$thumb_file" | cut -f1)
        echo "  ✅ $diagram.png thumbnail ($size)"
    else
        echo "  ❌ Missing: $thumb_file"
    fi
done

echo ""
echo "📊 Summary:"
png_count=$(find "$DIAGRAM_DIR" -name "*.png" -not -path "*/thumbnails/*" | wc -l)
svg_count=$(find "$DIAGRAM_DIR" -name "*.svg" | wc -l)
thumb_count=$(find "$THUMBNAIL_DIR" -name "*.png" | wc -l)

echo "  📷 Main PNGs: $png_count/6"
echo "  🖼️  SVGs: $svg_count/6"
echo "  🔍 Thumbnails: $thumb_count/6"

# Check README exists
if [ -f "$DIAGRAM_DIR/README.md" ]; then
    echo "  📋 Index: ✅"
else
    echo "  📋 Index: ❌"
fi

# Check total directory size
total_size=$(du -sh "$DIAGRAM_DIR" | cut -f1)
echo "  💾 Total size: $total_size"

echo ""
if [ "$png_count" -eq 6 ] && [ "$svg_count" -eq 6 ] && [ "$thumb_count" -eq 6 ]; then
    echo "✅ All diagrams verified successfully!"
    echo ""
    echo "🎯 Next steps:"
    echo "   1. View diagrams in GitHub/GitLab: They'll render automatically"
    echo "   2. Use interactive viewer: Open scripts/diagram_generator.html"
    echo "   3. Regenerate if needed: ./scripts/generate_diagrams.sh"
    echo "   4. Edit source diagrams: docs/architecture_diagrams.md"
else
    echo "❌ Some diagrams are missing. Run ./scripts/generate_diagrams.sh"
    exit 1
fi 