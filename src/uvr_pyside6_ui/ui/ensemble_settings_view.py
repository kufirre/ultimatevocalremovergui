from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QHBoxLayout, QComboBox
)
from PySide6.QtCore import Signal, Slot


class EnsembleSettingsView(QWidget):
    """
    View for Ensemble specific settings. Allows adding/removing models
    and configuring how they are combined.
    """
    add_model_clicked = Signal()
    remove_model_clicked = Signal()
    merge_method_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        settings_group = QGroupBox("Ensemble Settings")
        settings_layout = QVBoxLayout(settings_group)

        # --- Information Label ---
        info_label = QLabel("Build your ensemble by adding and configuring models.")
        settings_layout.addWidget(info_label)

        # --- Model List and Controls ---
        list_layout = QHBoxLayout()
        self.model_list = QListWidget()
        self.model_list.setToolTip("Models currently in the ensemble.")
        list_controls = QVBoxLayout()

        self.add_button = QPushButton("Add Model...")
        self.add_button.clicked.connect(self.add_model_clicked)
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_model_clicked)
        self.remove_button.setEnabled(False)  # Enable when item selected

        list_controls.addWidget(self.add_button)
        list_controls.addWidget(self.remove_button)
        list_controls.addStretch(1)

        list_layout.addWidget(self.model_list, 1)  # Give list stretch factor
        list_layout.addLayout(list_controls)
        settings_layout.addLayout(list_layout)

        # Connect list selection change to enable/disable remove button
        self.model_list.itemSelectionChanged.connect(
            lambda: self.remove_button.setEnabled(
                bool(self.model_list.selectedItems())
            )
        )

        # --- Merge Method ---
        merge_layout = QHBoxLayout()
        merge_label = QLabel("Merge Method:")
        self.merge_combo = QComboBox()
        self.merge_combo.addItems(["Average", "Min/Max"])
        self.merge_combo.currentTextChanged.connect(self.merge_method_changed)
        merge_layout.addWidget(merge_label)
        merge_layout.addWidget(self.merge_combo)
        merge_layout.addStretch(1)
        settings_layout.addLayout(merge_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)

        # --- Populate with some dummy data for now ---
        self.add_ensemble_item("VR Arch - VR Model 2 (HP)", "Vocals")
        self.add_ensemble_item("MDX-Net - Kim Vocal 1", "Vocals")

        print("EnsembleSettingsView Initialized (Improved Stub).")

    # --- Methods to be called by Presenter ---

    @Slot(str, str)
    def add_ensemble_item(self, model_name: str, target_stem: str):
        """Adds an item to the ensemble list."""
        item_text = f"{model_name} -> [{target_stem}]"
        QListWidgetItem(item_text, self.model_list)

    @Slot()
    def remove_selected_item(self):
        """Removes the currently selected item from the list."""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            return
        # QListWidget only supports single selection by default
        row = self.model_list.row(selected_items[0])
        self.model_list.takeItem(row)

    @Slot(list)
    def update_list(self, items: list):
        """Clears and repopulates the list."""
        self.model_list.clear()
        for item in items:
            # Assuming items is a list of tuples (model_name, target_stem)
            self.add_ensemble_item(item[0], item[1])
