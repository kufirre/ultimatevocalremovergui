from PySide6.QtCore import QSize, Qt, Slot  # Added QSize
from PySide6.QtGui import QAction, QIcon  # Added QIcon
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
from .batch_file_presenter import BatchFilePresenter
from .batch_file_view import BatchFileView
from .demucs_settings_presenter import DemucsSettingsPresenter
from .demucs_settings_view import DemucsSettingsView
from .ensemble_simple_presenter import EnsembleSimplePresenter
from .ensemble_simple_view import EnsembleSimpleView
from .error_log_presenter import ErrorLogPresenter
from .execution_control_presenter import ExecutionControlPresenter
from .execution_control_view import ExecutionControlView
from .file_io_presenter import FileIOPresenter
from .file_io_view import FileIOView
from .information_guide_presenter import InformationGuidePresenter
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
        self.setWindowIcon(QIcon(ac.QRC_ICON_PATH))
        self.setGeometry(
            100, 100, 600, 900  # Increased height to accommodate batch processing
        )

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

        # --- Information Guide and Error Log Presenters ---
        self.information_guide_presenter = InformationGuidePresenter(self)
        self.error_log_presenter = ErrorLogPresenter(self)

        # --- Batch Processing Components (Create first) ---
        self.batch_file_view = BatchFileView()
        self.presenters[ac.BATCH_FILE_PRESENTER_KEY] = BatchFilePresenter(
            view=self.batch_file_view
        )

        # --- File I/O (Updated to support batch processing) ---
        self.file_io_view = FileIOView()
        self.presenters[ac.FILE_IO_PRESENTER_KEY] = FileIOPresenter(
            view=self.file_io_view,
            batch_presenter=self.presenters[ac.BATCH_FILE_PRESENTER_KEY]
        )
        self.main_layout.addWidget(self.file_io_view)

        # --- Batch File Management (Initially hidden) ---
        self.batch_file_view.setVisible(False)
        self.main_layout.addWidget(self.batch_file_view)

        # --- Specific Settings Panels ---
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

        # Connect Demucs stem changes to model selection
        self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].connect_demucs_stem_changes(
            self.presenters[ac.DEMUCS_PRESENTER_KEY]
        )

        # --- Add Settings Panels to Model Selection View ---
        self.model_selection_view.add_settings_panel("VR Arch", self.vr_arch_view)
        self.model_selection_view.add_settings_panel("MDX-Net", self.mdx_net_view)
        self.model_selection_view.add_settings_panel("Demucs", self.demucs_view)
        self.model_selection_view.add_settings_panel("Ensemble", self.ensemble_view)

        # --- Add Model Selection to Layout ---
        self.main_layout.addWidget(self.model_selection_view)

        # --- Add Processing Settings to Layout ---
        self.processing_settings_view.setVisible(True)  # Ensure it's visible before adding
        self.processing_settings_view.show()  # Explicitly show it
        self.main_layout.addWidget(self.processing_settings_view)

        # --- Execution Control ---
        self.execution_control_view = ExecutionControlView()
        self.presenters[ac.EXECUTION_CONTROL_PRESENTER_KEY] = (
            ExecutionControlPresenter(
                view=self.execution_control_view,
                main_window_presenters=self.presenters,
                adapter=self.adapter,
            )
        )
        self.main_layout.addWidget(self.execution_control_view)

        # --- Scroll Area Setup ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.main_content_container)
        self.setCentralWidget(scroll_area)

        # --- Menu Bar ---
        self._create_menu_bar()

        # --- Connect File I/O Mode Changes ---
        self.file_io_view.batch_mode_toggled.connect(self._handle_batch_mode_toggle)
        self.presenters[ac.FILE_IO_PRESENTER_KEY].processing_mode_changed.connect(
            self._handle_processing_mode_change
        )

        # --- Connect Settings Persistence System ---
        self.settings_dialog_presenter.set_main_window_presenters(self.presenters)

        # --- Initialize UI State ---
        self._initialize_ui()

    def _create_menu_bar(self):
        """Create the application menu bar."""
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
        
        # Information Guide menu items
        user_guide_action = QAction("User Guide", self)
        user_guide_action.triggered.connect(self.information_guide_presenter.show_information_guide)
        help_menu.addAction(user_guide_action)
        
        help_menu.addSeparator()
        
        getting_started_action = QAction("Getting Started", self)
        getting_started_action.triggered.connect(self.information_guide_presenter.show_getting_started)
        help_menu.addAction(getting_started_action)
        
        model_types_action = QAction("Model Types", self)
        model_types_action.triggered.connect(self.information_guide_presenter.show_model_types)
        help_menu.addAction(model_types_action)
        
        processing_options_action = QAction("Processing Options", self)
        processing_options_action.triggered.connect(self.information_guide_presenter.show_processing_options)
        help_menu.addAction(processing_options_action)
        
        audio_formats_action = QAction("Audio Formats", self)
        audio_formats_action.triggered.connect(self.information_guide_presenter.show_audio_formats)
        help_menu.addAction(audio_formats_action)
        
        troubleshooting_action = QAction("Troubleshooting", self)
        troubleshooting_action.triggered.connect(self.information_guide_presenter.show_troubleshooting)
        help_menu.addAction(troubleshooting_action)
        
        faq_action = QAction("FAQ", self)
        faq_action.triggered.connect(self.information_guide_presenter.show_faq)
        help_menu.addAction(faq_action)
        
        help_menu.addSeparator()
        
        # Error Log menu item
        error_log_action = QAction("View Error Log", self)
        error_log_action.triggered.connect(self.error_log_presenter.show_error_log)
        help_menu.addAction(error_log_action)
        
        help_menu.addSeparator()
        
        about_action = QAction(ac.ACTION_ABOUT, self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _initialize_ui(self):
        """Initialize the UI state after all components are created."""
        # Ensure single file mode is active on startup
        self.presenters[ac.FILE_IO_PRESENTER_KEY].set_processing_mode("single")
        
        # Ensure processing settings view is visible (it should always be visible)
        self.processing_settings_view.setVisible(True)
        
        # Trigger initial method change to set up default selection
        if self.model_selection_view.method_combo.count() > 0:
            initial_method = self.model_selection_view.method_combo.currentText()
            if initial_method:
                self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].handle_method_change(
                    initial_method
                )
        else:
            self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY].handle_method_change("")

        # Trigger initial ensemble stem pair change to update processing settings checkboxes
        # This must happen after model selection is initialized
        if hasattr(self.ensemble_view, "main_stem_pair_combo"):
            initial_stem_pair = self.ensemble_view.main_stem_pair_combo.currentText()
            if initial_stem_pair:
                self.presenters[
                    ac.PROCESSING_SETTINGS_PRESENTER_KEY
                ].handle_ensemble_stem_pair_change(initial_stem_pair)
                
        # Ensure processing settings view is visible (final check)
        self.processing_settings_view.setVisible(True)
        self.processing_settings_view.show()

    @Slot(bool)
    def _handle_batch_mode_toggle(self, enabled: bool):
        """Handle the batch mode toggle from the file I/O view."""
        mode = "batch" if enabled else "single"
        self.presenters[ac.FILE_IO_PRESENTER_KEY].set_processing_mode(mode)

    @Slot(str)
    def _handle_processing_mode_change(self, mode: str):
        """Handle processing mode changes."""
        is_batch_mode = mode == "batch"
        
        # Show/hide batch file management
        self.batch_file_view.setVisible(is_batch_mode)
        
        # Ensure processing settings view is always visible regardless of mode
        self.processing_settings_view.setVisible(True)
        
        # Update window height based on mode
        if is_batch_mode:
            self.resize(self.width(), 1000)  # Taller for batch mode
        else:
            self.resize(self.width(), 820)   # Original height for single mode
        
        # Update status bar
        if is_batch_mode:
            self.status_bar.showMessage("Batch Processing Mode - Add files to the queue below")
        else:
            self.status_bar.showMessage(ac.STATUS_READY)

    def _open_settings_dialog(self):
        """Open the settings dialog."""
        self.settings_dialog_presenter.show_dialog()

    @Slot(str)
    def _open_download_center_tab(self, originating_method: str):
        self.settings_dialog_presenter.show_dialog(
            exec_dialog=False, default_model_type=originating_method
        )
        if self.settings_dialog_presenter.view:
            self.settings_dialog_presenter.view.tab_widget.setCurrentIndex(2)

    def _show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About UVR",
            f"{ac.APP_TITLE}\n\n"
            "Ultimate Vocal Remover - PySide6 Port\n"
            "Advanced audio source separation using machine learning\n\n"
            "This is a modern Qt-based port of the original UVR application."
        )

    def _quit_application(self):
        app = QApplication.instance()
        app.quit() if app else None

    def show_status_message(self, message, timeout=0):
        self.status_bar.showMessage(message, timeout)
