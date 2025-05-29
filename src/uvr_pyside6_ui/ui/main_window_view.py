from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStatusBar, QLabel, QMessageBox,
    QApplication, QScrollArea, QPushButton, QHBoxLayout, QFrame  # Added QScrollArea, QPushButton, QHBoxLayout, QFrame
)
from PySide6.QtGui import QAction, QIcon  # Added QIcon
from PySide6.QtCore import QSize, Slot  # Added QSize

# ... (all other view/presenter imports as in response #37) ...
from .file_io_view import FileIOView
from .file_io_presenter import FileIOPresenter
from .processing_settings_view import ProcessingSettingsView
from .processing_settings_presenter import ProcessingSettingsPresenter
from .model_selection_view import ModelSelectionView
from .model_selection_presenter import ModelSelectionPresenter
from .vr_arch_settings_view import VRArchSettingsView
from .vr_arch_settings_presenter import VRArchSettingsPresenter
from .mdx_net_settings_view import MDXNetSettingsView
from .mdx_net_settings_presenter import MDXNetSettingsPresenter
from .demucs_settings_view import DemucsSettingsView
from .demucs_settings_presenter import DemucsSettingsPresenter
from .ensemble_settings_view import EnsembleSettingsView
from .ensemble_settings_presenter import EnsembleSettingsPresenter
from .execution_control_view import ExecutionControlView
from .execution_control_presenter import ExecutionControlPresenter
from .settings_dialog_presenter import SettingsDialogPresenter
from ..core.uvr_core_adapter import UVRCoreAdapter


class MainWindowView(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("UVR - PySide6 Edition")
        self.setGeometry(100, 100, 680, 720)  # Adjusted default size inspired by UVR.py WIDTH

        # --- Main Content Container for ScrollArea ---
        self.main_content_container = QWidget()
        self.main_layout = QVBoxLayout(self.main_content_container)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(10)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.presenters = {}
        self.adapter = UVRCoreAdapter(self)
        self.settings_dialog_presenter = SettingsDialogPresenter(adapter=self.adapter, parent_qt_object=self)

        # --- Top Bar for Settings Button (Optional, or add to existing area) ---
        # For now, let's add it to the main layout for simplicity.
        # A QToolBar would be another option.

        # --- Instantiate UI Modules and add them to main_layout ---
        # ... (File I/O, Specific Settings Panels, Model Selection, Processing Settings as in response #37) ...
        # File I/O
        self.file_io_view = FileIOView();
        self.presenters["file_io"] = FileIOPresenter(view=self.file_io_view)
        self.main_layout.addWidget(self.file_io_view)
        # Specific Settings Panels
        self.vr_arch_view = VRArchSettingsView();
        self.presenters["vr_arch"] = VRArchSettingsPresenter(view=self.vr_arch_view)
        self.mdx_net_view = MDXNetSettingsView();
        self.presenters["mdx_net"] = MDXNetSettingsPresenter(view=self.mdx_net_view)
        self.demucs_view = DemucsSettingsView();
        self.presenters["demucs"] = DemucsSettingsPresenter(view=self.demucs_view)
        self.ensemble_view = EnsembleSettingsView();
        self.presenters["ensemble"] = EnsembleSettingsPresenter(view=self.ensemble_view, adapter=self.adapter)
        # Model Selection
        self.model_selection_view = ModelSelectionView()
        self.presenters["model_selection"] = ModelSelectionPresenter(view=self.model_selection_view,
                                                                     adapter=self.adapter)
        self.presenters["model_selection"].request_show_download_center.connect(self._open_download_center_tab)
        self.adapter.download_finished.connect(self.presenters["model_selection"]._on_model_downloaded_elsewhere)
        self.model_selection_view.add_settings_panel("VR Arch", self.vr_arch_view)
        self.model_selection_view.add_settings_panel("MDX-Net", self.mdx_net_view)
        self.model_selection_view.add_settings_panel("Demucs", self.demucs_view)
        self.model_selection_view.add_settings_panel("Ensemble", self.ensemble_view)
        self.main_layout.addWidget(self.model_selection_view)
        # Processing Settings (now includes new checkboxes)
        self.processing_settings_view = ProcessingSettingsView()
        self.presenters["processing_settings"] = ProcessingSettingsPresenter(view=self.processing_settings_view)
        self.main_layout.addWidget(self.processing_settings_view)

        # --- Execution Control and Settings Button Row ---
        bottom_controls_layout = QHBoxLayout()
        self.execution_control_view = ExecutionControlView()
        self.presenters["execution"] = ExecutionControlPresenter(
            view=self.execution_control_view,
            main_window_presenters=self.presenters,
            adapter=self.adapter
        )
        bottom_controls_layout.addWidget(self.execution_control_view, 1)
        # Settings button is now removed. Access settings via Edit > Preferences menu.
        self.main_layout.addLayout(bottom_controls_layout)

        self.main_layout.addStretch(0)

        self.main_content_container.setLayout(self.main_layout)

        # Settings Button previously in status_bar is also removed.
        # self.settings_button = QPushButton()
        # ... (rest of old status_bar button code removed)
        # self.status_bar.addPermanentWidget(self.settings_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.main_content_container)
        self.scroll_area.setFrameShape(QFrame.NoFrame)  # Cleaner look

        self.setCentralWidget(self.scroll_area)

        self._create_menu_bar()

        if self.model_selection_view.method_combo.count() > 0:
            initial_method = self.model_selection_view.method_combo.currentText()
            if initial_method:
                self.presenters["model_selection"].handle_method_change(initial_method)
        else:
            self.presenters["model_selection"].handle_method_change("")

        print("MainWindowView Fully Initialized with ScrollArea, new checkboxes, and settings button.")

    # ... (_create_menu_bar, _open_download_center_tab, _quit_application,
    #      _show_about_dialog, show_status_message methods remain unchanged from response #37) ...
    def _create_menu_bar(self):
        menu_bar = self.menuBar();
        menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu("&File");
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q");
        quit_action.triggered.connect(self._quit_application)
        file_menu.addAction(quit_action);
        edit_menu = menu_bar.addMenu("&Edit")
        prefs_action = QAction("&Preferences...", self);
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.triggered.connect(lambda: self.settings_dialog_presenter.show_dialog(default_model_type=None))
        edit_menu.addAction(prefs_action);
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self);
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    @Slot(str)
    def _open_download_center_tab(self, originating_method: str):
        self.settings_dialog_presenter.show_dialog(exec_dialog=False, default_model_type=originating_method)
        if self.settings_dialog_presenter.view: self.settings_dialog_presenter.view.tab_widget.setCurrentIndex(2)

    def _quit_application(self):
        app = QApplication.instance(); app.quit() if app else None

    def _show_about_dialog(self):
        QMessageBox.about(self, "About UVR - PySide6 Edition", "UVR GUI PySide6 Refactor.")

    def show_status_message(self, message, timeout=0):
        self.status_bar.showMessage(message, timeout)
