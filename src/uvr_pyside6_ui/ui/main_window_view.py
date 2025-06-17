from PySide6.QtCore import Slot  # Added QSize
from PySide6.QtGui import QAction  # Added QIcon
from PySide6.QtWidgets import (
    QApplication,  # Added QScrollArea, QPushButton, QHBoxLayout, QFrame
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core import app_constants as ac
from ..core.uvr_core_adapter import UVRCoreAdapter
from .demucs_settings_presenter import DemucsSettingsPresenter
from .demucs_settings_view import DemucsSettingsView
from .ensemble_simple_presenter import EnsembleSimplePresenter
from .ensemble_simple_view import EnsembleSimpleView
from .execution_control_presenter import ExecutionControlPresenter
from .execution_control_view import ExecutionControlView
from .file_io_presenter import FileIOPresenter

from .file_io_view import FileIOView
from .mdx_net_settings_presenter import MDXNetSettingsPresenter
from .mdx_net_settings_view import MDXNetSettingsView
from .model_selection_presenter import ModelSelectionPresenter
from .model_selection_view import ModelSelectionView
from .processing_settings_presenter import ProcessingSettingsPresenter
from .processing_settings_view import ProcessingSettingsView
from .settings_dialog_presenter import SettingsDialogPresenter
from .vr_arch_settings_presenter import VRArchSettingsPresenter
from .vr_arch_settings_view import VRArchSettingsView


class MainWindowView(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(ac.APP_TITLE)
        self.setGeometry(
            100, 100, 600, 820
        )  # Slightly increased height to accommodate reorganized settings without scrolling

        # --- Main Content Container for ScrollArea ---
        self.main_content_container = QWidget()
        self.main_layout = QVBoxLayout(self.main_content_container)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(10)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(ac.STATUS_READY)

        self.presenters = {}
        self.adapter = UVRCoreAdapter(self)
        self.settings_dialog_presenter = SettingsDialogPresenter(
            adapter=self.adapter, parent_qt_object=self
        )

        # --- Top Bar for Settings Button (Optional, or add to existing area) ---
        # For now, let's add it to the main layout for simplicity.
        # A QToolBar would be another option.

        # --- Instantiate UI Modules and add them to main_layout ---
        # ... (File I/O, Specific Settings Panels, Model Selection, Processing Settings as in response #37) ...
        # File I/O
        self.file_io_view = FileIOView()
        self.presenters[ac.FILE_IO_PRESENTER_KEY] = FileIOPresenter(
            view=self.file_io_view
        )
        self.main_layout.addWidget(self.file_io_view)
        # Specific Settings Panels
        self.vr_arch_view = VRArchSettingsView()
        self.presenters[ac.VR_ARCH_PRESENTER_KEY] = VRArchSettingsPresenter(
            view=self.vr_arch_view
        )
        self.mdx_net_view = MDXNetSettingsView()
        self.presenters[ac.MDX_NET_PRESENTER_KEY] = MDXNetSettingsPresenter(
            view=self.mdx_net_view
        )
        self.demucs_view = DemucsSettingsView()
        self.presenters[ac.DEMUCS_PRESENTER_KEY] = DemucsSettingsPresenter(
            view=self.demucs_view
        )
        self.ensemble_view = EnsembleSimpleView()
        self.presenters[ac.ENSEMBLE_PRESENTER_KEY] = EnsembleSimplePresenter(
            view=self.ensemble_view,
            adapter=self.adapter,
            settings_dialog_presenter=self.settings_dialog_presenter,
        )

        # Processing Settings (create first so we can connect to it)
        self.processing_settings_view = ProcessingSettingsView()
        self.presenters[ac.PROCESSING_SETTINGS_PRESENTER_KEY] = (
            ProcessingSettingsPresenter(view=self.processing_settings_view)
        )

        # Model Selection
        self.model_selection_view = ModelSelectionView()
        self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY] = ModelSelectionPresenter(
            view=self.model_selection_view, adapter=self.adapter
        )
        self.presenters[
            ac.MODEL_SELECTION_PRESENTER_KEY
        ].request_show_download_center.connect(self._open_download_center_tab)
        # self.adapter.download_finished.connect(self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY]._on_model_downloaded_elsewhere) # Removed, ModelSelectionPresenter now uses model_download_completed

        # Connect model changes to processing settings updates
        self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].model_changed.connect(
            self.presenters[ac.PROCESSING_SETTINGS_PRESENTER_KEY].handle_model_change
        )

        # Connect ensemble stem pair changes to processing settings updates
        self.ensemble_view.main_stem_pair_changed.connect(
            self.presenters[
                ac.PROCESSING_SETTINGS_PRESENTER_KEY
            ].handle_ensemble_stem_pair_change
        )

        # Connect Demucs stem changes to model selection presenter
        self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].connect_demucs_stem_changes(
            self.presenters[ac.DEMUCS_PRESENTER_KEY]
        )
        # Also store reference for stem detection
        self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY]._demucs_presenter = (
            self.presenters[ac.DEMUCS_PRESENTER_KEY]
        )

        self.model_selection_view.add_settings_panel("VR Arch", self.vr_arch_view)
        self.model_selection_view.add_settings_panel("MDX-Net", self.mdx_net_view)
        self.model_selection_view.add_settings_panel("Demucs", self.demucs_view)
        self.model_selection_view.add_settings_panel("Ensemble", self.ensemble_view)
        self.main_layout.addWidget(self.model_selection_view)
        self.main_layout.addWidget(self.processing_settings_view)

        # Connect presenters to settings dialog for advanced settings persistence
        self.settings_dialog_presenter.set_main_window_presenters(self.presenters)

        # --- Execution Control and Settings Button Row ---
        bottom_controls_layout = QHBoxLayout()
        self.execution_control_view = ExecutionControlView()
        self.presenters[ac.EXECUTION_PRESENTER_KEY] = ExecutionControlPresenter(
            view=self.execution_control_view,
            main_window_presenters=self.presenters,
            adapter=self.adapter,
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
                self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].handle_method_change(
                    initial_method
                )
        else:
            self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].handle_method_change("")

        # Trigger initial ensemble stem pair change to update processing settings checkboxes
        # This must happen after all connections are established
        current_stem_pair = self.ensemble_view.get_current_stem_pair()
        if current_stem_pair:
            self.presenters[
                ac.PROCESSING_SETTINGS_PRESENTER_KEY
            ].handle_ensemble_stem_pair_change(current_stem_pair)

        # Debug print removed

    # ... (_create_menu_bar, _open_download_center_tab, _quit_application,
    #      _show_about_dialog, show_status_message methods remain unchanged from response #37) ...
    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)
        file_menu = menu_bar.addMenu(ac.MENU_FILE)
        quit_action = QAction(ac.ACTION_QUIT, self)
        quit_action.setShortcut(ac.SHORTCUT_QUIT)
        quit_action.triggered.connect(self._quit_application)
        file_menu.addAction(quit_action)
        edit_menu = menu_bar.addMenu(ac.MENU_EDIT)
        prefs_action = QAction(ac.ACTION_PREFERENCES, self)
        prefs_action.setShortcut(ac.SHORTCUT_PREFERENCES)
        prefs_action.triggered.connect(
            lambda: self.settings_dialog_presenter.show_dialog(default_model_type=None)
        )
        edit_menu.addAction(prefs_action)
        help_menu = menu_bar.addMenu(ac.MENU_HELP)
        about_action = QAction(ac.ACTION_ABOUT, self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    @Slot(str)
    def _open_download_center_tab(self, originating_method: str):
        self.settings_dialog_presenter.show_dialog(
            exec_dialog=False, default_model_type=originating_method
        )
        if self.settings_dialog_presenter.view:
            self.settings_dialog_presenter.view.tab_widget.setCurrentIndex(2)

    def _quit_application(self):
        app = QApplication.instance()
        app.quit() if app else None

    def _show_about_dialog(self):
        QMessageBox.about(self, ac.ABOUT_TITLE, ac.ABOUT_MESSAGE)

    def show_status_message(self, message, timeout=0):
        self.status_bar.showMessage(message, timeout)
