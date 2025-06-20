"""
Unit tests for ensemble persistence functionality.

This module tests the EnsemblePersistenceManager to ensure proper
saving, loading, and management of ensemble configurations.
"""

import json
import tempfile
from pathlib import Path

import pytest
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core.ensemble_persistence_manager import EnsemblePersistenceManager


@pytest.mark.unit
@pytest.mark.ensemble
@pytest.mark.persistence
class TestEnsemblePersistenceManager:
    """Test cases for EnsemblePersistenceManager."""

    def test_initialization(self):
        """Test manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            assert manager.ensemble_cache_dir == cache_dir
            assert cache_dir.exists()

            # Should create placeholder file
            placeholder = cache_dir / "saved_ensembles_go_here.txt"
            assert placeholder.exists()

    def test_save_ensemble_success(self):
        """Test successful ensemble saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            # Set up signal spy
            saved_spy = QSignalSpy(manager.ensemble_saved)

            # Save ensemble
            success = manager.save_ensemble(
                name="Test Ensemble",
                main_stem_pair="Vocals/Instrumental",
                algorithm="Average/Average",
                selected_models=["model1.pth", "model2.onnx"],
            )

            assert success is True
            assert saved_spy.count() == 1
            assert saved_spy.at(0) == ["Test Ensemble"]

            # Check file was created
            ensemble_file = cache_dir / "Test_Ensemble.json"
            assert ensemble_file.exists()

            # Check file content
            with open(ensemble_file, "r") as f:
                data = json.load(f)

            assert data["ensemble_main_stem"] == "Vocals/Instrumental"
            assert data["ensemble_type"] == "Average/Average"
            assert data["selected_models"] == ["model1.pth", "model2.onnx"]
            assert data["_metadata"]["display_name"] == "Test Ensemble"

    def test_save_ensemble_validation_failure(self):
        """Test ensemble save with validation failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            # Test empty name
            result = manager.save_ensemble(
                "", "Vocals/Instrumental", "Average/Average", ["model1", "model2"]
            )
            assert result is False

            # Test invalid characters in name
            result = manager.save_ensemble(
                "test@name",
                "Vocals/Instrumental",
                "Average/Average",
                ["model1", "model2"],
            )
            assert result is False

            # Test invalid stem pair
            result = manager.save_ensemble(
                "Test", "4 Stem Ensemble", "Average/Average", ["model1", "model2"]
            )
            assert result is False

            # Test invalid algorithm
            result = manager.save_ensemble(
                "Test", "Vocals/Instrumental", "Invalid Algorithm", ["model1", "model2"]
            )
            assert result is False

            # Test empty algorithm
            result = manager.save_ensemble(
                "Test", "Vocals/Instrumental", "", ["model1", "model2"]
            )
            assert result is False

            # Test insufficient models
            result = manager.save_ensemble(
                "Test", "Vocals/Instrumental", "Average/Average", ["model1"]
            )
            assert result is False

            # Test empty models
            result = manager.save_ensemble(
                "Test", "Vocals/Instrumental", "Average/Average", []
            )
            assert result is False

    def test_load_ensemble_success(self):
        """Test successful ensemble loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            # Create test ensemble file
            ensemble_data = {
                "ensemble_main_stem": "Vocals/Instrumental",
                "ensemble_type": "Average/Average",
                "selected_models": ["model1.pth", "model2.onnx"],
                "_metadata": {"display_name": "Test Ensemble"},
            }

            ensemble_file = cache_dir / "Test_Ensemble.json"
            with open(ensemble_file, "w") as f:
                json.dump(ensemble_data, f)

            # Load ensemble
            loaded_data = manager.load_ensemble("Test Ensemble")

            assert loaded_data is not None
            assert loaded_data["ensemble_main_stem"] == "Vocals/Instrumental"
            assert loaded_data["ensemble_type"] == "Average/Average"
            assert loaded_data["selected_models"] == ["model1.pth", "model2.onnx"]

    def test_get_available_ensembles(self):
        """Test getting list of available ensembles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            # Create test ensemble files
            ensemble1_data = {
                "ensemble_main_stem": "Vocals/Instrumental",
                "ensemble_type": "Average/Average",
                "selected_models": ["model1.pth", "model2.onnx"],
                "_metadata": {"display_name": "First Ensemble"},
            }

            ensemble2_data = {
                "ensemble_main_stem": "Vocals/Instrumental",
                "ensemble_type": "Max/Max",
                "selected_models": ["model3.pth", "model4.onnx"],
                "_metadata": {"display_name": "Second Ensemble"},
            }

            # Save ensembles
            with open(cache_dir / "First_Ensemble.json", "w") as f:
                json.dump(ensemble1_data, f)

            with open(cache_dir / "Second_Ensemble.json", "w") as f:
                json.dump(ensemble2_data, f)

            # Get available ensembles
            ensembles = manager.get_available_ensembles()

            assert len(ensembles) == 2
            display_names = [e["display_name"] for e in ensembles]
            assert "First Ensemble" in display_names
            assert "Second Ensemble" in display_names


@pytest.mark.regression
@pytest.mark.ensemble
@pytest.mark.persistence
class TestEnsemblePersistenceRegression:
    """Regression tests for ensemble persistence."""

    def test_ensemble_persistence_prevents_data_loss(self):
        """
        CRITICAL Regression test: Ensemble configurations should persist correctly.

        This test prevents regression of ensemble data loss issues.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            # Save ensemble
            ensemble_name = "Critical Test Ensemble"
            models = [
                "important_model1.pth",
                "important_model2.onnx",
                "backup_model.pth",
            ]

            success = manager.save_ensemble(
                name=ensemble_name,
                main_stem_pair="Vocals/Instrumental",
                algorithm="Average/Average",
                selected_models=models,
            )

            assert success is True

            # Verify file exists and is readable
            ensemble_file = cache_dir / "Critical_Test_Ensemble.json"
            assert ensemble_file.exists()

            # Load and verify data integrity
            loaded_data = manager.load_ensemble(ensemble_name)
            assert loaded_data is not None
            assert loaded_data["selected_models"] == models
            assert len(loaded_data["selected_models"]) == 3

    def test_legacy_format_compatibility(self):
        """
        Regression test: Should handle legacy UVR ensemble format.

        This ensures backward compatibility with original UVR ensemble files.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "ensembles"
            manager = EnsemblePersistenceManager(cache_dir)

            # Create legacy format ensemble file (without metadata)
            legacy_data = {
                "ensemble_main_stem": "Vocals/Instrumental",
                "ensemble_type": "Average/Average",
                "selected_models": ["legacy_model1.pth", "legacy_model2.pth"],
            }

            legacy_file = cache_dir / "Legacy_Ensemble.json"
            with open(legacy_file, "w") as f:
                json.dump(legacy_data, f)

            # Should load successfully
            loaded_data = manager.load_ensemble("Legacy Ensemble")
            assert loaded_data is not None
            assert loaded_data["ensemble_main_stem"] == "Vocals/Instrumental"
            assert loaded_data["selected_models"] == [
                "legacy_model1.pth",
                "legacy_model2.pth",
            ]

            # Should normalize the data
            assert "ensemble_main_stem_pair" in loaded_data
            assert "ensemble_algorithm" in loaded_data
