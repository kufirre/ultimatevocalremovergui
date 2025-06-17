"""Presenter coordinating model and method selections."""

from PySide6.QtCore import QObject, Signal, Slot

from ..core import app_constants as ac
from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class ModelSelectionPresenter(QObject):
    """Manage user interactions for selecting processing methods and models."""

    request_show_download_center = Signal(str)  # Emits originating_method
    model_changed = Signal(
        str, str, str, str
    )  # method, model, primary_stem, secondary_stem
    settings_changed = Signal(dict)  # For persistence system

    def __init__(self, view, adapter):
        super().__init__()
        self.view = view
        self.adapter = adapter
        self._current_method = ""
        self._current_model = ""
        self.view.process_method_changed.connect(self.handle_method_change)
        self.view.model_selected_by_user.connect(self.process_model_selection)
        # self.adapter.download_finished.connect(self._on_model_downloaded_elsewhere) # Replaced by model_download_completed
        self.adapter.model_download_completed.connect(
            self._handle_model_list_refresh_on_download
        )

        self._available_methods = self.adapter.get_available_methods()
        self.view.set_process_methods(self._available_methods)

        if self._available_methods:
            self._current_method = self.view.method_combo.currentText()

            # self.view.set_ensemble_checked(self._is_advanced_ensemble_options) # REMOVED
        # Debug print removed

    def connect_demucs_stem_changes(self, demucs_presenter):
        """Connect to Demucs stem selection changes."""
        if hasattr(demucs_presenter, "view") and hasattr(
            demucs_presenter.view, "stems_changed"
        ):
            demucs_presenter.view.stems_changed.connect(self._handle_demucs_stem_change)

    @Slot(str)
    def _handle_model_list_refresh_on_download(self, model_type_ui_name: str):
        """
        Slot to refresh the model list for the current method if a download
        for that method type has just completed.
        """
        if model_type_ui_name == self._current_method:
            # print(f"ModelSelectionPresenter: Refreshing model list for {model_type_ui_name} due to download completion.")
            self.handle_method_change(self._current_method)

    @Slot(str)
    def handle_method_change(self, method: str) -> None:
        """Update available models when the processing method changes."""
        if not method:
            self.view.set_models([], "")
            self._current_method = ""
            self._current_model = ""
            self.view.show_settings_panel("")
            return
        self._current_method = method
        auto_selected_model = ""
        if method == ac.ENSEMBLE_MODELS_KEY:

            auto_selected_model = self.view.set_models([], current_method=method)
        else:
            models_for_method = self.adapter.get_available_models(method)

            auto_selected_model = self.view.set_models(
                models_for_method, current_method=method
            )
        if (
            auto_selected_model
            and auto_selected_model != ac.DOWNLOAD_MORE_MODELS_TEXT
            and auto_selected_model != ac.ENSEMBLE_MODEL_INFO_TEXT
        ):
            self._current_model = auto_selected_model
            self._emit_model_change_info()
            self._emit_settings_changed()  # Emit settings change for persistence

        else:
            self._current_model = ""
            self._emit_model_change_info()
            self._emit_settings_changed()  # Emit settings change for persistence

        # Manage ensemble view expansion state
        # Ensure ensemble_view is accessed correctly via self.view (ModelSelectionView)
        # which should have a way to get its panels, e.g., through widget_map.
        ensemble_view_widget = self.view.widget_map.get(ac.ENSEMBLE_MODELS_KEY)
        if ensemble_view_widget and hasattr(ensemble_view_widget, "set_expanded_mode"):
            if method == ac.ENSEMBLE_MODELS_KEY:
                ensemble_view_widget.set_expanded_mode(True)
            else:
                # Ensure ensemble panel is contracted if another method is chosen
                ensemble_view_widget.set_expanded_mode(False)
        elif method == ac.ENSEMBLE_MODELS_KEY:
            # Debug print removed
            pass  # Log this properly

        self.view.show_settings_panel(self._current_method)

    @Slot(str)
    def process_model_selection(self, selected_text: str) -> None:
        """Handle a user changing the selected model."""
        if selected_text == ac.DOWNLOAD_MORE_MODELS_TEXT:
            self.request_show_download_center.emit(
                self._current_method if self._current_method else ""
            )
            self.view.set_current_model_text(
                self._current_model if self._current_model else ""
            )
        elif selected_text and selected_text != ac.ENSEMBLE_MODEL_INFO_TEXT:
            if self._current_model != selected_text:
                self._current_model = selected_text
                self._emit_model_change_info()
                self._emit_settings_changed()  # Emit settings change for persistence
        elif not selected_text and self._current_model:
            self._current_model = ""
            self._emit_model_change_info()
            self._emit_settings_changed()  # Emit settings change for persistence

    def _emit_model_change_info(self):
        """Emit model change information including stem details."""
        if not self._current_method or not self._current_model:
            # Disable processing checkboxes when no model is selected
            self.model_changed.emit("", "", "", "")
            return

        primary_stem, secondary_stem = self._get_stems_for_model(
            self._current_method, self._current_model
        )
        self.model_changed.emit(
            self._current_method, self._current_model, primary_stem, secondary_stem
        )

    def _get_stems_for_model(self, method: str, model_name: str):
        """Get primary and secondary stem names for the given model."""
        try:
            # Get model info from adapter
            model_info = self.adapter.get_model_info(model_name, method)

            if method == ac.DEMUCS_MODELS_KEY:
                # For Demucs, check the currently selected stem in the Demucs view
                # Try to get current stem selection from Demucs presenter
                demucs_presenter = getattr(self, "_demucs_presenter", None)
                if demucs_presenter and hasattr(demucs_presenter, "view"):
                    current_stem = demucs_presenter.view.stem_combo.currentText()
                    return self._get_demucs_stems_for_selection(current_stem)
                # Default fallback for Demucs
                return ac.VOCAL_STEM, ac.INST_STEM

            elif method == ac.VR_ARCH_MODELS_KEY:
                if model_info and hasattr(model_info, "primary_stem"):
                    primary = getattr(model_info, "primary_stem", ac.VOCAL_STEM)
                    secondary = ac.secondary_stem(primary)
                    return primary, secondary
            elif method == ac.MDX_NET_MODELS_KEY:
                if model_info and hasattr(model_info, "mdx_model_stems"):
                    stems = getattr(model_info, "mdx_model_stems", [])
                    if stems:
                        primary = stems[0] if stems else ac.VOCAL_STEM
                        secondary = ac.secondary_stem(primary)
                        return primary, secondary
                # Default for most MDX models
                return ac.VOCAL_STEM, ac.INST_STEM
            elif method == ac.ENSEMBLE_MODELS_KEY:
                # For ensemble, disable individual stem checkboxes
                return "Primary", "Secondary"
        except Exception as e:
            # If we can't get model info, use defaults
            pass

        # Default fallback
        return ac.VOCAL_STEM, ac.INST_STEM

    @Slot(str)
    def _handle_demucs_stem_change(self, stem_selection: str):
        """Handle changes in Demucs stem selection."""
        if self._current_method == ac.DEMUCS_MODELS_KEY and self._current_model:
            primary_stem, secondary_stem = self._get_demucs_stems_for_selection(
                stem_selection
            )
            self.model_changed.emit(
                self._current_method, self._current_model, primary_stem, secondary_stem
            )

    def _get_demucs_stems_for_selection(self, stem_selection: str):
        """Get primary and secondary stems for Demucs based on selection."""
        if stem_selection == "All Stems":
            return "Primary", "Secondary"  # Disable checkboxes for All Stems
        elif stem_selection == "Vocals":
            return ac.VOCAL_STEM, ac.INST_STEM
        elif stem_selection == "Instrumental":
            # Instrumental is created by combining Bass+Drums+Other or subtracting Vocals
            return ac.INST_STEM, ac.VOCAL_STEM
        elif stem_selection == "Bass":
            return ac.BASS_STEM, ac.secondary_stem(ac.BASS_STEM)
        elif stem_selection == "Drums":
            return ac.DRUM_STEM, ac.secondary_stem(ac.DRUM_STEM)
        elif stem_selection == "Other":
            return ac.OTHER_STEM, ac.secondary_stem(ac.OTHER_STEM)
        else:
            return ac.VOCAL_STEM, ac.INST_STEM  # Default fallback

    def get_current_selection(self) -> dict:
        """Return the currently chosen processing method and model."""
        resolved_model_name = self._current_model
        if resolved_model_name == ac.DOWNLOAD_MORE_MODELS_TEXT or (
            self._current_method == ac.ENSEMBLE_MODELS_KEY
            and resolved_model_name == ac.ENSEMBLE_MODEL_INFO_TEXT
        ):
            resolved_model_name = ""

        settings = {}  # Initialize empty settings dictionary

        # Map UI method string to internal constant and specific model key
        if self._current_method == ac.VR_ARCH_MODELS_KEY:  # UI string: "VR Arch"
            settings["chosen_process_method"] = (
                ac.VR_ARCH_TYPE
            )  # Internal constant: 'VR Arc'
            settings["vr_model"] = resolved_model_name
        elif self._current_method == ac.MDX_NET_MODELS_KEY:  # UI string: "MDX-Net"
            settings["chosen_process_method"] = (
                ac.MDX_ARCH_TYPE
            )  # Internal constant: 'MDX-Net'
            settings["mdx_net_model"] = resolved_model_name
        elif self._current_method == ac.DEMUCS_MODELS_KEY:  # UI string: "Demucs"
            settings["chosen_process_method"] = (
                ac.DEMUCS_ARCH_TYPE
            )  # Internal constant: 'Demucs'
            settings["demucs_model"] = resolved_model_name
        elif self._current_method == ac.ENSEMBLE_MODELS_KEY:  # UI string: "Ensemble"
            settings["chosen_process_method"] = (
                ac.ENSEMBLE_MODE
            )  # Internal constant: 'Ensemble Mode'
            settings["ensemble_model"] = resolved_model_name
        else:
            # Default or error case if _current_method is unexpected
            settings["chosen_process_method"] = ""
            # Avoid adding a model key if the method is unknown to prevent downstream errors

        return settings

    def load_settings(self, settings_dict):
        """Load model selection from saved settings."""
        if not settings_dict:
            return

        logger.debug(f"Loading model selection settings: {settings_dict}")

        # Extract method and model from settings
        method = settings_dict.get("chosen_process_method", "")

        # Map internal constants back to UI strings
        method_mapping = {
            ac.VR_ARCH_TYPE: ac.VR_ARCH_MODELS_KEY,  # 'VR Arc' -> 'VR Arch'
            ac.MDX_ARCH_TYPE: ac.MDX_NET_MODELS_KEY,  # 'MDX-Net' -> 'MDX-Net'
            ac.DEMUCS_ARCH_TYPE: ac.DEMUCS_MODELS_KEY,  # 'Demucs' -> 'Demucs'
            ac.ENSEMBLE_MODE: ac.ENSEMBLE_MODELS_KEY,  # 'Ensemble Mode' -> 'Ensemble'
        }

        ui_method = method_mapping.get(method, method)

        # Get the model based on the method
        model = ""
        if method == ac.VR_ARCH_TYPE:
            model = settings_dict.get("vr_model", "")
        elif method == ac.MDX_ARCH_TYPE:
            model = settings_dict.get("mdx_net_model", "")
        elif method == ac.DEMUCS_ARCH_TYPE:
            model = settings_dict.get("demucs_model", "")
        elif method == ac.ENSEMBLE_MODE:
            model = settings_dict.get("ensemble_model", "")

        # Update the view if we have valid method and model
        if ui_method and ui_method != method:  # Only if mapping was successful
            self.view.set_current_method_text(ui_method)
            self._current_method = ui_method

            # Trigger method change to populate models
            self.handle_method_change(ui_method)

            # Set the model if it exists
            if model:
                self.view.set_current_model_text(model)
                self._current_model = model
                self._emit_model_change_info()

    def _emit_settings_changed(self):
        """Emit settings changed signal for persistence."""
        current_settings = self.get_current_selection()
        self.settings_changed.emit(current_settings)
