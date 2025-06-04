"""Worker thread for downloading models without blocking the UI."""

from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot

from . import model_downloader


class DownloadWorker(QObject):
    """Worker object that runs in a separate thread to download models."""

    # Signals
    progress = Signal(str, int)  # filename, percentage
    finished = Signal(bool, str, str, str)  # success, model_path, config_path, message

    def __init__(
        self,
        model_name: str,
        download_url: str,
        model_type: str,
        config_url: Optional[str] = None,
    ):
        super().__init__()
        self.model_name = model_name
        self.download_url = download_url
        self.model_type = model_type
        self.config_url = config_url
        self._is_cancelled = False

    def cancel(self):
        """Cancels the download operation if possible."""
        self._is_cancelled = True

    @Slot()
    def run(self):
        """Main worker method that runs in the thread."""
        try:
            # Use the progress signal as the callback
            success, model_path_or_msg, config_path = (
                model_downloader.download_model_file(
                    self.model_name,
                    self.download_url,
                    self.model_type,
                    self.config_url,
                    self.progress.emit,  # Pass the signal directly as the callback
                )
            )

            if success:
                message = f"✅ Successfully downloaded {self.model_name}"
                self.finished.emit(
                    True, model_path_or_msg, config_path if config_path else "", message
                )
            else:
                self.finished.emit(False, "", "", f"❌ {model_path_or_msg}")

        except Exception as e:
            error_msg = f"❌ Error downloading {self.model_name}: {str(e)}"
            self.finished.emit(False, "", "", error_msg)


class DownloadManager(QObject):
    """Manages download workers and threads."""

    # Forward signals from workers
    download_progress = Signal(str, int)  # filename, percentage
    download_finished = Signal(
        bool, str, str, str
    )  # success, model_path, config_path, message

    def __init__(self):
        super().__init__()
        self.active_threads: List[QThread] = []
        self.active_workers: List[DownloadWorker] = []

    def start_download(
        self,
        model_name: str,
        download_url: str,
        model_type: str,
        config_url: Optional[str] = None,
    ):
        """Starts a download in a separate thread."""

        # Create worker and thread
        worker = DownloadWorker(model_name, download_url, model_type, config_url)
        thread = QThread()

        # Move worker to thread
        worker.moveToThread(thread)

        # Connect signals
        thread.started.connect(worker.run)
        worker.progress.connect(self.download_progress)
        worker.finished.connect(self.download_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))

        # Store references
        self.active_threads.append(thread)
        self.active_workers.append(worker)

        # Start the thread
        thread.start()

        return worker  # Return worker in case caller wants to cancel

    def _cleanup_thread(self, thread: QThread, worker: DownloadWorker):
        """Remove thread and worker from active lists when finished."""
        if thread in self.active_threads:
            self.active_threads.remove(thread)
        if worker in self.active_workers:
            self.active_workers.remove(worker)

    def cancel_all_downloads(self):
        """Attempts to cancel all active downloads."""
        for worker in self.active_workers:
            worker.cancel()
