# ... (all necessary imports including SettingsDialogPresenter, UVRCoreAdapter, etc.) ...
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStatusBar, QMessageBox,
    QApplication
)
from PySide6.QtGui import QAction

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
from .settings_dialog_presenter import SettingsDialogPresenter  # Ensure this is imported
from ..core.uvr_core_adapter import UVRCoreAdapter  # Ensure this is imported


# ... (all necessary imports ...)

class MainWindowView(QMainWindow):
    def __init__(self, parent=None):
        # ... (all previous setup code for status bar, adapter, settings_dialog_presenter) ...
        super().__init__(parent)

        self.setWindowTitle("UVR - PySide6 Edition")
        self.setGeometry(100, 100, 800, 800)

        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.presenters = {}
        self.adapter = UVRCoreAdapter(self)
        self.settings_dialog_presenter = SettingsDialogPresenter(self)

        # File I/O
        self.file_io_view = FileIOView()
        self.presenters["file_io"] = FileIOPresenter(view=self.file_io_view)
        self.main_layout.addWidget(self.file_io_view)

        # Specific Settings Panels
        self.vr_arch_view = VRArchSettingsView()
        self.presenters["vr_arch"] = VRArchSettingsPresenter(view=self.vr_arch_view)
        self.mdx_net_view = MDXNetSettingsView()
        self.presenters["mdx_net"] = MDXNetSettingsPresenter(view=self.mdx_net_view)
        self.demucs_view = DemucsSettingsView()
        self.presenters["demucs"] = DemucsSettingsPresenter(view=self.demucs_view)
        self.ensemble_view = EnsembleSettingsView()
        self.presenters["ensemble"] = EnsembleSettingsPresenter(view=self.ensemble_view)

        # Model Selection Module
        self.model_selection_view = ModelSelectionView()
        self.presenters["model_selection"] = ModelSelectionPresenter(
            view=self.model_selection_view,
            adapter=self.adapter
        )
        self.presenters["model_selection"].request_show_download_center.connect(
            self._open_download_center_tab
        )
        self.model_selection_view.add_settings_panel("VR Arch", self.vr_arch_view)
        self.model_selection_view.add_settings_panel("MDX-Net", self.mdx_net_view)
        self.model_selection_view.add_settings_panel("Demucs", self.demucs_view)
        self.model_selection_view.add_settings_panel("Ensemble", self.ensemble_view)
        self.main_layout.addWidget(self.model_selection_view)

        # Processing Settings
        self.processing_settings_view = ProcessingSettingsView()
        self.presenters["processing_settings"] = ProcessingSettingsPresenter(
            view=self.processing_settings_view
        )
        self.main_layout.addWidget(self.processing_settings_view)

        # Execution Control
        self.execution_control_view = ExecutionControlView()
        self.presenters["execution"] = ExecutionControlPresenter(
            view=self.execution_control_view,
            main_window_presenters=self.presenters,
            adapter=self.adapter
        )
        self.main_layout.addWidget(self.execution_control_view)
        self.main_layout.addStretch(1)
        self._create_menu_bar()

        # --- Trigger initial method population and selection ---
        if self.model_selection_view.method_combo.count() > 0:
            initial_method = self.model_selection_view.method_combo.currentText()
            if initial_method:
                print(f"MainWindowView: Triggering initial panel display for method '{initial_method}'")
                # This call will now correctly find the panels in ModelSelectionView's stack
                self.presenters["model_selection"].handle_method_change(initial_method)
        else:
            # If no methods, ModelSelectionPresenter might need to clear/show a default empty panel
            print("MainWindowView: Method combo is empty on init. Triggering presenter with empty method.")
            self.presenters["model_selection"].handle_method_change("")

        print("MainWindowView Fully Initialized.")

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu("&File")
        quit_action = QAction("&Quit", self)
        quit_action.setStatusTip("Exit the application")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self._quit_application)
        file_menu.addAction(quit_action)
        edit_menu = menu_bar.addMenu("&Edit")
        prefs_action = QAction("&Preferences...", self)
        prefs_action.setStatusTip("Open application settings")
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.triggered.connect(self.settings_dialog_presenter.show_dialog)
        edit_menu.addAction(prefs_action)
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.setStatusTip("Show application information")
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    @Slot()
    def _open_download_center_tab(self):
        print("MainWindow: Opening Download Center tab in Preferences...")
        self.settings_dialog_presenter.show_dialog(exec_dialog=False)
        if self.settings_dialog_presenter.view:
            self.settings_dialog_presenter.view.tab_widget.setCurrentIndex(2)
        else:
            print("MainWindow: Settings dialog view not available after attempting to show.")

    def _quit_application(self):
        print("Quitting application...")
        app = QApplication.instance()
        if app: app.quit()

    def _show_about_dialog(self):
        QMessageBox.about(
            self, "About UVR - PySide6 Edition",
            "UVR GUI PySide6 Refactor.\nRefactoring in progress."
        )

    def show_status_message(self, message, timeout=0):
        self.status_bar.showMessage(message, timeout)
