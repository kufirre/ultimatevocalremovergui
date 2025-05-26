from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStatusBar, QMessageBox,
    QApplication
)
from PySide6.QtGui import QAction

from .file_io_view import FileIOView
from .processing_settings_view import ProcessingSettingsView
from .model_selection_view import ModelSelectionView
from .vr_arch_settings_view import VRArchSettingsView
from .mdx_net_settings_view import MDXNetSettingsView
from .demucs_settings_view import DemucsSettingsView
from .ensemble_settings_view import EnsembleSettingsView
from .execution_control_view import ExecutionControlView

from .file_io_presenter import FileIOPresenter
from .processing_settings_presenter import ProcessingSettingsPresenter
from .model_selection_presenter import ModelSelectionPresenter
from .vr_arch_settings_presenter import VRArchSettingsPresenter
from .mdx_net_settings_presenter import MDXNetSettingsPresenter
from .demucs_settings_presenter import DemucsSettingsPresenter
from .ensemble_settings_presenter import EnsembleSettingsPresenter
from .execution_control_presenter import ExecutionControlPresenter
from .settings_dialog_presenter import SettingsDialogPresenter

from ..core.uvr_core_adapter import UVRCoreAdapter


class MainWindowView(QMainWindow):
    """
    The main window shell for the application.
    It holds and layouts the different UI modules and includes the menu bar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("UVR - PySide6 Edition")
        self.setGeometry(100, 100, 800, 800)

        # --- Core Window Setup ---
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Dictionary to hold presenters for intercommunication (e.g., for Exec Control)
        self.presenters = {}

        # Pass self as parent for QObject mgmt
        self.adapter = UVRCoreAdapter(self)

        # --- Instantiate Settings Dialog Presenter (Needed for Menu) ---
        self.settings_dialog_presenter = SettingsDialogPresenter(self)

        # --- Instantiate and Add UI Modules ---

        # File I/O
        self.file_io_view = FileIOView()
        self.presenters["file_io"] = FileIOPresenter(view=self.file_io_view)
        self.main_layout.addWidget(self.file_io_view)

        # Instantiate Specific Settings Panels
        self.vr_arch_view = VRArchSettingsView()
        self.presenters["vr_arch"] = VRArchSettingsPresenter(view=self.vr_arch_view)

        self.mdx_net_view = MDXNetSettingsView()
        self.presenters["mdx_net"] = MDXNetSettingsPresenter(view=self.mdx_net_view)

        self.demucs_view = DemucsSettingsView()
        self.presenters["demucs"] = DemucsSettingsPresenter(view=self.demucs_view)

        self.ensemble_view = EnsembleSettingsView()
        self.presenters["ensemble"] = EnsembleSettingsPresenter(view=self.ensemble_view)

        # Model Selection (Pass Adapter)
        self.model_selection_view = ModelSelectionView()
        self.presenters["model_selection"] = ModelSelectionPresenter(
            view=self.model_selection_view,
            adapter=self.adapter
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

        # Execution Control (Pass Adapter)
        self.execution_control_view = ExecutionControlView()
        self.presenters["execution"] = ExecutionControlPresenter(
            view=self.execution_control_view,
            main_window_presenters=self.presenters,
            adapter=self.adapter  # Pass adapter
        )
        self.main_layout.addWidget(self.execution_control_view)

        self.main_layout.addStretch(1)

        self._create_menu_bar()

        # Trigger initial model selection & panel display
        self.presenters["model_selection"].handle_method_change(
            self.model_selection_view.method_combo.currentText()
        )

        print("MainWindowView Initialized with Core Adapter.")

    def _create_menu_bar(self):
        """Creates and configures the main menu bar."""
        menu_bar = self.menuBar()
        # Force menu bar into window (useful for dev/macOS script running)
        menu_bar.setNativeMenuBar(False)

        # --- File Menu ---
        file_menu = menu_bar.addMenu("&File")

        # Quit Action
        quit_action = QAction("&Quit", self)
        quit_action.setStatusTip("Exit the application")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self._quit_application)
        file_menu.addAction(quit_action)

        # --- Edit Menu ---
        edit_menu = menu_bar.addMenu("&Edit")

        # Preferences Action
        prefs_action = QAction("&Preferences...", self)
        prefs_action.setStatusTip("Open application settings")
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.triggered.connect(self.settings_dialog_presenter.show_dialog)
        edit_menu.addAction(prefs_action)

        # --- Help Menu ---
        help_menu = menu_bar.addMenu("&Help")

        # About Action
        about_action = QAction("&About", self)
        about_action.setStatusTip("Show application information")
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _quit_application(self):
        """Closes the application."""
        print("Quitting application...")
        # Get the QApplication instance and call quit()
        app = QApplication.instance()
        if app:
            app.quit()

    def _show_about_dialog(self):
        """Displays a simple 'About' message box."""
        QMessageBox.about(
            self,
            "About UVR - PySide6 Edition",
            "This is a community-driven rewrite of the UVR GUI "
            "using PySide6.\n\n"
            "Refactoring in progress."
        )

    def show_status_message(self, message, timeout=0):
        """Displays a message on the status bar."""
        self.status_bar.showMessage(message, timeout)
