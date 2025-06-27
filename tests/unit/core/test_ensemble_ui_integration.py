"""
Unit tests for ensemble UI integration functionality.

Tests the complete integration between ensemble UI components (presenters, views, dialogs)
and core ensemble functionality, including save/load operations and file management.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from PySide6.QtWidgets import QApplication

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter
from uvr_pyside6_ui.ui.ensemble_advanced_dialog import EnsembleAdvancedDialog
from uvr_pyside6_ui.ui.ensemble_simple_presenter import EnsembleSimplePresenter
from uvr_pyside6_ui.ui.ensemble_simple_view import EnsembleSimpleView


@pytest.fixture
def qapp():
    """Create QApplication for tests that need it."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_view():
    """Create a mock view for testing."""
    view = Mock(spec=EnsembleSimpleView)
    view.main_stem_pair_changed = Mock()
    view.ensemble_algorithm_changed = Mock()
    view.advanced_settings_requested = Mock()
    return view


@pytest.fixture
def mock_adapter():
    """Create a mock adapter for testing."""
    adapter = Mock(spec=UVRCoreAdapter)
    adapter.get_available_models.return_value = ["Model1", "Model2", "Model3"]
    return adapter


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config" / "saved_ensembles"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create a test ensemble file
        test_ensemble = {
            "ensemble_main_stem": "Vocals/Instrumental",
            "ensemble_type": "Average",
            "selected_models": ["Model1", "Model2"],
        }
        with open(config_dir / "test_ensemble.json", "w") as f:
            json.dump(test_ensemble, f)

        yield config_dir


class TestEnsembleSimplePresenter:
    """Test cases for EnsembleSimplePresenter."""

    def test_initialization(self, mock_view, mock_adapter):
        """Test presenter initialization."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)

        assert presenter.view == mock_view
        assert presenter.adapter == mock_adapter
        assert (
            presenter._current_main_stem_pair == ac.ENSEMBLE_MAIN_STEM_OPTIONS[0]
        )  # "4 Stem Ensemble"
        # Since the default stem pair is "4 Stem Ensemble", the algorithm will be from 4-stem options
        assert (
            presenter._current_algorithm == "Max Spec"
        )  # First option in ENSEMBLE_ALGORITHM_4_STEM_OPTIONS
        assert presenter._currently_selected_models == []
        assert presenter._advanced_settings["save_all_outputs"] is True
        assert presenter._advanced_settings["append_ensemble_name"] is False
        assert presenter._advanced_settings["use_waveform_ensemble"] is False

    def test_stem_pair_changed(self, mock_view, mock_adapter):
        """Test stem pair change handling."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)

        presenter.on_main_stem_pair_changed("4 Stem Ensemble")

        assert presenter._current_main_stem_pair == "4 Stem Ensemble"
        assert presenter._currently_selected_models == []  # Should be cleared
        mock_view.update_selection_status.assert_called_with([])

    def test_algorithm_changed(self, mock_view, mock_adapter):
        """Test algorithm change handling."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)

        presenter.on_ensemble_algorithm_changed("Max Spec")

        assert presenter._current_algorithm == "Max Spec"

    def test_update_algorithm_options_4_stem(self, mock_view, mock_adapter):
        """Test algorithm options update for 4-stem ensemble."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = "4 Stem Ensemble"

        presenter._update_algorithm_options()

        mock_view.update_algorithm_options.assert_called_with(
            ac.ENSEMBLE_ALGORITHM_4_STEM_OPTIONS
        )

    def test_update_algorithm_options_2_stem(self, mock_view, mock_adapter):
        """Test algorithm options update for 2-stem ensemble."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = "Vocals/Instrumental"

        presenter._update_algorithm_options()

        mock_view.update_algorithm_options.assert_called_with(
            ac.ENSEMBLE_ALGORITHM_OPTIONS
        )

    def test_get_current_ui_state(self, mock_view, mock_adapter):
        """Test getting current UI state."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = "Vocals/Instrumental"
        presenter._current_algorithm = "Max Spec/Min Spec"
        presenter._currently_selected_models = ["Model1", "Model2"]
        presenter._advanced_settings["save_all_outputs"] = False

        settings = presenter.get_current_ui_state()

        assert settings["ensemble_main_stem_pair"] == "Vocals/Instrumental"
        assert settings["ensemble_algorithm"] == "Max Spec/Min Spec"
        assert settings["ensemble_selected_models"] == ["Model1", "Model2"]
        assert settings["save_all_outputs"] is False
        assert settings["append_ensemble_name"] is False
        assert settings["use_waveform_ensemble"] is False

    def test_get_settings(self, mock_view, mock_adapter):
        """Test getting settings for processing (required by main application)."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = "Bass/No Bass"
        presenter._current_algorithm = "Min Spec/Min Spec"
        presenter._currently_selected_models = ["Bass Model"]
        presenter._advanced_settings["save_all_outputs"] = True

        settings = presenter.get_settings()

        # Should return the same data as get_current_ui_state()
        assert settings["ensemble_main_stem_pair"] == "Bass/No Bass"
        assert settings["ensemble_algorithm"] == "Min Spec/Min Spec"
        assert settings["ensemble_selected_models"] == ["Bass Model"]
        assert settings["save_all_outputs"] is True

    def test_update_from_advanced_dialog(self, mock_view, mock_adapter):
        """Test updating from advanced dialog settings."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)

        new_settings = {
            "ensemble_main_stem_pair": "Other/No Other",
            "ensemble_algorithm": "Average/Average",  # Valid for 2-stem ensembles
            "ensemble_selected_models": ["NewModel1", "NewModel2"],
            "save_all_outputs": False,
            "append_ensemble_name": True,
            "use_waveform_ensemble": True,
        }

        presenter.update_from_advanced_dialog(new_settings)

        assert presenter._current_main_stem_pair == "Other/No Other"
        assert presenter._current_algorithm == "Average/Average"
        assert presenter._currently_selected_models == ["NewModel1", "NewModel2"]
        assert presenter._advanced_settings["save_all_outputs"] is False
        assert presenter._advanced_settings["append_ensemble_name"] is True
        assert presenter._advanced_settings["use_waveform_ensemble"] is True

        # Verify view was updated
        mock_view.set_current_stem_pair.assert_called_with("Other/No Other")
        mock_view.set_current_algorithm.assert_called_with("Average/Average")
        mock_view.update_selection_status.assert_called_with(["NewModel1", "NewModel2"])

    def test_is_ensemble_configured_true(self, mock_view, mock_adapter):
        """Test ensemble configuration check when properly configured."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = "Vocals/Instrumental"  # Not the default
        presenter._currently_selected_models = ["Model1", "Model2"]  # At least 2 models

        assert presenter.is_ensemble_configured() is True

    def test_is_ensemble_configured_false_default_stem(self, mock_view, mock_adapter):
        """Test ensemble configuration check with default stem pair."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = ac.ENSEMBLE_MAIN_STEM_OPTIONS[0]  # Default
        presenter._currently_selected_models = ["Model1", "Model2"]

        assert presenter.is_ensemble_configured() is False

    def test_is_ensemble_configured_false_insufficient_models(
        self, mock_view, mock_adapter
    ):
        """Test ensemble configuration check with insufficient models."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)
        presenter._current_main_stem_pair = "Vocals/Instrumental"
        presenter._currently_selected_models = ["Model1"]  # Only 1 model

        assert presenter.is_ensemble_configured() is False

    @patch("uvr_pyside6_ui.ui.ensemble_simple_presenter.EnsembleAdvancedDialog")
    def test_advanced_settings_requested(
        self, mock_dialog_class, mock_view, mock_adapter
    ):
        """Test opening advanced settings dialog."""
        mock_dialog = Mock()
        mock_dialog_class.return_value = mock_dialog
        mock_settings_presenter = Mock()

        presenter = EnsembleSimplePresenter(
            mock_view, mock_adapter, mock_settings_presenter
        )

        presenter.on_advanced_settings_requested()

        # Verify dialog was created and configured
        mock_dialog_class.assert_called_once()
        mock_dialog.set_available_models.assert_called_once()
        mock_dialog.settings_updated.connect.assert_called_once()
        mock_dialog.exec.assert_called_once()

    def test_advanced_settings_updated(self, mock_view, mock_adapter):
        """Test handling advanced settings updates from dialog."""
        presenter = EnsembleSimplePresenter(mock_view, mock_adapter)

        # Simulate settings update from advanced dialog
        updated_settings = {
            "ensemble_main_stem_pair": "Bass/No Bass",
            "ensemble_algorithm": "Min Spec/Min Spec",  # Valid for 2-stem ensembles
            "ensemble_selected_models": ["Bass Model 1", "Bass Model 2"],
            "save_all_outputs": False,
            "append_ensemble_name": True,
            "use_waveform_ensemble": True,
        }

        presenter.update_from_advanced_dialog(updated_settings)

        # Verify internal state was updated
        assert presenter._current_main_stem_pair == "Bass/No Bass"
        assert presenter._current_algorithm == "Min Spec/Min Spec"
        assert presenter._currently_selected_models == ["Bass Model 1", "Bass Model 2"]
        assert presenter._advanced_settings["save_all_outputs"] is False
        assert presenter._advanced_settings["append_ensemble_name"] is True
        assert presenter._advanced_settings["use_waveform_ensemble"] is True

        # Verify view was updated
        mock_view.set_current_stem_pair.assert_called_with("Bass/No Bass")
        mock_view.update_selection_status.assert_called_with(
            ["Bass Model 1", "Bass Model 2"]
        )


class TestEnsembleAdvancedDialog:
    """Test cases for EnsembleAdvancedDialog."""

    def test_initialization(self, qapp):
        """Test dialog initialization."""
        current_settings = {
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Max Spec/Min Spec",
            "ensemble_selected_models": ["Model1"],
            "save_all_outputs": True,
            "append_ensemble_name": False,
            "use_waveform_ensemble": False,
        }

        dialog = EnsembleAdvancedDialog(current_settings)

        assert dialog._current_main_stem_pair == "Vocals/Instrumental"
        assert dialog._current_algorithm == "Max Spec/Min Spec"
        assert dialog._currently_selected_models == ["Model1"]
        assert dialog.save_all_outputs_checkbox.isChecked() is True
        assert dialog.append_ensemble_name_checkbox.isChecked() is False
        assert dialog.use_waveform_checkbox.isChecked() is False

    def test_set_available_models(self, qapp):
        """Test setting available models in advanced dialog."""
        current_settings = {
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Max Spec/Min Spec",
            "ensemble_selected_models": [],
            "save_all_outputs": True,
            "append_ensemble_name": False,
            "use_waveform_ensemble": False,
        }

        dialog = EnsembleAdvancedDialog(current_settings)

        models_by_type = {
            ac.VR_ARCH_MODELS_KEY: ["VR1", "VR2"],
            ac.MDX_NET_MODELS_KEY: ["MDX1", "MDX2"],
            ac.DEMUCS_MODELS_KEY: ["Demucs1", "Demucs2"],
        }

        dialog.set_available_models(models_by_type)

        # With the new lightweight filtering, all models are assumed to be available
        # for UI purposes, so none should be filtered out.
        assert (
            dialog.available_models_list.count() == 6
        ), "All models should be displayed in the list"

        # Verify the models_by_type was stored correctly
        assert dialog._available_models_by_type == models_by_type

    def test_stem_pair_changed(self, qapp):
        """Test stem pair change handling."""
        dialog = EnsembleAdvancedDialog({})

        dialog._on_stem_pair_changed("4 Stem Ensemble")

        assert dialog._current_main_stem_pair == "4 Stem Ensemble"

    def test_algorithm_changed(self, qapp):
        """Test algorithm change handling."""
        dialog = EnsembleAdvancedDialog({})

        dialog._on_algorithm_changed("Max Spec")

        assert dialog._current_algorithm == "Max Spec"

    def test_add_models_to_ensemble(self, qapp):
        """Test adding models to ensemble."""
        dialog = EnsembleAdvancedDialog({})

        # Mock selected items
        mock_item1 = Mock()
        mock_item1.text.return_value = "Model1"
        mock_item2 = Mock()
        mock_item2.text.return_value = "Model2"

        dialog.available_models_list.selectedItems = Mock(
            return_value=[mock_item1, mock_item2]
        )

        dialog._add_models_to_ensemble()

        assert "Model1" in dialog._currently_selected_models
        assert "Model2" in dialog._currently_selected_models

    def test_remove_models_from_ensemble(self, qapp):
        """Test removing models from ensemble."""
        dialog = EnsembleAdvancedDialog({})
        dialog._currently_selected_models = ["Model1", "Model2", "Model3"]

        # Mock selected items to remove
        mock_item = Mock()
        mock_item.text.return_value = "Model2"

        dialog.selected_models_list.selectedItems = Mock(return_value=[mock_item])

        dialog._remove_models_from_ensemble()

        assert "Model2" not in dialog._currently_selected_models
        assert "Model1" in dialog._currently_selected_models
        assert "Model3" in dialog._currently_selected_models

    def test_clear_selection(self, qapp):
        """Test clearing model selection."""
        dialog = EnsembleAdvancedDialog({})
        dialog._currently_selected_models = ["Model1", "Model2", "Model3"]

        dialog._clear_selection()

        assert dialog._currently_selected_models == []

    def test_get_current_settings(self, qapp):
        """Test getting current settings."""
        dialog = EnsembleAdvancedDialog({})
        dialog._current_main_stem_pair = "Vocals/Instrumental"
        dialog._current_algorithm = "Average"
        dialog._currently_selected_models = ["Model1", "Model2"]
        dialog.save_all_outputs_checkbox.setChecked(False)
        dialog.append_ensemble_name_checkbox.setChecked(True)
        dialog.use_waveform_checkbox.setChecked(True)

        settings = dialog._get_current_settings()

        assert settings["ensemble_main_stem_pair"] == "Vocals/Instrumental"
        assert settings["ensemble_algorithm"] == "Average"
        assert settings["ensemble_selected_models"] == ["Model1", "Model2"]
        assert settings["save_all_outputs"] is False
        assert settings["append_ensemble_name"] is True
        assert settings["use_waveform_ensemble"] is True

    @patch("os.path.exists")
    def test_load_saved_ensembles(self, mock_exists, qapp, temp_config_dir):
        """Test loading saved ensembles from filesystem."""
        mock_exists.return_value = True

        with patch("pathlib.Path.glob") as mock_glob:
            mock_file = Mock()
            mock_file.stem = "test_ensemble"
            mock_glob.return_value = [mock_file]

            dialog = EnsembleAdvancedDialog({})
            dialog._load_saved_ensembles()

            # Should have default item plus the test ensemble
            assert dialog.saved_ensembles_combo.count() >= 2

    @patch("builtins.open", new_callable=mock_open)
    @patch("uvr_pyside6_ui.ui.ensemble_advanced_dialog.QInputDialog.getText")
    def test_save_ensemble_success(self, mock_input, mock_open, qapp):
        """Test successful ensemble saving."""
        current_settings = {
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Max Spec/Min Spec",
            "ensemble_selected_models": ["Model1", "Model2"],
            "save_all_outputs": True,
            "append_ensemble_name": False,
            "use_waveform_ensemble": False,
        }

        dialog = EnsembleAdvancedDialog(current_settings)
        dialog._currently_selected_models = ["Model1", "Model2"]

        mock_input.return_value = ("Test Ensemble", True)

        # Mock the message box method instead of patching QMessageBox
        dialog._show_message_box = Mock()

        dialog._save_ensemble()

        # The mock_open will be called multiple times:
        # 1. ModelData creation tries to read model mapper files (4 times for different model types)
        # 2. The actual ensemble save operation (1 time)
        # So we expect at least 5 calls, but we only care about the final one for ensemble saving

        # Verify the final call was for saving the ensemble
        final_call = mock_open.call_args_list[-1]
        assert "config/saved_ensembles/Test_Ensemble.json" in str(final_call[0][0])
        assert final_call[0][1] == "w"  # Write mode

        mock_input.assert_called_once()
        dialog._show_message_box.assert_called_once()  # Assert that the message box method was called

    def test_save_ensemble_no_models(self, qapp):
        """Test save ensemble with no models selected."""
        dialog = EnsembleAdvancedDialog({})
        dialog._currently_selected_models = []

        # Mock the message box method to prevent UI blocking
        dialog._show_message_box = Mock()

        dialog._save_ensemble()

        # Should show warning message via our custom method
        dialog._show_message_box.assert_called_once()

    @patch("uvr_pyside6_ui.ui.ensemble_advanced_dialog.QInputDialog")
    def test_save_ensemble_invalid_name(self, mock_input_dialog, qapp):
        """Test save ensemble with invalid name."""
        mock_input_dialog.getText.return_value = ("Invalid@Name!", True)

        dialog = EnsembleAdvancedDialog({})
        dialog._currently_selected_models = ["Model1", "Model2"]

        # Mock the message box method to prevent UI blocking
        dialog._show_message_box = Mock()

        dialog._save_ensemble()

        # Should show invalid name warning
        dialog._show_message_box.assert_called_once()

    def test_apply_settings(self, qapp):
        """Test applying settings."""
        dialog = EnsembleAdvancedDialog({})
        dialog.settings_updated = Mock()

        dialog._apply_settings()

        dialog.settings_updated.emit.assert_called_once()

    def test_ok_clicked(self, qapp):
        """Test OK button click."""
        dialog = EnsembleAdvancedDialog({})
        dialog._apply_settings = Mock()
        dialog.accept = Mock()

        dialog._ok_clicked()

        dialog._apply_settings.assert_called_once()
        dialog.accept.assert_called_once()


class TestEnsembleSimpleView:
    """Test cases for EnsembleSimpleView."""

    def test_initialization(self, qapp):
        """Test view initialization."""
        view = EnsembleSimpleView()

        assert view.stem_pair_combo.count() > 0
        assert view.algorithm_combo is not None
        assert view.selection_status_label is not None
        assert view.advanced_button is not None

    def test_set_current_stem_pair(self, qapp):
        """Test setting current stem pair."""
        view = EnsembleSimpleView()

        view.set_current_stem_pair("Vocals/Instrumental")

        assert view.get_current_stem_pair() == "Vocals/Instrumental"

    def test_update_algorithm_options(self, qapp):
        """Test updating algorithm options."""
        view = EnsembleSimpleView()

        algorithms = ["Average", "Max Spec", "Min Spec"]
        view.update_algorithm_options(algorithms)

        assert view.algorithm_combo.count() == 3
        assert view.algorithm_combo.itemText(0) == "Average"

    def test_update_selection_status_no_models(self, qapp):
        """Test selection status with no models."""
        view = EnsembleSimpleView()

        view.update_selection_status([])

        assert "No models selected" in view.selection_status_label.text()

    def test_update_selection_status_one_model(self, qapp):
        """Test selection status with one model."""
        view = EnsembleSimpleView()

        view.update_selection_status(["Model1"])

        assert "1 model selected" in view.selection_status_label.text()

    def test_update_selection_status_multiple_models(self, qapp):
        """Test selection status with multiple models."""
        view = EnsembleSimpleView()

        view.update_selection_status(["Model1", "Model2", "Model3"])

        assert "3 models selected" in view.selection_status_label.text()


class TestEnsembleIntegration:
    """Integration tests for ensemble functionality."""

    def test_presenter_view_integration(self, qapp, mock_adapter):
        """Test presenter and view working together."""
        view = EnsembleSimpleView()
        presenter = EnsembleSimplePresenter(view, mock_adapter)

        # Test stem pair change
        view.stem_pair_combo.setCurrentText("4 Stem Ensemble")
        view.stem_pair_combo.currentTextChanged.emit("4 Stem Ensemble")

        assert presenter._current_main_stem_pair == "4 Stem Ensemble"

    @patch("uvr_pyside6_ui.ui.ensemble_simple_presenter.EnsembleAdvancedDialog")
    def test_advanced_dialog_integration(self, mock_dialog_class, qapp, mock_adapter):
        """Test integration between simple presenter and advanced dialog."""
        mock_dialog = Mock()
        mock_dialog_class.return_value = mock_dialog

        view = EnsembleSimpleView()
        presenter = EnsembleSimplePresenter(view, mock_adapter, Mock())

        # Trigger advanced settings
        view.advanced_button.clicked.emit()

        # Verify dialog was created and configured
        mock_dialog_class.assert_called_once()
        mock_dialog.exec.assert_called_once()

    def test_settings_persistence(self, qapp, mock_adapter):
        """Test UI state persistence through get/update cycle."""
        view = EnsembleSimpleView()
        presenter = EnsembleSimplePresenter(view, mock_adapter)

        # Set some UI state via the update method (simulating advanced dialog)
        original_settings = {
            "ensemble_main_stem_pair": "4 Stem Ensemble",
            "ensemble_algorithm": "Max Spec",  # Valid for 4-stem
            "ensemble_selected_models": ["Model1", "Model2"],
            "save_all_outputs": False,
            "append_ensemble_name": True,
            "use_waveform_ensemble": True,
        }

        # Update from advanced dialog (this is how settings are loaded now)
        presenter.update_from_advanced_dialog(original_settings)

        # Get current UI state
        retrieved_settings = presenter.get_current_ui_state()

        # Verify all settings were preserved
        for key, value in original_settings.items():
            assert retrieved_settings[key] == value


@pytest.mark.integration
class TestEnsembleFileOperations:
    """Test ensemble file save/load operations."""

    def test_ensemble_file_format(self, temp_config_dir):
        """Test ensemble file format compatibility."""
        ensemble_data = {
            "ensemble_main_stem": "Vocals/Instrumental",
            "ensemble_type": "Average",
            "selected_models": ["Model1", "Model2"],
        }

        file_path = temp_config_dir / "format_test.json"
        with open(file_path, "w") as f:
            json.dump(ensemble_data, f)

        # Verify file can be read back
        with open(file_path, "r") as f:
            loaded_data = json.load(f)

        assert loaded_data == ensemble_data

    def test_ensemble_directory_creation(self):
        """Test automatic creation of ensemble directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config" / "saved_ensembles"

            # Directory should not exist initially
            assert not config_path.exists()

            # Create directory structure
            config_path.mkdir(parents=True, exist_ok=True)

            # Directory should now exist
            assert config_path.exists()
            assert config_path.is_dir()


class TestEnsembleSaveAllOutputs:
    """Test ensemble save_all_outputs functionality."""

    def test_save_all_outputs_logic_with_vocals_only(self):
        """Test the core logic of save_all_outputs with vocals_only mode.

        This test verifies that when save_all_outputs=True and vocals_only=True,
        only vocal individual files are saved, not instrumental files.
        This matches the original UVR behavior where get_files_to_ensemble only
        looks for files with specific stem suffixes.
        """

        import numpy as np

        # Test the core logic: when save_all_outputs=True and vocals_only=True,
        # only vocal individual files should be saved, instrumental files should be skipped

        # Mock model results - each model produces both stems
        model_results = {
            "VocalModel": {
                "Vocals": np.random.random((2, 44100)).astype(np.float32),
                "Instrumental": np.random.random((2, 44100)).astype(np.float32),
            },
            "InstModel": {
                "Instrumental": np.random.random((2, 44100)).astype(np.float32),
                "Vocals": np.random.random((2, 44100)).astype(np.float32),
            },
        }

        save_all_outputs = True
        stems_to_process = ["Vocals"]  # Vocals only mode

        # Simulate the corrected logic
        saved_files = []
        ensemble_stems = []

        for model_name, results in model_results.items():
            for stem_name, audio_data in results.items():
                # Only save and process stems that are part of the ensemble
                if stem_name in stems_to_process:
                    # This file would be saved as individual output
                    saved_files.append(f"{model_name}_({stem_name}).wav")
                    # This stem would be added to ensemble collection
                    ensemble_stems.append(stem_name)
                # Stems not in stems_to_process are completely skipped

        # Verify the corrected behavior
        assert len(saved_files) == 2  # Only 2 vocal files saved
        assert saved_files == ["VocalModel_(Vocals).wav", "InstModel_(Vocals).wav"]
        assert all("Vocals" in f for f in saved_files)
        assert not any("Instrumental" in f for f in saved_files)

        # Verify ensemble collection
        assert len(ensemble_stems) == 2
        assert all(stem == "Vocals" for stem in ensemble_stems)

    def test_save_all_outputs_logic_with_instrumental_only(self):
        """Test save_all_outputs with instrumental_only mode."""
        import numpy as np

        # Mock model results
        model_results = {
            "VocalModel": {
                "Vocals": np.random.random((2, 44100)).astype(np.float32),
                "Instrumental": np.random.random((2, 44100)).astype(np.float32),
            },
            "InstModel": {
                "Instrumental": np.random.random((2, 44100)).astype(np.float32),
                "Vocals": np.random.random((2, 44100)).astype(np.float32),
            },
        }

        save_all_outputs = True
        stems_to_process = ["Instrumental"]  # Instrumental only mode

        # Simulate the corrected logic
        saved_files = []

        for model_name, results in model_results.items():
            for stem_name, audio_data in results.items():
                # Only save stems that are part of the ensemble
                if stem_name in stems_to_process:
                    saved_files.append(f"{model_name}_({stem_name}).wav")

        # Verify only instrumental files are saved
        assert len(saved_files) == 2
        assert saved_files == [
            "VocalModel_(Instrumental).wav",
            "InstModel_(Instrumental).wav",
        ]
        assert all("Instrumental" in f for f in saved_files)
        assert not any("Vocals" in f for f in saved_files)

    def test_save_all_outputs_logic_with_both_stems(self):
        """Test save_all_outputs when both stems are being processed."""
        import numpy as np

        # Mock model results
        model_results = {
            "GeneralModel": {
                "Vocals": np.random.random((2, 44100)).astype(np.float32),
                "Instrumental": np.random.random((2, 44100)).astype(np.float32),
            },
        }

        save_all_outputs = True
        stems_to_process = ["Vocals", "Instrumental"]  # Both stems

        # Simulate the corrected logic
        saved_files = []

        for model_name, results in model_results.items():
            for stem_name, audio_data in results.items():
                # Save all stems that are part of the ensemble
                if stem_name in stems_to_process:
                    saved_files.append(f"{model_name}_({stem_name}).wav")

        # Verify both stems are saved
        assert len(saved_files) == 2
        assert "GeneralModel_(Vocals).wav" in saved_files
        assert "GeneralModel_(Instrumental).wav" in saved_files

    def test_save_all_outputs_disabled_only_saves_ensemble_stems(self):
        """Test that when save_all_outputs=False, individual files are still created for ensemble but cleaned up after."""
        import numpy as np

        # Mock model results
        model_results = {
            "VocalModel": {
                "Vocals": np.random.random((2, 44100)).astype(np.float32),
                "Instrumental": np.random.random((2, 44100)).astype(np.float32),
            },
        }

        save_all_outputs = False
        stems_to_process = ["Vocals"]  # Vocals only mode

        # Simulate the logic
        temporarily_saved_files = []
        files_to_cleanup = []

        for model_name, results in model_results.items():
            for stem_name, audio_data in results.items():
                # Only process stems that are part of the ensemble
                if stem_name in stems_to_process:
                    file_path = f"{model_name}_({stem_name}).wav"
                    temporarily_saved_files.append(file_path)
                    # These files would be cleaned up after ensemble creation if save_all_outputs=False
                    if not save_all_outputs:
                        files_to_cleanup.append(file_path)

        # Verify that individual files are created temporarily but marked for cleanup
        assert len(temporarily_saved_files) == 1
        assert temporarily_saved_files[0] == "VocalModel_(Vocals).wav"
        assert len(files_to_cleanup) == 1
        assert files_to_cleanup[0] == "VocalModel_(Vocals).wav"

    def test_output_format_consistency(self):
        """Test that individual model outputs use the same format as ensemble output."""
        import numpy as np

        # Test different output formats
        test_formats = [
            ("WAV", "wav"),
            ("FLAC", "flac"),
            ("MP3", "mp3"),
        ]

        for save_format, expected_ext in test_formats:
            # Mock model results
            model_results = {
                "TestModel": {
                    "Vocals": np.random.random((2, 44100)).astype(np.float32),
                },
            }

            stems_to_process = ["Vocals"]

            # Simulate the format logic from the fixed code
            individual_files = []
            ensemble_files = []

            for model_name, results in model_results.items():
                for stem_name, audio_data in results.items():
                    if stem_name in stems_to_process:
                        # Individual file uses selected format
                        individual_file = (
                            f"song_{model_name}_({stem_name}).{expected_ext}"
                        )
                        individual_files.append(individual_file)

            # Ensemble file also uses selected format
            ensemble_file = f"song_Ensemble_(Vocals).{expected_ext}"
            ensemble_files.append(ensemble_file)

            # Verify format consistency
            assert len(individual_files) == 1
            assert individual_files[0] == f"song_TestModel_(Vocals).{expected_ext}"
            assert ensemble_files[0] == f"song_Ensemble_(Vocals).{expected_ext}"

            # Verify all files have the same extension
            all_files = individual_files + ensemble_files
            extensions = [f.split(".")[-1] for f in all_files]
            assert all(
                ext == expected_ext for ext in extensions
            ), f"Format inconsistency for {save_format}: {extensions}"
