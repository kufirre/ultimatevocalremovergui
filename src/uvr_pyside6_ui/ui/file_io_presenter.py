from PySide6.QtCore import QObject, Slot


class FileIOPresenter(QObject):
    """
    Presenter for the File I/O View. Connects View signals to
    handling logic and will later interact with the Model/Adapter.
    """

    def __init__(self, view):
        super().__init__()
        self.view = view
        # self.model = model # This will be the uvr_core_adapter later

        # --- Store the state ---
        self._input_path = ""
        self._output_path = ""

        # --- Connect signals from View to Presenter's slots ---
        self.view.select_input_clicked.connect(self.handle_select_input)
        self.view.select_output_clicked.connect(self.handle_select_output)
        self.view.input_path_changed.connect(self.handle_input_path_update)
        self.view.output_path_changed.connect(self.handle_output_path_update)

        # Debug print removed

    @Slot()
    def handle_select_input(self):
        """Handles the 'Browse...' click for input."""
        # Debug print removed
        # Tell the View to perform the action of showing the dialog.
        self.view.show_input_file_dialog()

    @Slot()
    def handle_select_output(self):
        """Handles the 'Browse...' click for output."""
        # Debug print removed
        self.view.show_output_folder_dialog()

    @Slot(str)
    def handle_input_path_update(self, path):
        """Updates the internal state when input path changes."""
        if self._input_path != path:
            self._input_path = path
            # Debug print removed
            # Here you would typically:
            # - Validate the path.
            # - Update the model or application state.
            # - Potentially enable/disable other UI elements via their presenters.
            # - Maybe update the view IF validation changes the path.

    @Slot(str)
    def handle_output_path_update(self, path):
        """Updates the internal state when output path changes."""
        if self._output_path != path:
            self._output_path = path
            # Debug print removed
            # Add validation and model updates here too.

    # --- Public methods (if needed by other parts) ---
    def get_paths(self):
        """Provides the current paths to other components if needed."""
        return self._input_path, self._output_path
