import sys
from PySide6.QtWidgets import QApplication
# We use a relative import here because it's within the same package
from .ui.main_window_view import MainWindowView


def run():
    """Initializes and runs the PySide6 application."""
    # Debug print removed
    app = QApplication(sys.argv)

    app.setStyle("Fusion") # Apply Fusion style

    main_window = MainWindowView()
    main_window.show()

    # Debug print removed
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
