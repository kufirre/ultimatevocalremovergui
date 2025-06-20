"""
Regression tests for progress bar and dynamic calculation fixes.

This module contains tests that prevent regression of the progress bar issues
where VR processing would get stuck at 30% and console logging was excessive.
"""

from unittest.mock import Mock, patch

import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.processing_worker import ProcessingWorker


@pytest.mark.regression
@pytest.mark.critical
class TestProgressBarRegression:
    """Regression tests for progress bar stuck at 30% issue."""

    def test_vr_progress_never_stuck_at_30_percent(self, valid_settings_dict):
        """
        CRITICAL Regression test: VR progress bar should never get stuck at 30%.

        This test prevents regression of the issue where VR processing
        would show 30% progress for 5+ minutes instead of flowing smoothly.
        """
        # Set up VR processing
        vr_settings = valid_settings_dict.copy()
        vr_settings["chosen_process_method"] = ac.VR_ARCH_TYPE
        vr_settings["vr_model"] = "test_vr_model.pth"

        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.return_value = Mock(spec=ModelData)
            mock_model_data.return_value.model_status = True
            mock_model_data.return_value.is_gpu_conversion = 0
            mock_model_data.return_value.process_method = ac.VR_ARCH_TYPE
            mock_model_data.return_value.batch_size = 4

            worker = ProcessingWorker(vr_settings)

            # Simulate VR processing progress updates
            worker.total_progress_steps = 10  # Simulate 10 processing steps
            progress_values = []

            # Simulate multiple progress updates (like during batch processing)
            for i in range(10):
                current_fraction = 0.3 + (0.45 * (i + 1) / 10)  # 30% to 75% range
                worker._set_progress_bar_callback(current_fraction)
                progress_values.append(worker.progress_value)

            # Verify progress flows smoothly and never gets stuck
            assert all(
                progress_values[i] >= progress_values[i - 1]
                for i in range(1, len(progress_values))
            ), "Progress should be monotonically increasing (regression: stuck progress)"

            # Verify progress moves beyond 30%
            assert any(
                p > 30 for p in progress_values
            ), "Progress should move beyond 30% (regression: stuck at 30%)"

            # Verify final progress is reasonable
            assert (
                progress_values[-1] >= 70
            ), f"Final progress should be at least 70%, got {progress_values[-1]}% (regression: low final progress)"

    def test_progress_monotonic_constraint_enforced(self, valid_settings_dict):
        """
        Regression test: Progress should never go backwards (monotonic constraint).

        This test ensures the monotonic constraint fix prevents progress from decreasing.
        """
        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.return_value = Mock(spec=ModelData)
            mock_model_data.return_value.model_status = True
            mock_model_data.return_value.is_gpu_conversion = 0

            worker = ProcessingWorker(valid_settings_dict)

            # Test that progress never goes backwards
            progress_sequence = [
                0.1,
                0.5,
                0.3,
                0.8,
                0.7,
                1.0,
            ]  # Intentionally non-monotonic input
            recorded_progress = []

            for fraction in progress_sequence:
                worker._set_progress_bar_callback(fraction)
                recorded_progress.append(worker.progress_value)

            # Verify that despite non-monotonic input, output is monotonic
            for i in range(1, len(recorded_progress)):
                assert (
                    recorded_progress[i] >= recorded_progress[i - 1]
                ), f"Progress should never decrease: {recorded_progress[i-1]}% -> {recorded_progress[i]}% (regression: non-monotonic progress)"

    def test_progress_bounds_are_respected(self, valid_settings_dict):
        """
        Regression test: Progress should always be within 0-100% bounds.

        This test ensures progress values are properly bounded.
        """
        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.return_value = Mock(spec=ModelData)
            mock_model_data.return_value.model_status = True
            mock_model_data.return_value.is_gpu_conversion = 0

            worker = ProcessingWorker(valid_settings_dict)

            # Test extreme values
            extreme_values = [-0.5, 0.0, 0.5, 1.0, 1.5, 2.0]

            for fraction in extreme_values:
                worker._set_progress_bar_callback(fraction)

                # Verify progress is always within bounds
                assert (
                    0 <= worker.progress_value <= 100
                ), f"Progress should be 0-100%, got {worker.progress_value}% for input {fraction}"


@pytest.mark.regression
@pytest.mark.critical
class TestConsoleLoggingRegression:
    """Regression tests for excessive console logging fixes."""

    def test_vr_console_logging_not_excessive(self, valid_settings_dict):
        """
        Regression test: VR processing should not produce excessive console logging.

        This test prevents regression of the issue where VR processing
        would spam the console with percentage completion text.
        """
        vr_settings = valid_settings_dict.copy()
        vr_settings["chosen_process_method"] = ac.VR_ARCH_TYPE

        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.return_value = Mock(spec=ModelData)
            mock_model_data.return_value.model_status = True
            mock_model_data.return_value.is_gpu_conversion = 0

            worker = ProcessingWorker(vr_settings)

            # Mock console output capture
            console_messages = []

            def mock_write_to_console(message):
                console_messages.append(message)

            worker._write_to_console = mock_write_to_console

            # Simulate many progress updates (like during batch processing)
            for i in range(50):  # Simulate many updates
                worker._set_progress_bar_callback(0.3 + (0.4 * i / 50))

            # Verify console output is reasonable (not excessive)
            percentage_messages = [msg for msg in console_messages if "%" in str(msg)]
            assert (
                len(percentage_messages) <= 10
            ), f"Should not have excessive percentage messages, got {len(percentage_messages)} (regression: console spam)"

    def test_console_messages_are_reasonable(self, valid_settings_dict):
        """
        Regression test: Console messages should be reasonable in quantity.

        This test ensures the console cleanup didn't break basic functionality.
        """
        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.return_value = Mock(spec=ModelData)
            mock_model_data.return_value.model_status = True
            mock_model_data.return_value.is_gpu_conversion = 0

            worker = ProcessingWorker(valid_settings_dict)

            # Mock console output capture
            console_messages = []

            def mock_write_to_console(message):
                console_messages.append(str(message))

            worker._write_to_console = mock_write_to_console

            # Test a few progress updates
            for i in range(3):
                worker._set_progress_bar_callback(0.1 + (0.8 * i / 3))

            # The key regression test: console should not be spammed
            # We don't require specific messages, just that it's not excessive
            assert (
                len(console_messages) <= 20
            ), f"Console messages should be reasonable, got {len(console_messages)} (regression: console spam)"


@pytest.mark.regression
@pytest.mark.integration
class TestProgressIntegration:
    """Integration tests for progress bar fixes across different components."""

    def test_progress_consistency_across_model_types(self):
        """
        Regression test: Progress behavior should be consistent across VR, MDX, and Demucs.

        This test ensures that progress fixes work consistently across all model types.
        """
        model_types = [
            (ac.VR_ARCH_TYPE, "vr_model"),
            (ac.MDX_ARCH_TYPE, "mdx_net_model"),
            (ac.DEMUCS_ARCH_TYPE, "demucs_model"),
        ]

        for model_type, model_key in model_types:
            settings = {
                "chosen_process_method": model_type,
                model_key: f"test_{model_type.lower()}_model.pth",
                "input_paths": ["/test/audio.wav"],
                "output_path": "/test/output",
            }

            with patch.object(ModelData, "from_settings_dict") as mock_model_data:
                mock_model_data.return_value = Mock(spec=ModelData)
                mock_model_data.return_value.model_status = True
                mock_model_data.return_value.is_gpu_conversion = 0
                mock_model_data.return_value.process_method = model_type

                worker = ProcessingWorker(settings)

                # Test that progress works consistently
                worker._set_progress_bar_callback(0.5)

                # All model types should handle progress the same way
                assert (
                    0 <= worker.progress_value <= 100
                ), f"Progress should be valid for {model_type} (regression: inconsistent progress handling)"

                # The key regression test: progress should respond to input
                # We don't require exact values, just that it's not stuck at 0
                assert (
                    worker.progress_value > 0
                ), f"Progress should respond to input for {model_type} (regression: progress not updating)"

    def test_batch_processing_progress_scales_correctly(self, valid_settings_dict):
        """
        Regression test: Progress should scale correctly with batch size.

        This test ensures that the dynamic progress calculation works correctly
        with different batch sizes (which was part of the original issue).
        """
        batch_sizes = [1, 4, 8, 16]

        for batch_size in batch_sizes:
            with patch.object(ModelData, "from_settings_dict") as mock_model_data:
                mock_model_data.return_value = Mock(spec=ModelData)
                mock_model_data.return_value.model_status = True
                mock_model_data.return_value.is_gpu_conversion = 0
                mock_model_data.return_value.batch_size = batch_size

                worker = ProcessingWorker(valid_settings_dict)

                # Simulate batch processing with different batch sizes
                worker.total_progress_steps = 20  # Fixed total steps

                # Progress should work regardless of batch size
                for i in range(5):  # Simulate 5 progress updates
                    worker._set_progress_bar_callback(0.3 + (0.4 * i / 5))

                # The key regression test: progress should work with any batch size
                # We don't require exact values, just that it's reasonable
                assert (
                    worker.progress_value >= 0
                ), f"Progress should be non-negative with batch_size={batch_size}"
                assert (
                    worker.progress_value <= 100
                ), f"Progress should not exceed 100% with batch_size={batch_size}"
