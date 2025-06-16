"""View for the download center functionality."""

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from uvr_pyside6_ui.core.logger_utils import get_logger

logger = get_logger(__name__)


class DownloadCenterView(QWidget):
    """View for the download center tab."""

    # Signals
    download_button_clicked = Signal()
    download_stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_download_center_ui()

    def _create_download_center_ui(self):
        """Create the Download Center tab with clean, simple design matching settings guide."""
        dc_main_layout = QVBoxLayout(self)
        dc_main_layout.setSpacing(20)
        dc_main_layout.setContentsMargins(20, 20, 20, 20)

        # Model Selection section - matching settings guide style
        selection_group = QGroupBox("Model Selection")
        selection_layout = QFormLayout(selection_group)
        selection_layout.setSpacing(15)

        # Architecture dropdown
        self.dc_architecture_combo = QComboBox()
        self.dc_architecture_combo.addItems(["VR Architecture", "MDX-Net", "Demucs"])
        self.dc_architecture_combo.setCurrentText("VR Architecture")
        self.dc_architecture_combo.currentTextChanged.connect(
            self._on_architecture_changed
        )
        selection_layout.addRow("Architecture:", self.dc_architecture_combo)

        # Model dropdown
        self.dc_model_combo = QComboBox()
        self.dc_model_combo.currentTextChanged.connect(
            self._on_dc_list_selection_changed
        )
        selection_layout.addRow("Model:", self.dc_model_combo)

        dc_main_layout.addWidget(selection_group)

        # Download section - matching settings guide style
        download_group = QGroupBox("Download")
        download_layout = QVBoxLayout(download_group)
        download_layout.setSpacing(15)

        # Download button
        self.dc_download_btn = QPushButton("Download Selected Model")
        try:
            download_icon = QIcon(":/uvr/img/download.png")
            if not download_icon.isNull():
                self.dc_download_btn.setIcon(download_icon)
                self.dc_download_btn.setIconSize(QSize(20, 20))
        except Exception:
            pass

        self.dc_download_btn.clicked.connect(self.download_button_clicked.emit)
        download_layout.addWidget(self.dc_download_btn)

        dc_main_layout.addWidget(download_group)

        # Progress section - matching settings guide style
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(10)

        # Progress info label with text wrapping
        self.dc_progress_info_label = QLabel("Ready to download")
        self.dc_progress_info_label.setWordWrap(True)
        self.dc_progress_info_label.setMaximumHeight(
            60
        )  # Limit height to prevent UI stretching
        progress_layout.addWidget(self.dc_progress_info_label)

        # Progress percentage and bar container
        progress_container = QHBoxLayout()

        # Progress bar with simple styling
        self.dc_progress_bar = QProgressBar()
        self.dc_progress_bar.setMinimum(0)
        self.dc_progress_bar.setMaximum(100)
        self.dc_progress_bar.setValue(0)
        progress_container.addWidget(self.dc_progress_bar, 1)

        # Progress percentage label
        self.dc_progress_percent_label = QLabel("0%")
        self.dc_progress_percent_label.setMinimumWidth(40)
        progress_container.addWidget(self.dc_progress_percent_label)

        progress_layout.addLayout(progress_container)

        dc_main_layout.addWidget(progress_group)

        # Control buttons section - matching settings guide style
        controls_group = QGroupBox("Actions")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setSpacing(10)

        # Stop download button
        self.dc_stop_btn = QPushButton("Stop Download")
        self.dc_stop_btn.setEnabled(False)
        self.dc_stop_btn.clicked.connect(self.download_stop_requested.emit)
        controls_layout.addWidget(self.dc_stop_btn, 0, 0)

        # Refresh list button
        self.dc_refresh_btn = QPushButton("Refresh List")
        controls_layout.addWidget(self.dc_refresh_btn, 0, 1)

        # Download key button
        self.dc_key_btn = QPushButton("VIP Access")
        try:
            key_icon = QIcon(":/uvr/img/key.png")
            if not key_icon.isNull():
                self.dc_key_btn.setIcon(key_icon)
                self.dc_key_btn.setIconSize(QSize(16, 16))
        except Exception:
            pass
        controls_layout.addWidget(self.dc_key_btn, 1, 0)

        # Manual download button
        self.dc_manual_btn = QPushButton("Manual Download")
        controls_layout.addWidget(self.dc_manual_btn, 1, 1)

        dc_main_layout.addWidget(controls_group)

        dc_main_layout.addStretch()

    def _on_architecture_changed(self):
        """Handle architecture dropdown changes and update model list."""
        self._populate_models_for_architecture()
        self._on_dc_list_selection_changed()

    def _populate_models_for_architecture(self):
        """Populate the model dropdown based on selected architecture."""
        if not hasattr(self, "dc_architecture_combo") or not hasattr(
            self, "dc_model_combo"
        ):
            return

        architecture = self.dc_architecture_combo.currentText()

        # Get models for the selected architecture
        if architecture == "VR Architecture":
            models = getattr(self, "_vr_models", [])
        elif architecture == "MDX-Net":
            models = getattr(self, "_mdx_models", [])
        elif architecture == "Demucs":
            models = getattr(self, "_demucs_models", [])
        else:
            models = []

        # Update model dropdown
        self.dc_model_combo.clear()
        if models:
            self.dc_model_combo.addItems(models)
        else:
            self.dc_model_combo.addItems(["No models available"])

    def _on_model_type_changed(self):
        """Handle model type changes - legacy method for compatibility."""
        self._on_dc_list_selection_changed()

    def _on_dc_list_selection_changed(self):
        """Handle model selection changes."""
        architecture = self.get_selected_model_type()
        model = self.get_selected_model()
        self.dc_download_btn.setEnabled(
            bool(architecture and model and model != "No models available")
        )

    def get_selected_model_type(self):
        """Get the currently selected architecture."""
        if hasattr(self, "dc_architecture_combo"):
            return self.dc_architecture_combo.currentText()
        return None

    def get_selected_model(self):
        """Get the currently selected model."""
        if hasattr(self, "dc_model_combo"):
            model = self.dc_model_combo.currentText()
            return model if model != "No models available" else None
        return None

    def set_vr_models(self, models):
        """Set VR models and update dropdown if VR is selected."""
        self._vr_models = models
        if (
            hasattr(self, "dc_architecture_combo")
            and self.dc_architecture_combo.currentText() == "VR Architecture"
        ):
            self._populate_models_for_architecture()

    def set_mdx_models(self, models):
        """Set MDX models and update dropdown if MDX is selected."""
        self._mdx_models = models
        if (
            hasattr(self, "dc_architecture_combo")
            and self.dc_architecture_combo.currentText() == "MDX-Net"
        ):
            self._populate_models_for_architecture()

    def set_demucs_models(self, models):
        """Set Demucs models and update dropdown if Demucs is selected."""
        self._demucs_models = models
        if (
            hasattr(self, "dc_architecture_combo")
            and self.dc_architecture_combo.currentText() == "Demucs"
        ):
            self._populate_models_for_architecture()

    def set_download_in_progress_state(self, in_progress: bool):
        """Set UI state for download progress."""
        self.dc_download_btn.setEnabled(not in_progress)
        self.dc_stop_btn.setEnabled(in_progress)

        # Disable model selection during download
        self.dc_architecture_combo.setEnabled(not in_progress)
        self.dc_model_combo.setEnabled(not in_progress)

    def show_status_message(self, message: str, duration: int = 3000):
        """Show a status message (for compatibility with presenter)."""
        # Truncate very long messages to prevent UI stretching
        if len(message) > 100:
            display_message = message[:97] + "..."
            logger.info(f"Status (truncated): {display_message}")
            logger.debug(f"Full status message: {message}")
        else:
            display_message = message
            logger.info(f"Status: {message}")

        # Update progress label if available
        if hasattr(self, "dc_progress_info_label"):
            self.dc_progress_info_label.setText(display_message)

    def isVisible(self):
        """Check if the view is visible."""
        return super().isVisible() and self.parent() is not None
